from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any

from app.core.runtime_contract import APP_VERSION, SCHEMA_VERSION

EVIDENCE_SCHEMA = "mgc.production-incident-evidence.v1"
INTEGRITY_ALGORITHM = "sha256"
_SEVERITY_ORDER = {"low": 0, "medium": 1, "high": 2, "critical": 3}


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _canonical(data: dict[str, Any]) -> bytes:
    return json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _fingerprint(code: str, component: str) -> str:
    return hashlib.sha256(f"{code}|{component}".encode("utf-8")).hexdigest()


def _signal(code: str, severity: str, component: str, summary: str, evidence: dict[str, Any]) -> dict[str, Any]:
    return {
        "code": code,
        "severity": severity,
        "component": component,
        "summary": summary,
        "signal_fingerprint": _fingerprint(code, component),
        "evidence": evidence,
    }


def build_incident_evidence(
    operations: dict[str, Any],
    *,
    readiness: dict[str, Any] | None = None,
    generated_at: datetime | None = None,
) -> dict[str, Any]:
    """Build bounded-cardinality, privacy-safe incident evidence from existing operator snapshots.

    The report is diagnostic evidence only. It never restarts infrastructure, resolves an
    incident, changes authoritative engineering data or authorizes production.
    """
    signals: list[dict[str, Any]] = []

    ready = readiness or {}
    if ready and ready.get("status") not in {"ready", "ok"}:
        failed_required = sorted(
            str(c.get("name") or "unknown")[:64]
            for c in (ready.get("checks") or [])
            if bool(c.get("required", True)) and str(c.get("status")) != "ok"
        )
        if failed_required:
            signals.append(_signal(
                "REQUIRED_DEPENDENCY_NOT_READY", "high", "readiness",
                "One or more required runtime dependencies are not ready.",
                {"failed_required_components": failed_required[:32], "failed_count": len(failed_required)},
            ))

    dep = operations.get("dependency_sli") or {}
    dep_slo = dep.get("required_dependency_slo") or {}
    if dep_slo.get("status") == "BURNING":
        signals.append(_signal(
            "DEPENDENCY_ERROR_BUDGET_BURN", "high", "dependencies",
            "Required dependency availability is consuming or has exhausted its error budget.",
            {
                "observed": dep_slo.get("observed"),
                "target": dep_slo.get("target"),
                "budget_remaining_ratio": dep_slo.get("budget_remaining_ratio"),
                "window_minutes": dep.get("window_minutes"),
            },
        ))

    queue = operations.get("queue") or {}
    if queue.get("status") == "WARN":
        signals.append(_signal(
            "QUEUE_AGE_BREACH", "medium", "compute-queue",
            "Managed compute queue age is above the configured operational threshold.",
            {
                "oldest_job_age_seconds": queue.get("oldest_job_age_seconds"),
                "policy_max_age_seconds": queue.get("policy_max_age_seconds"),
            },
        ))

    integrations = operations.get("integrations") or {}
    if integrations.get("status") == "BURNING":
        stale = sorted(
            str(x.get("source_domain") or x.get("code") or "external")[:64]
            for x in (integrations.get("systems") or [])
            if x.get("freshness_compliant") is False
        )
        signals.append(_signal(
            "INTEGRATION_FRESHNESS_BREACH", "high", "integrations",
            "External engineering-data freshness is below the configured SLO.",
            {
                "freshness_compliance": integrations.get("freshness_compliance"),
                "target": integrations.get("target"),
                "stale_source_domains": stale[:32],
            },
        ))

    projections = operations.get("projections") or {}
    if projections and projections.get("status") not in {None, "healthy", "ok", "OK"}:
        signals.append(_signal(
            "PROJECTION_DEGRADED", "medium", "read-models",
            "A rebuildable projection/read-model pipeline is degraded.",
            {"status": projections.get("status"), "dead_letter": projections.get("dead_letter") or projections.get("dead_letter_count") or 0},
        ))

    workload = operations.get("workload") or {}
    dead = int(workload.get("dead_letter_jobs") or 0)
    orphaned = int(workload.get("orphaned_jobs") or 0)
    expired = int(workload.get("expired_running_leases") or 0)
    if dead or orphaned or expired:
        severity = "high" if orphaned or expired else "medium"
        signals.append(_signal(
            "WORKLOAD_RECOVERY_REQUIRED", severity, "compute-workload",
            "Managed workload contains jobs requiring operator recovery or replay review.",
            {"dead_letter_jobs": dead, "orphaned_jobs": orphaned, "expired_running_leases": expired},
        ))

    resilience = operations.get("resilience") or {}
    if resilience.get("mode") == "BROWNOUT":
        signals.append(_signal(
            "OPTIONAL_DEPENDENCY_BROWNOUT", "medium", "resilience",
            "Optional dependency circuits are open; core engineering remains available with reduced enrichment.",
            {"mode": "BROWNOUT", "open_circuits": int(resilience.get("open_circuits") or 0)},
        ))

    deployment = operations.get("deployment_safety") or {}
    incompatible = int(deployment.get("incompatible_components") or 0)
    if incompatible:
        signals.append(_signal(
            "RUNTIME_VERSION_SKEW", "high", "deployment",
            "Incompatible runtime components are visible in the deployment registry.",
            {"incompatible_components": incompatible},
        ))

    for key, code, component in (
        ("high_availability", "APPLICATION_HA_UNSAFE", "application-ha"),
        ("authoritative_data_ha", "AUTHORITATIVE_DATA_HA_UNSAFE", "authoritative-data-ha"),
        ("multi_host_topology", "MULTI_HOST_TOPOLOGY_UNSAFE", "multi-host"),
    ):
        snap = operations.get(key) or {}
        if snap.get("status") == "UNSAFE":
            signals.append(_signal(
                code, "critical", component,
                "A fail-closed production safety invariant is unsafe.",
                {"status": "UNSAFE", "enabled": bool(snap.get("enabled", True))},
            ))

    signals = sorted(signals, key=lambda x: (-_SEVERITY_ORDER[x["severity"]], x["code"], x["component"]))
    counts = {sev: sum(1 for x in signals if x["severity"] == sev) for sev in _SEVERITY_ORDER}
    highest = signals[0]["severity"] if signals else None
    generated = generated_at or utcnow()
    if generated.tzinfo is None:
        generated = generated.replace(tzinfo=timezone.utc)

    report: dict[str, Any] = {
        "schema": EVIDENCE_SCHEMA,
        "release": APP_VERSION,
        "database_schema": SCHEMA_VERSION,
        "generated_at": generated.astimezone(timezone.utc).isoformat(),
        "status": "INCIDENT_SIGNALS" if signals else "CLEAR",
        "signal_count": len(signals),
        "highest_severity": highest,
        "severity_counts": counts,
        "signals": signals,
        "governance": {
            "contains_raw_logs": False,
            "contains_document_content": False,
            "contains_queries": False,
            "contains_credentials": False,
            "bounded_cardinality": True,
            "automatic_destructive_recovery": False,
            "automatic_incident_resolution": False,
            "production_authorized": False,
            "human_operator_required": True,
        },
    }
    report["integrity"] = {
        "algorithm": INTEGRITY_ALGORITHM,
        "payload_sha256": hashlib.sha256(_canonical(report)).hexdigest(),
    }
    return report


def validate_incident_evidence(report: dict[str, Any]) -> tuple[bool, list[str]]:
    errors: list[str] = []
    if report.get("schema") != EVIDENCE_SCHEMA:
        errors.append("schema")
    if report.get("release") != APP_VERSION:
        errors.append("release")
    if report.get("database_schema") != SCHEMA_VERSION:
        errors.append("database_schema")
    governance = report.get("governance") or {}
    if governance.get("production_authorized") is not False:
        errors.append("production_authorized")
    if governance.get("automatic_destructive_recovery") is not False:
        errors.append("automatic_destructive_recovery")
    integrity = report.get("integrity") or {}
    expected = str(integrity.get("payload_sha256") or "")
    body = dict(report)
    body.pop("integrity", None)
    actual = hashlib.sha256(_canonical(body)).hexdigest()
    if integrity.get("algorithm") != INTEGRITY_ALGORITHM or expected != actual:
        errors.append("integrity")
    return not errors, errors
