from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import Identity, get_identity, is_engineering_admin
from app.db.models import PilotScenarioResult, PilotStudy, PilotTelemetryAggregate, PilotUsabilityIssue, Project
from app.db.session import get_db
from app.services.audit import log_event
from app.services.enterprise_security import security_posture
from app.services.integration_reconciliation import build_reconciliation_report
from app.services.pilot_acceptance import (
    DEFAULT_REQUIRED_ROLES,
    evaluate_pilot,
    normalize_policy,
    sanitize_telemetry_metadata,
)

router = APIRouter(tags=["pilot"])


def _admin(identity: Identity) -> None:
    if not is_engineering_admin(identity):
        raise HTTPException(403, "Engineering AI administrator group required")


def _pilot_or_404(db: Session, pilot_id: str) -> PilotStudy:
    row = db.get(PilotStudy, pilot_id)
    if not row:
        raise HTTPException(404, "Pilot study not found")
    return row


class PilotCreate(BaseModel):
    code: str = Field(min_length=2, max_length=96)
    project_code: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=2, max_length=255)
    mode: Literal["synthetic", "controlled"] = "controlled"
    required_roles: list[str] = Field(default_factory=lambda: list(DEFAULT_REQUIRED_ROLES), max_length=16)
    gate_policy: dict[str, Any] = Field(default_factory=dict)
    notes: str | None = Field(default=None, max_length=4000)


class ScenarioRecord(BaseModel):
    scenario_code: str = Field(min_length=1, max_length=96)
    role: str = Field(min_length=1, max_length=64)
    domain: str = Field(default="engineering", min_length=1, max_length=64)
    required: bool = True
    status: Literal["not_run", "pass", "fail", "blocked"] = "not_run"
    baseline_seconds: float | None = Field(default=None, ge=0)
    mgc_seconds: float | None = Field(default=None, ge=0)
    expected_evidence_count: int = Field(default=0, ge=0, le=10000)
    evidence_count: int = Field(default=0, ge=0, le=10000)
    blocker_severity: Literal["info", "medium", "high", "critical"] | None = None
    usability_rating: float | None = Field(default=None, ge=1, le=5)
    feedback_category: str | None = Field(default=None, max_length=64)


class TelemetryAggregate(BaseModel):
    period_start: datetime
    role: str = Field(min_length=1, max_length=64)
    surface: str = Field(min_length=1, max_length=96)
    sessions: int = Field(default=0, ge=0, le=1_000_000)
    completions: int = Field(default=0, ge=0, le=1_000_000)
    errors: int = Field(default=0, ge=0, le=1_000_000)
    total_duration_seconds: float = Field(default=0, ge=0)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ExternalGateEvidence(BaseModel):
    gates: dict[str, Any]


class UsabilityIssueCreate(BaseModel):
    issue_code: str = Field(min_length=2, max_length=96)
    role: str = Field(default="all", min_length=1, max_length=64)
    surface: str = Field(default="project_workspace", min_length=1, max_length=96)
    category: str = Field(default="usability", min_length=1, max_length=64)
    severity: Literal["info", "medium", "high", "critical"] = "medium"
    title: str = Field(min_length=2, max_length=255)
    problem_statement: str = Field(min_length=2, max_length=4000)
    remediation: str | None = Field(default=None, max_length=4000)
    occurrence_count: int = Field(default=1, ge=1, le=1_000_000)
    evidence: dict[str, Any] = Field(default_factory=dict)


class UsabilityIssueUpdate(BaseModel):
    status: Literal["open", "accepted", "fixed", "verified", "closed"] | None = None
    remediation: str | None = Field(default=None, max_length=4000)
    occurrence_count: int | None = Field(default=None, ge=1, le=1_000_000)
    evidence: dict[str, Any] | None = None
    verification: dict[str, Any] | None = None


