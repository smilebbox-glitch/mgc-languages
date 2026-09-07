from __future__ import annotations

from app.core.runtime_contract import APP_VERSION

import hashlib
import io
import json
import math
import zipfile
from datetime import datetime, timedelta, timezone
from typing import Any

from prometheus_client import Gauge
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.operational_health import readiness_snapshot
from app.core.resilience import resilience_snapshot
from app.core.deployment_safety import deployment_safety_snapshot
from app.core.cutover_safety import cutover_safety_snapshot
from app.core.high_availability import high_availability_snapshot
from app.core.authoritative_ha import authoritative_ha_snapshot
from app.core.multi_host_topology import multi_host_topology_snapshot
from app.core.production_certification import runtime_acceptance_snapshot
from app.core.incident_evidence import build_incident_evidence, validate_incident_evidence
from app.services.projection_outbox import projection_health
from app.services.engineering_handover import handover_dashboard
from app.services.data_lifecycle import lifecycle_dashboard
from app.services.performance_governance import performance_governance_snapshot
from app.services.background_jobs import workload_snapshot
from app.db.session import engine
from app.db.models import ComputeJob, ExternalSystem, OperationalHealthSample, ProductionIncident
from app.services.enterprise_security import redact_details, security_posture

VERSION = APP_VERSION
QUEUE_DEPTH = Gauge("mgc_queue_depth", "Observed Celery/Redis queue depth", ["queue"])
QUEUE_OLDEST_AGE = Gauge("mgc_queue_oldest_age_seconds", "Oldest queued compute-job age", ["queue"])
INTEGRATION_LAG = Gauge("mgc_integration_lag_seconds", "Age since last successful/observed integration sync", ["system"])
OPEN_INCIDENTS = Gauge("mgc_open_incidents", "Open production-support incidents", ["severity"])
ERROR_BUDGET = Gauge("mgc_slo_error_budget_remaining_ratio", "Remaining SLO error-budget ratio", ["slo"])
INCIDENT_SIGNALS = Gauge("mgc_incident_evidence_signals", "Active bounded automated incident-evidence signals", ["severity"])
HANDOVER_JOBS = Gauge("mgc_handover_jobs", "Controlled engineering handover jobs by lifecycle status", ["status"])
HANDOVER_UNRECONCILED_AGE = Gauge("mgc_handover_oldest_unreconciled_age_seconds", "Age of oldest delivered handover awaiting reconciliation")
HANDOVER_WRITE_ENABLED = Gauge("mgc_handover_write_enabled", "1 when controlled external handover write-back is explicitly enabled")
LIFECYCLE_PURGE_REQUESTS = Gauge("mgc_lifecycle_purge_requests", "Engineering purge requests by state", ["state"])
LIFECYCLE_LEGAL_HOLDS = Gauge("mgc_lifecycle_active_legal_holds", "Active engineering legal holds")
LIFECYCLE_AUTHORITATIVE_PURGE = Gauge("mgc_lifecycle_authoritative_purge_enabled", "1 only when authoritative evidence purge is explicitly enabled")
WORKLOAD_JOBS = Gauge("mgc_compute_jobs", "Managed compute jobs by resource class and status", ["resource_class", "status"])
WORKLOAD_DLQ = Gauge("mgc_compute_dead_letter_jobs", "Managed compute jobs currently in dead-letter state")
WORKLOAD_ORPHANED = Gauge("mgc_compute_orphaned_jobs", "Managed compute jobs requiring confirmed manual recovery")
WORKLOAD_EXPIRED_LEASES = Gauge("mgc_compute_expired_running_leases", "Running compute jobs whose PostgreSQL worker lease is expired")
WORKLOAD_RECOVERIES = Gauge("mgc_compute_recovery_events_total", "Audited compute-job recovery events recorded in PostgreSQL")

