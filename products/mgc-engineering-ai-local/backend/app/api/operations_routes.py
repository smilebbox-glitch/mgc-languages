from __future__ import annotations

from app.core.runtime_contract import APP_VERSION

import io

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.security import Identity, get_identity, is_engineering_admin
from app.db.models import EditConflictEvent, OperationsGameDayExercise, OperationsGameDayRun, ProductionIncident
from app.db.session import get_db
from app.services.audit import log_event
from app.core.resilience import resilience_snapshot
from app.core.operational_health import readiness_snapshot
from app.core.deployment_safety import deployment_safety_snapshot
from app.core.cutover_safety import cutover_safety_snapshot
from app.core.high_availability import high_availability_snapshot
from app.core.authoritative_ha import authoritative_ha_snapshot
from app.core.multi_host_topology import multi_host_topology_snapshot
from app.core.production_certification import runtime_acceptance_snapshot
from app.core.release_provenance import registry_summary
from app.core.release_provenance_governance import verify_governance
from app.core.config import get_settings
from app.services.production_support import (
    build_support_bundle,
    capture_health_samples,
    create_incident,
    dependency_sli,
    list_incidents,
    operations_summary,
    incident_evidence_snapshot,
    reconcile_automated_incident_evidence,
    update_incident,
)
from app.services.projection_outbox import enqueue_rebuild, list_outbox, projection_health, replay_dead_letter, drain_projection_outbox
from app.services.revision_control import integrity_dashboard
from app.db.session import SessionLocal
from app.services.operations_acceptance import (
    create_game_day,
    evaluate_game_day,
    finalize_game_day,
    list_game_days,
    record_external_gates,
    start_game_day,
    update_exercise,
)

router = APIRouter(prefix="/operations", tags=["operations"])


def _admin(identity: Identity) -> None:
    if not is_engineering_admin(identity):
        raise HTTPException(403, "Engineering Admin role is required")


class IncidentCreate(BaseModel):
    code: str = Field(min_length=2, max_length=96)
    severity: str = Field(default="medium", max_length=16)
    component: str = Field(default="application", max_length=64)
    summary: str = Field(min_length=3, max_length=512)
    impact_summary: str | None = Field(default=None, max_length=4000)
    detected_by: str = Field(default="operator", max_length=64)
    evidence: dict = Field(default_factory=dict)


class IncidentUpdate(BaseModel):
    status: str | None = Field(default=None, max_length=24)
    severity: str | None = Field(default=None, max_length=16)
    resolution_summary: str | None = Field(default=None, max_length=4000)
    evidence: dict | None = None


class GameDayCreate(BaseModel):
    code: str = Field(min_length=2, max_length=96)
    name: str = Field(min_length=3, max_length=255)
    mode: str = Field(default="controlled", max_length=32)
    notes: str | None = Field(default=None, max_length=4000)


class GameDayExerciseUpdate(BaseModel):
    status: str | None = Field(default=None, max_length=32)
    started_at: str | None = None
    fault_injected_at: str | None = None
    detected_at: str | None = None
    mitigated_at: str | None = None
    recovered_at: str | None = None
    verified_at: str | None = None
    actual_rpo_seconds: int | None = Field(default=None, ge=0)
    evidence: dict | None = None
    notes: str | None = Field(default=None, max_length=4000)


class GameDayExternalGates(BaseModel):
    evidence: dict = Field(default_factory=dict)


@router.get("/summary")
def summary(window_minutes: int | None = None, identity: Identity = Depends(get_identity), db: Session = Depends(get_db)):
    _admin(identity)
    return operations_summary(db, window_minutes=window_minutes)


@router.get("/slo")
def slo(window_minutes: int | None = None, identity: Identity = Depends(get_identity), db: Session = Depends(get_db)):
    _admin(identity)
    return dependency_sli(db, window_minutes=window_minutes)


@router.get("/resilience")
def resilience(identity: Identity = Depends(get_identity)):
    _admin(identity)
    snapshot = resilience_snapshot()
    snapshot["operator_guidance"] = {
        "NORMAL": "No optional dependency circuit is open.",
        "BROWNOUT": "Core engineering remains available. Inspect open optional circuits before restoring enrichment capacity.",
    }.get(snapshot.get("mode"), "Inspect dependency diagnostics.")
    return snapshot