def _view(p: PilotStudy) -> dict[str, Any]:
    return {
        "id": p.id, "code": p.code, "project_code": p.project_code, "name": p.name,
        "mode": p.mode, "status": p.status, "required_roles": p.required_roles or [],
        "gate_policy": normalize_policy(p.gate_policy_json),
        "external_gate_evidence": p.external_gate_evidence_json or {},
        "final_decision": p.final_decision,
        "started_at": p.started_at.isoformat() if p.started_at else None,
        "completed_at": p.completed_at.isoformat() if p.completed_at else None,
    }


def _ux_issue_view(x: PilotUsabilityIssue) -> dict[str, Any]:
    return {
        "id": x.id, "pilot_id": x.pilot_id, "project_code": x.project_code, "issue_code": x.issue_code,
        "role": x.role, "surface": x.surface, "category": x.category, "severity": x.severity,
        "title": x.title, "problem_statement": x.problem_statement, "remediation": x.remediation,
        "status": x.status, "occurrence_count": x.occurrence_count, "evidence": x.evidence_json or {},
        "verification": x.verification_json or {}, "closed_at": x.closed_at.isoformat() if x.closed_at else None,
    }


@router.get("/pilot/studies")
def list_pilots(project_code: str | None = None, identity: Identity = Depends(get_identity), db: Session = Depends(get_db)):
    _admin(identity)
    stmt = select(PilotStudy).order_by(PilotStudy.created_at.desc())
    if project_code:
        stmt = stmt.where(PilotStudy.project_code == project_code)
    return [_view(x) for x in db.scalars(stmt).all()]


@router.post("/pilot/studies")
def create_pilot(req: PilotCreate, identity: Identity = Depends(get_identity), db: Session = Depends(get_db)):
    _admin(identity)
    if not db.scalar(select(Project).where(Project.code == req.project_code)):
        raise HTTPException(404, "Project not found")
    if db.scalar(select(PilotStudy).where(PilotStudy.code == req.code.strip())):
        raise HTTPException(409, "Pilot code already exists")
    roles = [x.strip().lower() for x in req.required_roles if x.strip()]
    if not roles:
        raise HTTPException(400, "At least one required role is required")
    row = PilotStudy(
        code=req.code.strip(), project_code=req.project_code, name=req.name.strip(), mode=req.mode,
        status="planned", required_roles=list(dict.fromkeys(roles)), gate_policy_json=normalize_policy(req.gate_policy),
        notes=req.notes, created_by=identity.user,
    )
    db.add(row); db.commit(); db.refresh(row)
    log_event(db, identity.user, "PILOT_CREATE", "pilot_study", row.id, {"code": row.code, "project_code": row.project_code, "mode": row.mode})
    return _view(row)


@router.post("/pilot/studies/{pilot_id}/start")
def start_pilot(pilot_id: str, identity: Identity = Depends(get_identity), db: Session = Depends(get_db)):
    _admin(identity); row = _pilot_or_404(db, pilot_id)
    row.status = "running"; row.started_at = row.started_at or datetime.now(timezone.utc)
    db.commit(); db.refresh(row)
    log_event(db, identity.user, "PILOT_START", "pilot_study", row.id, {})
    return _view(row)


@router.post("/pilot/studies/{pilot_id}/scenarios")
def record_scenario(pilot_id: str, req: ScenarioRecord, identity: Identity = Depends(get_identity), db: Session = Depends(get_db)):
    _admin(identity); pilot = _pilot_or_404(db, pilot_id)
    row = db.scalar(select(PilotScenarioResult).where(
        PilotScenarioResult.pilot_id == pilot.id,
        PilotScenarioResult.scenario_code == req.scenario_code,
        PilotScenarioResult.role == req.role.lower(),
    ))
    values = req.model_dump()
    values["role"] = req.role.lower(); values["domain"] = req.domain.lower()
    if row:
        for k, v in values.items(): setattr(row, k, v)
    else:
        row = PilotScenarioResult(pilot_id=pilot.id, **values); db.add(row)
    db.commit(); db.refresh(row)
    log_event(db, identity.user, "PILOT_SCENARIO_RECORD", "pilot_study", pilot.id, {"scenario_code": row.scenario_code, "role": row.role, "status": row.status})
    return {"id": row.id, **values}