_ALLOWED_INCIDENT_SEVERITIES = {"low", "medium", "high", "critical"}
_ALLOWED_INCIDENT_STATUSES = {"open", "mitigating", "monitoring", "resolved"}


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _utc(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def error_budget(*, target: float, good: int, total: int) -> dict[str, Any]:
    target = min(max(float(target), 0.0), 1.0)
    total = max(int(total), 0)
    good = min(max(int(good), 0), total)
    if total == 0:
        return {
            "status": "NO_DATA",
            "target": target,
            "observed": None,
            "total": 0,
            "bad": 0,
            "budget_allowed_bad": 0.0,
            "budget_consumed_ratio": None,
            "budget_remaining_ratio": None,
        }
    bad = total - good
    observed = good / total
    allowed_bad = total * (1.0 - target)
    if allowed_bad <= 0:
        consumed = math.inf if bad else 0.0
        remaining = 1.0 if bad == 0 else 0.0
    else:
        consumed = bad / allowed_bad
        remaining = max(0.0, 1.0 - consumed)
    return {
        "status": "PASS" if observed >= target else "BURNING",
        "target": round(target, 6),
        "observed": round(observed, 6),
        "total": total,
        "bad": bad,
        "budget_allowed_bad": round(allowed_bad, 3),
        "budget_consumed_ratio": round(consumed, 4) if math.isfinite(consumed) else None,
        "budget_remaining_ratio": round(remaining, 4),
    }


def capture_health_samples(db: Session, snapshot: dict[str, Any] | None = None, *, captured_at: datetime | None = None) -> dict[str, Any]:
    snap = snapshot or readiness_snapshot()
    when = _utc(captured_at) or utcnow()
    inserted = 0
    for c in snap.get("checks") or []:
        component = str(c.get("name") or "unknown")[:64]
        status = "ok" if str(c.get("status")) == "ok" else "failed"
        detail = str(c.get("detail") or "observed")[:64]
        db.add(OperationalHealthSample(
            captured_at=when,
            component=component,
            status=status,
            required=bool(c.get("required", True)),
            latency_ms=float(c.get("latency_ms") or 0.0),
            detail_code=detail,
        ))
        inserted += 1
    retention_days = max(1, int(get_settings().operational_health_retention_days))
    cutoff = when - timedelta(days=retention_days)
    db.execute(delete(OperationalHealthSample).where(OperationalHealthSample.captured_at < cutoff))
    db.commit()
    return {"captured_at": when.isoformat(), "samples": inserted, "overall_status": snap.get("status", "unknown"), "retention_days": retention_days}


def dependency_sli(db: Session, *, window_minutes: int | None = None, now: datetime | None = None) -> dict[str, Any]:
    cfg = get_settings()
    current = _utc(now) or utcnow()
    minutes = max(1, min(int(window_minutes or cfg.operations_default_window_minutes), 60 * 24 * 30))
    since = current - timedelta(minutes=minutes)
    rows = db.scalars(select(OperationalHealthSample).where(OperationalHealthSample.captured_at >= since)).all()
    by_component: dict[str, dict[str, int]] = {}
    required_good = required_total = 0
    for row in rows:
        bucket = by_component.setdefault(row.component, {"good": 0, "total": 0, "required": bool(row.required)})
        bucket["total"] += 1
        if row.status == "ok":
            bucket["good"] += 1
        if row.required:
            required_total += 1
            if row.status == "ok":
                required_good += 1
    components = []
    for name, b in sorted(by_component.items()):
        observed = (b["good"] / b["total"]) if b["total"] else None
        components.append({"component": name, "required": b["required"], "samples": b["total"], "availability": round(observed, 6) if observed is not None else None})
    budget = error_budget(target=cfg.slo_dependency_availability_target, good=required_good, total=required_total)
    if budget["budget_remaining_ratio"] is not None:
        ERROR_BUDGET.labels("required_dependencies").set(budget["budget_remaining_ratio"])
    return {
        "schema": "mgc-dependency-sli-v1",
        "window_minutes": minutes,
        "window_start": since.isoformat(),
        "window_end": current.isoformat(),
        "required_dependency_slo": budget,
        "components": components,
        "note": "Health samples are operational observations; external Prometheus remains the authoritative multi-replica time-series store.",
    }


def queue_snapshot(db: Session, *, now: datetime | None = None) -> dict[str, Any]:
    cfg = get_settings()
    current = _utc(now) or utcnow()
    queues = ["interactive", "cpu", "io", "cad", "ai", "maintenance"]
    legacy_aliases = {"cpu": ["cpu", "heavy", "default"], "maintenance": ["maintenance", "background"]}
    depths: dict[str, int | None] = {q: None for q in queues}
    redis_status = "unavailable"
    try:
        import redis
        client = redis.Redis.from_url(cfg.redis_url, socket_connect_timeout=cfg.health_timeout_seconds, socket_timeout=cfg.health_timeout_seconds)
        for q in queues:
            physical = legacy_aliases.get(q, [q])
            depths[q] = sum(int(client.llen(name)) for name in physical)
            QUEUE_DEPTH.labels(q).set(depths[q] or 0)
        redis_status = "available"
    except Exception:
        pass

    oldest_by_queue: dict[str, float | None] = {q: None for q in queues}
    for q in queues:
        physical = legacy_aliases.get(q, [q])
        oldest = db.scalar(select(func.min(ComputeJob.created_at)).where(ComputeJob.queue.in_(physical), ComputeJob.status.in_(["queued", "running"])))
        if oldest:
            age = max(0.0, (current - (_utc(oldest) or current)).total_seconds())
            oldest_by_queue[q] = round(age, 1)
            QUEUE_OLDEST_AGE.labels(q).set(age)
    max_age = max([v for v in oldest_by_queue.values() if v is not None] or [0.0])
    return {
        "redis": redis_status,
        "queues": [{"queue": q, "depth": depths[q], "oldest_job_age_seconds": oldest_by_queue[q]} for q in queues],
        "oldest_job_age_seconds": round(max_age, 1),
        "policy_max_age_seconds": int(cfg.slo_queue_max_age_seconds),
        "status": "WARN" if max_age > cfg.slo_queue_max_age_seconds else "OK",
    }


def integration_lag_snapshot(db: Session, *, now: datetime | None = None) -> dict[str, Any]:
    cfg = get_settings()
    current = _utc(now) or utcnow()
    rows = db.scalars(select(ExternalSystem).where(ExternalSystem.enabled == True).order_by(ExternalSystem.code)).all()  # noqa: E712
    items = []
    fresh = total_with_sla = 0
    for system in rows:
        sync_at = _utc(system.last_sync_at)
        lag = max(0.0, (current - sync_at).total_seconds()) if sync_at else None
        expected_min = int(system.expected_freshness_minutes or 0) or None
        compliant = None
        if expected_min:
            total_with_sla += 1
            compliant = lag is not None and lag <= expected_min * 60
            if compliant:
                fresh += 1
        if lag is not None:
            INTEGRATION_LAG.labels(system.code[:64]).set(lag)
        items.append({
            "system": system.code,
            "source_domain": system.source_domain,
            "last_sync_status": system.last_sync_status or "never",
            "lag_seconds": round(lag, 1) if lag is not None else None,
            "expected_freshness_minutes": expected_min,
            "freshness_compliant": compliant,
            "data_confidence": system.last_quality_json.get("level") if isinstance(system.last_quality_json, dict) else None,
        })
    ratio = (fresh / total_with_sla) if total_with_sla else None
    target = float(cfg.slo_integration_freshness_target)
    return {
        "systems": items,
        "systems_with_sla": total_with_sla,
        "fresh_systems": fresh,
        "freshness_compliance": round(ratio, 6) if ratio is not None else None,
        "target": target,
        "status": "NO_DATA" if ratio is None else ("PASS" if ratio >= target else "BURNING"),
    }


def list_incidents(db: Session, *, limit: int = 100, include_evidence: bool = True) -> list[dict[str, Any]]:
    rows = db.scalars(select(ProductionIncident).order_by(ProductionIncident.started_at.desc()).limit(max(1, min(limit, 500)))).all()
    counts = {s: 0 for s in _ALLOWED_INCIDENT_SEVERITIES}
    out = []
    for r in rows:
        if r.status != "resolved" and r.severity in counts:
            counts[r.severity] += 1
        out.append({
            "id": r.id, "code": r.code, "severity": r.severity, "status": r.status, "component": r.component,
            "summary": r.summary, "impact_summary": r.impact_summary, "detected_by": r.detected_by,
            "started_at": _utc(r.started_at).isoformat() if r.started_at else None,
            "resolved_at": _utc(r.resolved_at).isoformat() if r.resolved_at else None,
            "resolution_summary": r.resolution_summary,
            "evidence": redact_details(r.evidence_json or {}) if include_evidence else {"present": bool(r.evidence_json)},
        })
    for sev, count in counts.items():
        OPEN_INCIDENTS.labels(sev).set(count)
    return out


def create_incident(db: Session, *, code: str, severity: str, component: str, summary: str, actor: str, impact_summary: str | None = None, detected_by: str = "operator", evidence: dict | None = None) -> ProductionIncident:
    severity = severity.lower().strip()
    if severity not in _ALLOWED_INCIDENT_SEVERITIES:
        raise ValueError("Unsupported incident severity")
    row = ProductionIncident(code=code.strip(), severity=severity, component=component.strip()[:64], summary=summary.strip()[:512], impact_summary=impact_summary, detected_by=detected_by.strip()[:64], evidence_json=evidence or {}, created_by=actor)
    db.add(row); db.commit(); db.refresh(row)
    return row


def update_incident(db: Session, row: ProductionIncident, *, actor: str, status: str | None = None, severity: str | None = None, resolution_summary: str | None = None, evidence: dict | None = None, now: datetime | None = None) -> ProductionIncident:
    if status is not None:
        status = status.lower().strip()
        if status not in _ALLOWED_INCIDENT_STATUSES:
            raise ValueError("Unsupported incident status")
        row.status = status
        if status == "resolved":
            if not str(resolution_summary or row.resolution_summary or "").strip():
                raise ValueError("Resolution summary is required before resolving an incident")
            row.resolved_at = _utc(now) or utcnow()
    if severity is not None:
        severity = severity.lower().strip()
        if severity not in _ALLOWED_INCIDENT_SEVERITIES:
            raise ValueError("Unsupported incident severity")
        row.severity = severity
    if resolution_summary is not None:
        row.resolution_summary = resolution_summary.strip()
    if evidence is not None:
        row.evidence_json = evidence
    row.updated_by = actor
    db.commit(); db.refresh(row)
    return row


def incident_evidence_snapshot(
    db: Session,
    *,
    operations: dict[str, Any] | None = None,
    readiness: dict[str, Any] | None = None,
    generated_at: datetime | None = None,
) -> dict[str, Any]:
    report = build_incident_evidence(
        operations or operations_summary(db),
        readiness=readiness or readiness_snapshot(),
        generated_at=generated_at,
    )
    for severity, count in (report.get("severity_counts") or {}).items():
        if severity in _ALLOWED_INCIDENT_SEVERITIES:
            INCIDENT_SIGNALS.labels(severity).set(int(count or 0))
    return report


def reconcile_automated_incident_evidence(
    db: Session,
    report: dict[str, Any],
    *,
    actor: str = "system-observer",
    materialize: bool | None = None,
) -> dict[str, Any]:
    """Materialize active automated signals as operator-owned incidents without auto-resolution.

    Existing open automated incidents are deduplicated by signal fingerprint and refreshed.
    Resolved incidents are never reopened or closed automatically; a persistent/recurrent signal
    becomes a new incident on a later reconciliation pass.
    """
    valid, errors = validate_incident_evidence(report)
    if not valid:
        raise ValueError("Invalid incident evidence: " + ", ".join(errors))
    enabled = bool(get_settings().automated_incident_materialization_enabled) if materialize is None else bool(materialize)
    open_auto = db.scalars(
        select(ProductionIncident).where(
            ProductionIncident.status != "resolved",
            ProductionIncident.detected_by == "automated-observability",
        )
    ).all()
    by_fp = {}
    for row in open_auto:
        ev = row.evidence_json if isinstance(row.evidence_json, dict) else {}
        fp = str(ev.get("signal_fingerprint") or "")
        if fp:
            by_fp[fp] = row

    actions: list[dict[str, Any]] = []
    rank = {"low": 0, "medium": 1, "high": 2, "critical": 3}
    now = utcnow()
    for signal in report.get("signals") or []:
        fp = str(signal.get("signal_fingerprint") or "")
        if not fp:
            continue
        row = by_fp.get(fp)
        evidence = {
            "schema": "mgc.automated-incident-signal.v1",
            "signal_fingerprint": fp,
            "signal_code": signal.get("code"),
            "observed_at": report.get("generated_at"),
            "report_sha256": (report.get("integrity") or {}).get("payload_sha256"),
            "evidence": signal.get("evidence") or {},
            "governance": {
                "automatic_resolution": False,
                "automatic_destructive_recovery": False,
                "production_authorized": False,
                "human_operator_required": True,
            },
        }
        if row is not None:
            current_sev = str(row.severity or "medium")
            proposed = str(signal.get("severity") or "medium")
            if rank.get(proposed, 0) > rank.get(current_sev, 0):
                row.severity = proposed
            row.summary = str(signal.get("summary") or row.summary)[:512]
            row.component = str(signal.get("component") or row.component)[:64]
            row.evidence_json = evidence
            row.updated_by = actor
            db.add(row)
            actions.append({"signal_fingerprint": fp, "action": "REFRESHED", "incident_id": row.id})
            continue
        if not enabled:
            actions.append({"signal_fingerprint": fp, "action": "EVIDENCE_ONLY", "incident_id": None})
            continue
        code = f"AUTO-OBS-{fp[:12].upper()}-{now.strftime('%Y%m%d%H%M%S')}"
        row = ProductionIncident(
            code=code,
            severity=str(signal.get("severity") or "medium"),
            status="open",
            component=str(signal.get("component") or "application")[:64],
            summary=str(signal.get("summary") or "Automated operational signal")[:512],
            impact_summary="Automated evidence only; operator impact assessment required.",
            detected_by="automated-observability",
            evidence_json=evidence,
            created_by=actor,
        )
        db.add(row)
        db.flush()
        by_fp[fp] = row
        actions.append({"signal_fingerprint": fp, "action": "CREATED", "incident_id": row.id})
    db.commit()
    return {
        "schema": "mgc.automated-incident-reconciliation.v1",
        "release": VERSION,
        "materialization_enabled": enabled,
        "signals": int(report.get("signal_count") or 0),
        "actions": actions,
        "automatic_resolution": False,
        "production_authorized": False,
        "human_operator_required": True,
    }


def operations_summary(db: Session, *, window_minutes: int | None = None) -> dict[str, Any]:
    slo = dependency_sli(db, window_minutes=window_minutes)
    queue = queue_snapshot(db)
    integrations = integration_lag_snapshot(db)
    incidents = list_incidents(db, limit=get_settings().support_bundle_max_incidents, include_evidence=False)
    projections = projection_health(db)
    handover = handover_dashboard(db)
    lifecycle = lifecycle_dashboard(db)
    performance = performance_governance_snapshot(engine)
    workload = workload_snapshot(db)
    resilience = resilience_snapshot()
    deployment = deployment_safety_snapshot()
    cutover = cutover_safety_snapshot()
    high_availability = high_availability_snapshot()
    authoritative_ha = authoritative_ha_snapshot()
    multi_host_topology = multi_host_topology_snapshot()
    production_certification = runtime_acceptance_snapshot(db)
    for resource, statuses in (workload.get("resource_classes") or {}).items():
        for state, count in statuses.items():
            WORKLOAD_JOBS.labels(resource, state).set(int(count or 0))
    WORKLOAD_DLQ.set(int(workload.get("dead_letter_jobs") or 0))
    WORKLOAD_ORPHANED.set(int(workload.get("orphaned_jobs") or 0))
    WORKLOAD_EXPIRED_LEASES.set(int(workload.get("expired_running_leases") or 0))
    WORKLOAD_RECOVERIES.set(int(workload.get("recovery_events") or 0))
    for status in ("pending_authorization","authorized","delivering","delivered","reconciled","failed","reconciliation_failed"):
        HANDOVER_JOBS.labels(status).set(int(handover.get(status) or 0))
    HANDOVER_UNRECONCILED_AGE.set(float(handover.get("oldest_unreconciled_age_seconds") or 0.0))
    HANDOVER_WRITE_ENABLED.set(1 if handover.get("write_enabled") else 0)
    LIFECYCLE_PURGE_REQUESTS.labels("pending_authorization").set(int(lifecycle.get("pending_purge_authorizations") or 0))
    LIFECYCLE_PURGE_REQUESTS.labels("authorized").set(int(lifecycle.get("authorized_purges") or 0))
    LIFECYCLE_LEGAL_HOLDS.set(int(lifecycle.get("active_legal_holds") or 0))
    LIFECYCLE_AUTHORITATIVE_PURGE.set(1 if lifecycle.get("authoritative_purge_enabled") else 0)
    open_incidents = [x for x in incidents if x["status"] != "resolved"]
    critical = [x for x in open_incidents if x["severity"] == "critical"]
    return {
        "version": VERSION,
        "dependency_sli": slo,
        "queue": queue,
        "integrations": integrations,
        "projections": projections,
        "handover": handover,
        "data_lifecycle": lifecycle,
        "database_performance": performance,
        "workload": workload,
        "resilience": resilience,
        "deployment_safety": deployment,
        "cutover_safety": cutover,
        "high_availability": high_availability,
        "authoritative_data_ha": authoritative_ha,
        "multi_host_topology": multi_host_topology,
        "production_certification": production_certification,
        "incidents": {"open": len(open_incidents), "critical": len(critical), "recent": incidents[:10]},
        "status": "RED" if critical or int(deployment.get("incompatible_components") or 0) > 0 or high_availability.get("status") == "UNSAFE" or authoritative_ha.get("status") == "UNSAFE" or multi_host_topology.get("status") == "UNSAFE" else ("AMBER" if open_incidents or queue["status"] == "WARN" or integrations["status"] == "BURNING" or projections["status"] != "healthy" or handover["operational_status"] != "OK" or lifecycle.get("authorized_purges",0) > 0 or performance.get("operational_status") != "OK" or workload.get("dead_letter_jobs",0) > 0 or workload.get("orphaned_jobs",0) > 0 or workload.get("expired_running_leases",0) > 0 or workload.get("running_cancel_requested",0) > 0 or resilience.get("mode") == "BROWNOUT" or int(deployment.get("draining_components") or 0) > 0 or (high_availability.get("enabled") and high_availability.get("status") != "HEALTHY") or (multi_host_topology.get("enabled") and multi_host_topology.get("status") != "HEALTHY") or production_certification.get("decision") == "NO_GO" else "GREEN"),
        "human_operator_required": True,
    }


def _privacy_safe_support_operations(summary: dict[str, Any]) -> dict[str, Any]:
    """Strip operator free-text incident narrative from exported support bundles.

    The live Operations API remains unchanged. This export transform prevents an operator-typed
    VIN/part/document identifier from being copied into an IT troubleshooting ZIP.
    """
    safe = json.loads(json.dumps(redact_details(summary), ensure_ascii=False, default=str))
    box = safe.get("incidents") if isinstance(safe, dict) else None
    if isinstance(box, dict):
        rows = []
        for item in box.get("recent") or []:
            if not isinstance(item, dict):
                continue
            rows.append({
                "id": item.get("id"),
                "code": item.get("code"),
                "severity": item.get("severity"),
                "status": item.get("status"),
                "component": item.get("component"),
                "detected_by": item.get("detected_by"),
                "started_at": item.get("started_at"),
                "resolved_at": item.get("resolved_at"),
                "summary_present": bool(item.get("summary")),
                "impact_summary_present": bool(item.get("impact_summary")),
                "resolution_summary_present": bool(item.get("resolution_summary")),
                "evidence_present": bool((item.get("evidence") or {}).get("present")) if isinstance(item.get("evidence"), dict) else bool(item.get("evidence")),
                "operator_narrative_exported": False,
            })
        box["recent"] = rows
    return safe


def build_support_bundle(db: Session, *, actor: str, window_minutes: int | None = None, readiness: dict[str, Any] | None = None) -> tuple[bytes, dict[str, Any]]:
    """Create a privacy-safe troubleshooting bundle; no raw logs, documents, queries or secrets."""
    generated = utcnow()
    files: dict[str, bytes] = {}
    safe_health = readiness or readiness_snapshot()
    operations = operations_summary(db, window_minutes=window_minutes)
    incident_evidence = incident_evidence_snapshot(db, operations=operations, readiness=safe_health, generated_at=generated)
    docs = {
        "health.json": safe_health,
        "operations-summary.json": _privacy_safe_support_operations(operations),
        "incident-evidence.json": incident_evidence,
        "security-posture.json": security_posture(),
        "resilience.json": resilience_snapshot(),
        "deployment-safety.json": deployment_safety_snapshot(),
        "cutover-safety.json": cutover_safety_snapshot(),
        "high-availability.json": high_availability_snapshot(),
        "authoritative-ha.json": authoritative_ha_snapshot(),
        "multi-host-topology.json": multi_host_topology_snapshot(),
        "production-certification.json": runtime_acceptance_snapshot(db),
    }
    for name, obj in docs.items():
        files[name] = json.dumps(obj, ensure_ascii=False, sort_keys=True, indent=2, default=str).encode("utf-8") + b"\n"
    manifest_files = []
    for name in sorted(files):
        manifest_files.append({"name": name, "sha256": hashlib.sha256(files[name]).hexdigest(), "bytes": len(files[name])})
    manifest = {
        "schema": "mgc-support-bundle-v1",
        "application_version": VERSION,
        "generated_at": generated.isoformat(),
        "generated_by": "engineering-admin",
        "files": manifest_files,
        "privacy": {
            "contains_raw_logs": False,
            "contains_document_content": False,
            "contains_queries": False,
            "contains_vin_or_part_history": False,
            "contains_secrets": False,
        },
    }
    files["manifest.json"] = json.dumps(manifest, ensure_ascii=False, sort_keys=True, indent=2).encode("utf-8") + b"\n"
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for name, payload in sorted(files.items()):
            zf.writestr(name, payload)
    payload = buf.getvalue()
    public = {**manifest, "zip_sha256": hashlib.sha256(payload).hexdigest(), "zip_bytes": len(payload), "actor_recorded_in_audit_only": bool(actor)}
    return payload, public