@router.get("/deployment-safety")
def deployment_safety(identity: Identity = Depends(get_identity)):
    _admin(identity)
    snapshot = deployment_safety_snapshot(touch_api=True)
    snapshot["operator_guidance"] = (
        "Proceed only when incompatible_components=0; drain workers before replacing them and keep exactly one scheduler leader."
        if snapshot.get("rolling_upgrade_safe") else
        "STOP rollout: incompatible runtime/schema component detected. Do not force task execution across the skew."
    )
    return snapshot


@router.get("/cutover-safety")
def cutover_safety(identity: Identity = Depends(get_identity)):
    _admin(identity)
    snapshot = cutover_safety_snapshot(touch_api=True)
    snapshot["operator_guidance"] = (
        "Candidate runtime is visible and compatible. Complete synthetic/SLO acceptance before changing gateway traffic."
        if snapshot.get("cutover_preconditions_met") else
        "Do not cut over: candidate runtime is absent/incompatible or deployment skew is unresolved."
    )
    return snapshot


@router.get("/high-availability")
def high_availability(identity: Identity = Depends(get_identity)):
    _admin(identity)
    snapshot = high_availability_snapshot(touch_api=True)
    snapshot["operator_guidance"] = {
        "HEALTHY": "HA replica targets and singleton scheduler leadership are observed.",
        "DEGRADED": "Core can continue serving, but one or more redundancy targets are below policy.",
        "UNSAFE": "Stop deployment changes and resolve version skew or scheduler split-brain risk.",
        "UNKNOWN": "Component registry is unavailable; do not claim HA certification from telemetry.",
        "DISABLED": "HA overlay is not enabled for this deployment.",
    }.get(snapshot.get("status"), "Inspect HA topology diagnostics.")
    return snapshot


@router.get("/multi-host-topology")
def multi_host_topology(identity: Identity = Depends(get_identity)):
    _admin(identity)
    snapshot = multi_host_topology_snapshot(touch_api=True)
    snapshot["operator_guidance"] = {
        "HEALTHY": "Required API/worker roles are spread across independent failure domains. Keep external LB and authoritative DB/evidence fencing enabled.",
        "DEGRADED": "Serving capacity remains, but anti-affinity/failure-domain targets are not fully met. Do not claim multi-host certification.",
        "UNSAFE": "STOP topology changes: resolve runtime version skew or node/failure-domain identity conflicts.",
        "UNKNOWN": "Ephemeral component registry is unavailable; do not infer multi-host placement safety.",
        "DISABLED": "Multi-host topology policy is not enabled for this deployment.",
    }.get(snapshot.get("status"), "Inspect multi-host topology diagnostics.")
    return snapshot


@router.get("/production-certification")
def production_certification(profile: str | None = None, identity: Identity = Depends(get_identity), db: Session = Depends(get_db)):
    _admin(identity)
    try:
        snapshot = runtime_acceptance_snapshot(db, profile=profile)
    except ValueError as exc:
        raise HTTPException(400, str(exc))
    snapshot["operator_guidance"] = {
        "NO_GO": "STOP rollout/production acceptance: resolve failed topology, authority, incident or DB-pool gates before continuing.",
        "CONDITIONAL": "Runtime prerequisites are acceptable, but target-host load/failover evidence and human approval are still required.",
        "GO": "Technical acceptance evidence passed; human change approval is still required before production authorization.",
    }.get(snapshot.get("decision"), "Inspect certification checks.")
    return snapshot


@router.get("/release-provenance")
def release_provenance(identity: Identity = Depends(get_identity)):
    _admin(identity)
    settings = get_settings()
    if not settings.release_provenance_registry_enabled:
        return {
            "schema": "mgc-release-provenance-registry-v1",
            "status": "DISABLED",
            "production_authorized": False,
            "operator_guidance": "Enable the controlled release provenance registry only on approved release-evidence storage.",
        }
    snapshot = registry_summary(settings.release_provenance_registry_path)
    governance = verify_governance(
        settings.release_provenance_registry_path,
        require_external_anchor=settings.release_provenance_require_external_anchor,
        require_worm_receipt=settings.release_provenance_require_worm_receipt,
        anchor_max_age_hours=settings.release_provenance_anchor_max_age_hours,
        checkpoint_max_age_hours=settings.release_provenance_checkpoint_max_age_hours,
    )
    snapshot["governance"] = {
        "status": governance.get("status"),
        "checkpoint_count": governance.get("checkpoint_count"),
        "external_anchor": governance.get("external_anchor"),
        "worm": governance.get("worm"),
        "key_lifecycle": governance.get("key_lifecycle"),
        "retention": governance.get("retention"),
        "warnings": governance.get("warnings"),
        "failures": governance.get("failures"),
        "production_authorized": False,
    }
    snapshot["operator_guidance"] = {
        "PASS": "Registry chain is valid; governance summary shows anchor/WORM/key/retention posture. Full offline verification remains required before approval.",
        "FAIL": "STOP release-evidence promotion: registry chain/object integrity is invalid.",
    }.get(snapshot.get("status"), "Inspect the controlled provenance registry.")
    return snapshot


