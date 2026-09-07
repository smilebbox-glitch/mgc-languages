from __future__ import annotations

from app.core.runtime_contract import APP_VERSION

from datetime import datetime, timezone
from statistics import median
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import OperationsGameDayExercise, OperationsGameDayRun, ProductionIncident

VERSION = APP_VERSION

DEFAULT_EXERCISES = [
    {"code": "postgres_outage", "component": "postgresql", "scenario_type": "dependency_outage", "rto": 900, "rpo": 300, "critical": True},
    {"code": "redis_outage", "component": "redis", "scenario_type": "dependency_outage", "rto": 600, "rpo": 0, "critical": False},
    {"code": "qdrant_outage", "component": "qdrant", "scenario_type": "dependency_outage", "rto": 900, "rpo": 0, "critical": False},
    {"code": "worker_crash_restart", "component": "celery_worker", "scenario_type": "worker_restart", "rto": 300, "rpo": 0, "critical": False},
    {"code": "integration_outage", "component": "integration", "scenario_type": "external_dependency", "rto": 1800, "rpo": 900, "critical": False},
    {"code": "expired_tls_certificate", "component": "tls_edge", "scenario_type": "certificate_failure", "rto": 900, "rpo": 0, "critical": True},
    {"code": "oidc_failure", "component": "oidc", "scenario_type": "identity_failure", "rto": 900, "rpo": 0, "critical": True},
    {"code": "queue_overload", "component": "celery_queue", "scenario_type": "capacity_overload", "rto": 900, "rpo": 0, "critical": False},
    {"code": "backup_restore", "component": "postgresql_storage_qdrant", "scenario_type": "disaster_recovery", "rto": 3600, "rpo": 900, "critical": True},
]

REQUIRED_EXTERNAL_GATES = [
    "docker_runtime_acceptance",
    "cve_scan",
    "dependency_lock_resolution",
    "oidc_negative_tests",
    "mtls_negative_tests",
    "monitoring_alert_routing",
    "pilot_performance_profile",
]