@router.post("/pilot/studies/{pilot_id}/telemetry")
def record_telemetry(pilot_id: str, req: TelemetryAggregate, identity: Identity = Depends(get_identity), db: Session = Depends(get_db)):
    _admin(identity); pilot = _pilot_or_404(db, pilot_id)
    try:
        metadata = sanitize_telemetry_metadata(req.metadata)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    if req.completions > req.sessions or req.errors > req.sessions:
        raise HTTPException(400, "Telemetry completions/errors cannot exceed sessions")
    row = PilotTelemetryAggregate(
        pilot_id=pilot.id, period_start=req.period_start, role=req.role.lower(), surface=req.surface,
        sessions=req.sessions, completions=req.completions, errors=req.errors,
        total_duration_seconds=req.total_duration_seconds, metadata_json=metadata,
    )
    db.add(row); db.commit(); db.refresh(row)
    log_event(db, identity.user, "PILOT_TELEMETRY_AGGREGATE", "pilot_study", pilot.id, {"role": row.role, "surface": row.surface, "sessions": row.sessions})
    return {"id": row.id, "privacy": "aggregate_only"}


@router.patch("/pilot/studies/{pilot_id}/external-gates")
def update_external_gates(pilot_id: str, req: ExternalGateEvidence, identity: Identity = Depends(get_identity), db: Session = Depends(get_db)):
    _admin(identity); pilot = _pilot_or_404(db, pilot_id)
    allowed = set(normalize_policy(pilot.gate_policy_json).get("required_external_gates", []))
    current = dict(pilot.external_gate_evidence_json or {})
    for code, raw in req.gates.items():
        if code not in allowed:
            raise HTTPException(400, f"Unknown external pilot gate: {code}")
        if isinstance(raw, str): raw = {"status": raw}
        if not isinstance(raw, dict): raise HTTPException(400, f"Invalid evidence for {code}")
        status = str(raw.get("status") or "NOT_RUN").upper()
        if status not in {"PASS", "FAIL", "NOT_RUN"}: raise HTTPException(400, f"Invalid status for {code}")
        current[code] = {"status": status, "evidence_ref": str(raw.get("evidence_ref") or "")[:512], "recorded_at": datetime.now(timezone.utc).isoformat()}
    pilot.external_gate_evidence_json = current
    db.commit(); db.refresh(pilot)
    log_event(db, identity.user, "PILOT_EXTERNAL_GATE_UPDATE", "pilot_study", pilot.id, {"gates": sorted(req.gates)})
    return _view(pilot)


@router.get("/pilot/studies/{pilot_id}/usability-issues")
def list_usability_issues(pilot_id: str, identity: Identity = Depends(get_identity), db: Session = Depends(get_db)):
    _admin(identity); _pilot_or_404(db, pilot_id)
    rows=db.scalars(select(PilotUsabilityIssue).where(PilotUsabilityIssue.pilot_id==pilot_id).order_by(PilotUsabilityIssue.created_at.desc())).all()
    return [_ux_issue_view(x) for x in rows]