@router.get("/authoritative-ha")
def authoritative_ha(identity: Identity = Depends(get_identity)):
    _admin(identity)
    snapshot = authoritative_ha_snapshot()
    snapshot["operator_guidance"] = {
        "HEALTHY": "Authoritative writes are permitted: PostgreSQL primary and evidence generation are proven safe.",
        "UNSAFE": "STOP writes/failover finalization. Verify PostgreSQL fencing, cluster identity and active evidence generation.",
        "DISABLED": "Authoritative DB/evidence HA fencing is not enabled for this deployment.",
    }.get(snapshot.get("status"), "Inspect authoritative database/evidence diagnostics.")
    return snapshot


@router.post("/health-samples")
def record_health_sample(identity: Identity = Depends(get_identity), db: Session = Depends(get_db)):
    _admin(identity)
    result = capture_health_samples(db)
    log_event(db, identity.user, "OPERATIONAL_HEALTH_SNAPSHOT", "operations", details={"samples": result["samples"], "overall_status": result["overall_status"]})
    return result


@router.get("/incident-evidence")
def incident_evidence(identity: Identity = Depends(get_identity), db: Session = Depends(get_db)):
    _admin(identity)
    return incident_evidence_snapshot(db)


@router.post("/incident-evidence/reconcile")
def incident_evidence_reconcile(identity: Identity = Depends(get_identity), db: Session = Depends(get_db)):
    _admin(identity)
    report = incident_evidence_snapshot(db)
    result = reconcile_automated_incident_evidence(db, report, actor=identity.user, materialize=None)
    log_event(db, identity.user, "AUTOMATED_INCIDENT_EVIDENCE_RECONCILED", "operations", details={
        "signals": result["signals"], "materialization_enabled": result["materialization_enabled"]
    })
    return result


@router.get("/incidents")
def incidents(limit: int = 100, identity: Identity = Depends(get_identity), db: Session = Depends(get_db)):
    _admin(identity)
    return {"items": list_incidents(db, limit=limit)}


@router.post("/incidents")
def incident_create(req: IncidentCreate, identity: Identity = Depends(get_identity), db: Session = Depends(get_db)):
    _admin(identity)
    try:
        row = create_incident(db, code=req.code, severity=req.severity, component=req.component, summary=req.summary,
                              actor=identity.user, impact_summary=req.impact_summary, detected_by=req.detected_by, evidence=req.evidence)
    except ValueError as exc:
        raise HTTPException(400, str(exc))
    log_event(db, identity.user, "PRODUCTION_INCIDENT_CREATED", "production_incident", row.id, {"code": row.code, "severity": row.severity, "component": row.component})
    return {"id": row.id, "code": row.code, "status": row.status, "severity": row.severity}


@router.patch("/incidents/{incident_id}")
def incident_update(incident_id: str, req: IncidentUpdate, identity: Identity = Depends(get_identity), db: Session = Depends(get_db)):
    _admin(identity)
    row = db.get(ProductionIncident, incident_id)
    if not row:
        raise HTTPException(404, "Incident not found")
    try:
        row = update_incident(db, row, actor=identity.user, status=req.status, severity=req.severity,
                              resolution_summary=req.resolution_summary, evidence=req.evidence)
    except ValueError as exc:
        raise HTTPException(400, str(exc))
    log_event(db, identity.user, "PRODUCTION_INCIDENT_UPDATED", "production_incident", row.id, {"status": row.status, "severity": row.severity})
    return {"id": row.id, "code": row.code, "status": row.status, "severity": row.severity, "resolved_at": row.resolved_at}


@router.get("/support-bundle")
def support_bundle(window_minutes: int | None = None, identity: Identity = Depends(get_identity), db: Session = Depends(get_db)):
    _admin(identity)
    payload, manifest = build_support_bundle(db, actor=identity.user, window_minutes=window_minutes)
    log_event(db, identity.user, "SUPPORT_BUNDLE_EXPORTED", "operations", details={"sha256": manifest["zip_sha256"], "bytes": manifest["zip_bytes"]})
    headers = {
        "Content-Disposition": f'attachment; filename="mgc-support-bundle-v{APP_VERSION}.zip"',
        "X-MGC-Bundle-SHA256": manifest["zip_sha256"],
    }
    return Response(content=payload, media_type="application/zip", headers=headers)