ALLOWED_MODES = {"rehearsal", "controlled"}
ALLOWED_EXERCISE_STATUS = {"planned", "running", "recovered", "verified", "failed", "blocked"}


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _utc(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def default_policy() -> dict[str, Any]:
    return {
        "required_exercises": [x["code"] for x in DEFAULT_EXERCISES],
        "required_external_gates": list(REQUIRED_EXTERNAL_GATES),
        "critical_exercises": [x["code"] for x in DEFAULT_EXERCISES if x["critical"]],
        "require_zero_open_critical_incidents": True,
        "high_incident_yields_conditional": True,
        "human_go_live_required": True,
        "application_never_injects_faults": True,
    }


def create_game_day(db: Session, *, code: str, name: str, mode: str, actor: str, notes: str | None = None) -> OperationsGameDayRun:
    mode = mode.strip().lower()
    if mode not in ALLOWED_MODES:
        raise ValueError("Unsupported game-day mode")
    if db.scalar(select(OperationsGameDayRun).where(OperationsGameDayRun.code == code.strip())):
        raise ValueError("Game-day code already exists")
    policy = default_policy()
    row = OperationsGameDayRun(
        code=code.strip(), name=name.strip(), mode=mode, status="planned",
        required_exercises=policy["required_exercises"], gate_policy_json=policy,
        external_gate_evidence_json={}, notes=notes, created_by=actor,
    )
    db.add(row); db.commit(); db.refresh(row)
    for spec in DEFAULT_EXERCISES:
        db.add(OperationsGameDayExercise(
            run_id=row.id, exercise_code=spec["code"], component=spec["component"], scenario_type=spec["scenario_type"],
            required=True, status="planned", target_rto_seconds=spec["rto"], target_rpo_seconds=spec["rpo"],
            runbook_ref=f"docs/GAME_DAY_RUNBOOK.md#{spec['code'].replace('_','-')}",
        ))
    db.commit()
    return row


def list_game_days(db: Session, *, limit: int = 100) -> list[dict[str, Any]]:
    rows = db.scalars(select(OperationsGameDayRun).order_by(OperationsGameDayRun.created_at.desc()).limit(max(1, min(limit, 500)))).all()
    return [{
        "id": r.id, "code": r.code, "name": r.name, "mode": r.mode, "status": r.status,
        "final_decision": r.final_decision, "started_at": _utc(r.started_at).isoformat() if r.started_at else None,
        "completed_at": _utc(r.completed_at).isoformat() if r.completed_at else None,
    } for r in rows]


def start_game_day(db: Session, row: OperationsGameDayRun, *, actor: str, now: datetime | None = None) -> OperationsGameDayRun:
    if row.status not in {"planned", "paused"}:
        raise ValueError("Game day cannot be started from current status")
    row.status = "active"; row.started_at = _utc(now) or utcnow(); row.closed_by = None
    row.updated_at = utcnow()
    db.commit(); db.refresh(row)
    return row


def record_external_gates(db: Session, row: OperationsGameDayRun, *, evidence: dict[str, Any]) -> OperationsGameDayRun:
    safe = {}
    for key, value in evidence.items():
        if key not in REQUIRED_EXTERNAL_GATES:
            continue
        if isinstance(value, dict):
            safe[key] = {"status": str(value.get("status") or "UNKNOWN").upper(), "evidence_ref": str(value.get("evidence_ref") or "")[:255]}
        else:
            safe[key] = {"status": "PASS" if bool(value) else "FAIL", "evidence_ref": ""}
    row.external_gate_evidence_json = safe
    db.commit(); db.refresh(row)
    return row


def _seconds(a: datetime | None, b: datetime | None) -> float | None:
    a = _utc(a); b = _utc(b)
    if a is None or b is None or b < a:
        return None
    return round((b - a).total_seconds(), 3)


def exercise_metrics(row: OperationsGameDayExercise) -> dict[str, Any]:
    rto = _seconds(row.fault_injected_at or row.started_at, row.recovered_at)
    mttr = _seconds(row.detected_at, row.recovered_at)
    rpo = row.actual_rpo_seconds
    return {
        "actual_rto_seconds": rto,
        "actual_mttr_seconds": mttr,
        "actual_rpo_seconds": rpo,
        "rto_target_seconds": row.target_rto_seconds,
        "rpo_target_seconds": row.target_rpo_seconds,
        "rto_pass": None if rto is None or row.target_rto_seconds is None else rto <= row.target_rto_seconds,
        "rpo_pass": None if rpo is None or row.target_rpo_seconds is None else rpo <= row.target_rpo_seconds,
    }


def update_exercise(db: Session, row: OperationsGameDayExercise, *, actor: str, payload: dict[str, Any]) -> OperationsGameDayExercise:
    if "status" in payload and payload["status"] is not None:
        status = str(payload["status"]).strip().lower()
        if status not in ALLOWED_EXERCISE_STATUS:
            raise ValueError("Unsupported exercise status")
        row.status = status
    for field in ("started_at", "fault_injected_at", "detected_at", "mitigated_at", "recovered_at", "verified_at"):
        if field in payload and payload[field] is not None:
            setattr(row, field, _utc(payload[field]))
    if payload.get("actual_rpo_seconds") is not None:
        row.actual_rpo_seconds = max(0, int(payload["actual_rpo_seconds"]))
    if payload.get("evidence") is not None:
        row.evidence_json = dict(payload["evidence"])
    if payload.get("notes") is not None:
        row.notes = str(payload["notes"])[:4000]
    if row.status == "verified":
        if row.recovered_at is None or row.verified_at is None:
            raise ValueError("Recovered and verified timestamps are required before VERIFIED")
        metrics = exercise_metrics(row)
        if metrics["rto_pass"] is None or metrics["rpo_pass"] is None:
            raise ValueError("RTO/RPO evidence is required before VERIFIED")
        if not row.evidence_json:
            raise ValueError("Exercise evidence is required before VERIFIED")
    row.updated_by = actor
    db.commit(); db.refresh(row)
    return row


def evaluate_game_day(db: Session, row: OperationsGameDayRun) -> dict[str, Any]:
    exercises = db.scalars(select(OperationsGameDayExercise).where(OperationsGameDayExercise.run_id == row.id).order_by(OperationsGameDayExercise.exercise_code)).all()
    policy = row.gate_policy_json or default_policy()
    required = set(row.required_exercises or policy.get("required_exercises") or [])
    critical = set(policy.get("critical_exercises") or [])
    by_code = {x.exercise_code: x for x in exercises}
    blockers: list[dict[str, Any]] = []
    conditions: list[dict[str, Any]] = []
    items = []
    rtos = []; mttrs = []
    for code in sorted(required):
        ex = by_code.get(code)
        if ex is None:
            blockers.append({"code": "MISSING_EXERCISE", "exercise": code, "severity": "critical"})
            continue
        m = exercise_metrics(ex)
        items.append({"exercise_code": code, "component": ex.component, "status": ex.status, **m})
        if ex.status != "verified":
            blockers.append({"code": "EXERCISE_NOT_VERIFIED", "exercise": code, "severity": "critical" if code in critical else "high", "actual": ex.status})
            continue
        if m["actual_rto_seconds"] is not None: rtos.append(m["actual_rto_seconds"])
        if m["actual_mttr_seconds"] is not None: mttrs.append(m["actual_mttr_seconds"])
        if m["rpo_pass"] is False:
            blockers.append({"code": "RPO_TARGET_MISSED", "exercise": code, "severity": "critical", "actual": m["actual_rpo_seconds"], "target": m["rpo_target_seconds"]})
        if m["rto_pass"] is False:
            target = float(m["rto_target_seconds"] or 0)
            actual = float(m["actual_rto_seconds"] or 0)
            if code in critical or (target and actual > target * 1.25):
                blockers.append({"code": "RTO_TARGET_MISSED", "exercise": code, "severity": "critical" if code in critical else "high", "actual": actual, "target": target})
            else:
                conditions.append({"code": "RTO_TARGET_SLIGHTLY_MISSED", "exercise": code, "severity": "medium", "actual": actual, "target": target})

    ext = row.external_gate_evidence_json or {}
    if row.mode == "controlled":
        for gate in policy.get("required_external_gates") or REQUIRED_EXTERNAL_GATES:
            state = (ext.get(gate) or {}).get("status") if isinstance(ext.get(gate), dict) else None
            if str(state).upper() != "PASS":
                blockers.append({"code": "EXTERNAL_GATE_NOT_PASS", "gate": gate, "severity": "critical", "actual": state or "MISSING"})

    open_incidents = db.scalars(select(ProductionIncident).where(ProductionIncident.status != "resolved")).all()
    for inc in open_incidents:
        if inc.severity == "critical":
            blockers.append({"code": "OPEN_CRITICAL_INCIDENT", "incident": inc.code, "severity": "critical"})
        elif inc.severity == "high":
            conditions.append({"code": "OPEN_HIGH_INCIDENT", "incident": inc.code, "severity": "high"})

    required_count = len(required)
    verified_count = sum(1 for code in required if code in by_code and by_code[code].status == "verified")
    coverage = verified_count / required_count if required_count else 0.0
    if row.mode == "rehearsal":
        decision = "PRECHECK_FAIL" if blockers else "PRECHECK_PASS"
    else:
        decision = "NO_GO" if blockers else ("CONDITIONAL_GO" if conditions else "GO")
    return {
        "schema": "mgc-operations-acceptance-v1",
        "version": VERSION,
        "run_id": row.id,
        "mode": row.mode,
        "decision": decision,
        "required_exercise_coverage": round(coverage, 6),
        "exercises": items,
        "metrics": {
            "median_rto_seconds": round(median(rtos), 3) if rtos else None,
            "median_mttr_seconds": round(median(mttrs), 3) if mttrs else None,
            "verified_required_exercises": verified_count,
            "required_exercises": required_count,
        },
        "blockers": blockers,
        "conditions": conditions,
        "human_go_live_required": True,
        "deployment_authorized": False,
        "fault_injection_performed_by_application": False,
    }


def finalize_game_day(db: Session, row: OperationsGameDayRun, *, actor: str, confirm: str, now: datetime | None = None) -> dict[str, Any]:
    if confirm != "FINALIZE_OPERATIONS_ACCEPTANCE":
        raise ValueError("Explicit confirmation FINALIZE_OPERATIONS_ACCEPTANCE is required")
    evaluation = evaluate_game_day(db, row)
    row.final_decision = evaluation["decision"]
    row.final_evaluation_json = evaluation
    row.status = "completed"
    row.closed_by = actor
    row.completed_at = _utc(now) or utcnow()
    db.commit(); db.refresh(row)
    return {**evaluation, "finalized": True, "deployment_authorized": False}