@router.post("/pilot/studies/{pilot_id}/usability-issues")
def create_usability_issue(pilot_id: str, req: UsabilityIssueCreate, identity: Identity = Depends(get_identity), db: Session = Depends(get_db)):
    _admin(identity); pilot=_pilot_or_404(db, pilot_id)
    if db.scalar(select(PilotUsabilityIssue).where(PilotUsabilityIssue.pilot_id==pilot_id, PilotUsabilityIssue.issue_code==req.issue_code.strip())):
        raise HTTPException(409, "Usability issue code already exists for this pilot")
    forbidden={"user","user_id","username","email","ip","ip_address","query","query_text","vin","vehicle_identifier","document_id","employee","person"}
    keys={str(k).lower() for k in req.evidence}
    if keys & forbidden: raise HTTPException(400, "Usability issue evidence must not contain participant/content identifiers")
    row=PilotUsabilityIssue(pilot_id=pilot.id, project_code=pilot.project_code, issue_code=req.issue_code.strip(), role=req.role.strip().lower(), surface=req.surface.strip(), category=req.category.strip(), severity=req.severity, title=req.title.strip(), problem_statement=req.problem_statement.strip(), remediation=req.remediation, occurrence_count=req.occurrence_count, evidence_json=req.evidence, created_by=identity.user)
    db.add(row); db.commit(); db.refresh(row)
    log_event(db, identity.user, "PILOT_UX_ISSUE_CREATE", "pilot_usability_issue", row.id, {"pilot_id":pilot.id,"issue_code":row.issue_code,"severity":row.severity})
    return _ux_issue_view(row)


@router.patch("/pilot/studies/{pilot_id}/usability-issues/{issue_id}")
def update_usability_issue(pilot_id: str, issue_id: str, req: UsabilityIssueUpdate, identity: Identity = Depends(get_identity), db: Session = Depends(get_db)):
    _admin(identity); _pilot_or_404(db, pilot_id); row=db.get(PilotUsabilityIssue, issue_id)
    if not row or row.pilot_id!=pilot_id: raise HTTPException(404, "Usability issue not found")
    if req.status is not None: row.status=req.status
    if req.remediation is not None: row.remediation=req.remediation
    if req.occurrence_count is not None: row.occurrence_count=req.occurrence_count
    if req.evidence is not None: row.evidence_json=req.evidence
    if req.verification is not None: row.verification_json=req.verification
    if row.status in {"verified","closed"}:
        if not row.remediation or not row.verification_json: raise HTTPException(400, "Closing a usability issue requires remediation and verification evidence")
        row.closed_by=identity.user; row.closed_at=datetime.now(timezone.utc)
    else:
        row.closed_by=None; row.closed_at=None
    db.commit(); db.refresh(row)
    log_event(db, identity.user, "PILOT_UX_ISSUE_UPDATE", "pilot_usability_issue", row.id, {"pilot_id":pilot_id,"status":row.status})
    return _ux_issue_view(row)


@router.get("/pilot/studies/{pilot_id}/evaluation")
def pilot_evaluation(pilot_id: str, identity: Identity = Depends(get_identity), db: Session = Depends(get_db)):
    _admin(identity); pilot = _pilot_or_404(db, pilot_id)
    reconciliation = build_reconciliation_report(db, pilot.project_code) if pilot.mode == "controlled" else None
    return evaluate_pilot(db, pilot, reconciliation_report=reconciliation, security_posture=security_posture())


@router.post("/pilot/studies/{pilot_id}/finalize")
def finalize_pilot(pilot_id: str, confirm: str, identity: Identity = Depends(get_identity), db: Session = Depends(get_db)):
    _admin(identity); pilot = _pilot_or_404(db, pilot_id)
    if confirm != "FINALIZE_PILOT":
        raise HTTPException(400, "Explicit confirm=FINALIZE_PILOT is required")
    reconciliation = build_reconciliation_report(db, pilot.project_code) if pilot.mode == "controlled" else None
    report = evaluate_pilot(db, pilot, reconciliation_report=reconciliation, security_posture=security_posture())
    pilot.final_decision = report["decision"]
    pilot.final_evaluation_json = report
    pilot.status = "completed"
    pilot.completed_at = datetime.now(timezone.utc)
    pilot.closed_by = identity.user
    db.commit(); db.refresh(pilot)
    log_event(db, identity.user, "PILOT_FINALIZE", "pilot_study", pilot.id, {"decision": pilot.final_decision})
    return {"pilot": _view(pilot), "evaluation": report, "deployment_authorized": False}