@router.get("/game-days")
def game_days(limit: int = 100, identity: Identity = Depends(get_identity), db: Session = Depends(get_db)):
    _admin(identity)
    return {"items": list_game_days(db, limit=limit)}


@router.post("/game-days")
def game_day_create(req: GameDayCreate, identity: Identity = Depends(get_identity), db: Session = Depends(get_db)):
    _admin(identity)
    try:
        row = create_game_day(db, code=req.code, name=req.name, mode=req.mode, actor=identity.user, notes=req.notes)
    except ValueError as exc:
        raise HTTPException(400, str(exc))
    log_event(db, identity.user, "OPERATIONS_GAME_DAY_CREATED", "operations_game_day", row.id, {"code": row.code, "mode": row.mode})
    return {"id": row.id, "code": row.code, "mode": row.mode, "status": row.status}


@router.post("/game-days/{run_id}/start")
def game_day_start(run_id: str, identity: Identity = Depends(get_identity), db: Session = Depends(get_db)):
    _admin(identity)
    row = db.get(OperationsGameDayRun, run_id)
    if not row:
        raise HTTPException(404, "Game day not found")
    try:
        row = start_game_day(db, row, actor=identity.user)
    except ValueError as exc:
        raise HTTPException(400, str(exc))
    log_event(db, identity.user, "OPERATIONS_GAME_DAY_STARTED", "operations_game_day", row.id, {"code": row.code})
    return {"id": row.id, "status": row.status, "started_at": row.started_at}


@router.get("/game-days/{run_id}")
def game_day_detail(run_id: str, identity: Identity = Depends(get_identity), db: Session = Depends(get_db)):
    _admin(identity)
    row = db.get(OperationsGameDayRun, run_id)
    if not row:
        raise HTTPException(404, "Game day not found")
    exercises = db.query(OperationsGameDayExercise).filter_by(run_id=row.id).order_by(OperationsGameDayExercise.exercise_code).all()
    return {
        "id": row.id, "code": row.code, "name": row.name, "mode": row.mode, "status": row.status,
        "external_gates": row.external_gate_evidence_json or {},
        "exercises": [{
            "id": x.id, "exercise_code": x.exercise_code, "component": x.component, "scenario_type": x.scenario_type,
            "status": x.status, "target_rto_seconds": x.target_rto_seconds, "target_rpo_seconds": x.target_rpo_seconds,
            "actual_rpo_seconds": x.actual_rpo_seconds, "runbook_ref": x.runbook_ref,
        } for x in exercises],
        "evaluation": evaluate_game_day(db, row),
    }


@router.patch("/game-days/{run_id}/exercises/{exercise_code}")
def game_day_exercise_update(run_id: str, exercise_code: str, req: GameDayExerciseUpdate, identity: Identity = Depends(get_identity), db: Session = Depends(get_db)):
    _admin(identity)
    row = db.query(OperationsGameDayExercise).filter_by(run_id=run_id, exercise_code=exercise_code).one_or_none()
    if not row:
        raise HTTPException(404, "Game-day exercise not found")
    payload = req.model_dump(exclude_none=True)
    from datetime import datetime
    for key in ("started_at","fault_injected_at","detected_at","mitigated_at","recovered_at","verified_at"):
        if key in payload and isinstance(payload[key], str):
            try:
                payload[key] = datetime.fromisoformat(payload[key].replace("Z", "+00:00"))
            except ValueError:
                raise HTTPException(400, f"Invalid timestamp for {key}")
    try:
        row = update_exercise(db, row, actor=identity.user, payload=payload)
    except ValueError as exc:
        raise HTTPException(400, str(exc))
    log_event(db, identity.user, "OPERATIONS_GAME_DAY_EXERCISE_UPDATED", "operations_game_day_exercise", row.id, {"exercise_code": row.exercise_code, "status": row.status})
    return {"id": row.id, "exercise_code": row.exercise_code, "status": row.status}


@router.patch("/game-days/{run_id}/external-gates")
def game_day_external_gates(run_id: str, req: GameDayExternalGates, identity: Identity = Depends(get_identity), db: Session = Depends(get_db)):
    _admin(identity)
    row = db.get(OperationsGameDayRun, run_id)
    if not row:
        raise HTTPException(404, "Game day not found")
    row = record_external_gates(db, row, evidence=req.evidence)
    log_event(db, identity.user, "OPERATIONS_GAME_DAY_EXTERNAL_GATES_UPDATED", "operations_game_day", row.id, {"gates": sorted((row.external_gate_evidence_json or {}).keys())})
    return {"id": row.id, "external_gates": row.external_gate_evidence_json}


@router.get("/game-days/{run_id}/evaluation")
def game_day_evaluation(run_id: str, identity: Identity = Depends(get_identity), db: Session = Depends(get_db)):
    _admin(identity)
    row = db.get(OperationsGameDayRun, run_id)
    if not row:
        raise HTTPException(404, "Game day not found")
    return evaluate_game_day(db, row)


@router.post("/game-days/{run_id}/finalize")
def game_day_finalize(run_id: str, confirm: str, identity: Identity = Depends(get_identity), db: Session = Depends(get_db)):
    _admin(identity)
    row = db.get(OperationsGameDayRun, run_id)
    if not row:
        raise HTTPException(404, "Game day not found")
    try:
        out = finalize_game_day(db, row, actor=identity.user, confirm=confirm)
    except ValueError as exc:
        raise HTTPException(400, str(exc))
    log_event(db, identity.user, "OPERATIONS_GAME_DAY_FINALIZED", "operations_game_day", row.id, {"decision": out["decision"], "deployment_authorized": False})
    return out


@router.get("/projections")
def projection_status(identity: Identity = Depends(get_identity), db: Session = Depends(get_db)):
    _admin(identity)
    return projection_health(db)


@router.get("/projections/outbox")
def projection_outbox(status: str | None = None, target: str | None = None, limit: int = 100, identity: Identity = Depends(get_identity), db: Session = Depends(get_db)):
    _admin(identity)
    return {"items": list_outbox(db, status=status, target=target, limit=limit)}


@router.post("/projections/process")
def projection_process(limit: int | None = None, identity: Identity = Depends(get_identity), db: Session = Depends(get_db)):
    _admin(identity)
    out = drain_projection_outbox(SessionLocal, limit=limit, worker_id=f"manual:{identity.user}")
    log_event(db, identity.user, "PROJECTION_OUTBOX_MANUAL_DRAIN", "projection_outbox", details={k: out.get(k) for k in ("claimed", "processed", "succeeded", "retry", "dead_letter", "superseded")})
    return out


@router.post("/projections/rebuild")
def projection_rebuild(target: str | None = None, project_code: str | None = None, manufacturing_area: str | None = None, identity: Identity = Depends(get_identity), db: Session = Depends(get_db)):
    _admin(identity)
    try:
        out = enqueue_rebuild(db, target=target, project_code=project_code, manufacturing_area=manufacturing_area)
    except ValueError as exc:
        raise HTTPException(400, str(exc))
    log_event(db, identity.user, "PROJECTION_REBUILD_ENQUEUED", "projection_outbox", details=out)
    return out


@router.post("/projections/dlq/{event_id}/replay")
def projection_dlq_replay(event_id: str, identity: Identity = Depends(get_identity), db: Session = Depends(get_db)):
    _admin(identity)
    row = replay_dead_letter(db, event_id)
    if not row:
        raise HTTPException(404, "Dead-letter event not found")
    log_event(db, identity.user, "PROJECTION_DLQ_REPLAYED", "projection_outbox", row.id, {"target": row.target})
    return {"id": row.id, "status": row.status, "attempt_count": row.attempt_count, "max_attempts": row.max_attempts}


@router.get("/integrity")
def domain_integrity_status(identity: Identity = Depends(get_identity), db: Session = Depends(get_db)):
    _admin(identity)
    return integrity_dashboard(db)


@router.get("/conflicts")
def edit_conflict_history(limit: int = 100, identity: Identity = Depends(get_identity), db: Session = Depends(get_db)):
    _admin(identity)
    limit = max(1, min(int(limit), 500))
    rows = db.query(EditConflictEvent).order_by(EditConflictEvent.created_at.desc()).limit(limit).all()
    return {"items": [{
        "id": x.id, "entity_type": x.entity_type, "entity_id": x.entity_id, "route": x.route,
        "expected_version": x.expected_version, "current_version": x.current_version,
        "created_at": x.created_at.isoformat(),
    } for x in rows]}
