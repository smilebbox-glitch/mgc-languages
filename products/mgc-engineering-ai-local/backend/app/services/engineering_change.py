import hashlib
import json
import secrets
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import ChangeApproval, ChangeEvent, ChangeEventState, ChangeRequest, DesignReview, Document, PartRevision
from app.services.change_impact import analyze_change_impact
from app.db.unit_of_work import UnitOfWork

ALLOWED_PRIORITIES = {"low", "normal", "high", "urgent"}
TERMINAL_STATUSES = {"implemented", "rejected", "cancelled"}


def _canonicalize(value):
    if isinstance(value, dict):
        return {k: _canonicalize(value[k]) for k in sorted(value)}
    if isinstance(value, list):
        normalized = [_canonicalize(v) for v in value]
        return sorted(normalized, key=lambda x: json.dumps(x, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str))
    return value


def _impact_digest(impact: dict) -> str:
    canonical = json.dumps(_canonicalize(impact), ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _code(prefix: str) -> str:
    return f"{prefix}-{_now():%Y%m%d}-{secrets.token_hex(3).upper()}"


def _event_digest(change_id: str, user: str, action: str, summary: str, details: dict, created_at: datetime, previous_hash: str) -> str:
    payload = {
        "change_id": change_id, "user": user, "action": action, "summary": summary,
        "details": details, "created_at": created_at.astimezone(timezone.utc).isoformat(), "previous_hash": previous_hash,
    }
    canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def add_change_event(db: Session, change_id: str, user: str, action: str, summary: str, details: dict | None = None) -> ChangeEvent:
    change = db.scalar(select(ChangeRequest).where(ChangeRequest.id == change_id).with_for_update())
    if not change:
        raise ValueError("Change request not found")
    state = db.scalar(select(ChangeEventState).where(ChangeEventState.change_id == change_id).with_for_update())
    if state is None:
        existing = db.scalars(select(ChangeEvent).where(ChangeEvent.change_id == change_id).order_by(ChangeEvent.created_at.asc(), ChangeEvent.id.asc())).all()
        state = ChangeEventState(change_id=change_id, head_hash=existing[-1].event_hash if existing else "", event_count=len(existing))
        db.add(state); db.flush()
    created_at = _now(); details = details or {}; previous = state.head_hash or ""
    digest = _event_digest(change_id, user, action, summary, details, created_at, previous)
    event = ChangeEvent(change_id=change_id, user=user, action=action, summary=summary, details=details, previous_hash=previous, event_hash=digest, created_at=created_at)
    db.add(event); state.head_hash = digest; state.event_count = int(state.event_count or 0) + 1; state.updated_at = created_at
    return event


def log_change_event(db: Session, change_id: str, user: str, action: str, summary: str, details: dict | None = None) -> ChangeEvent:
    event = add_change_event(db, change_id, user, action, summary, details)
    db.commit(); db.refresh(event); return event


def change_history(db: Session, change_id: str, limit: int = 200) -> tuple[list[ChangeEvent], bool]:
    rows = db.scalars(select(ChangeEvent).where(ChangeEvent.change_id == change_id).order_by(ChangeEvent.created_at.asc(), ChangeEvent.id.asc())).all()
    previous = ""; valid = True
    for row in rows:
        expected = _event_digest(row.change_id, row.user, row.action, row.summary, row.details or {}, row.created_at, previous)
        if row.previous_hash != previous or row.event_hash != expected: valid = False
        previous = row.event_hash
    state = db.get(ChangeEventState, change_id)
    if rows:
        if state is None or state.head_hash != previous or int(state.event_count or 0) != len(rows): valid = False
    elif state is not None and (state.head_hash or int(state.event_count or 0)): valid = False
    return list(reversed(rows[-max(1, min(limit, 500)):])), valid




def _lock_change(db: Session, change: ChangeRequest) -> ChangeRequest:
    locked = db.scalar(select(ChangeRequest).where(ChangeRequest.id == change.id).with_for_update())
    if not locked:
        raise ValueError("Change request not found")
    return locked

def _assert_revision_visible(db: Session, part_number: str, revision: str, allowed_document_ids: set[str]) -> None:
    rev = db.scalar(select(PartRevision).where(PartRevision.part_number == part_number, PartRevision.revision == revision))
    if not rev: raise ValueError(f"Revision {part_number} {revision} not found")
    docs = db.scalars(select(Document).where(Document.part_number == part_number, Document.revision == revision)).all()
    if not any(d.id in allowed_document_ids for d in docs): raise ValueError("Revision is not visible to the current identity")


def create_change(db: Session, *, title: str, description: str | None, reason: str, part_number: str, from_revision: str, to_revision: str, priority: str, user: str, allowed_document_ids: set[str]) -> ChangeRequest:
    pn, fr, tr = part_number.upper().strip(), from_revision.upper().strip(), to_revision.upper().strip()
    if priority not in ALLOWED_PRIORITIES: raise ValueError("Unsupported priority")
    if fr == tr: raise ValueError("From and to revisions must be different")
    _assert_revision_visible(db, pn, fr, allowed_document_ids); _assert_revision_visible(db, pn, tr, allowed_document_ids)
    row = ChangeRequest(code=_code("ECR"), title=title.strip(), description=description, reason=reason.strip(), part_number=pn, from_revision=fr, to_revision=tr, status="draft", priority=priority, owner=user, created_by=user)
    with UnitOfWork(db) as uow:
        db.add(row); db.flush()
        add_change_event(db, row.id, user, "ECR_CREATED", f"Создан запрос изменения {row.code}", {"part_number": pn, "from_revision": fr, "to_revision": tr, "priority": priority, "reason": reason, "row_version": row.row_version})
        uow.commit()
    db.refresh(row)
    return row


def run_change_impact(db: Session, change: ChangeRequest, user: str, allowed_document_ids: set[str]) -> ChangeRequest:
    change = _lock_change(db, change)
    if change.status in TERMINAL_STATUSES: raise ValueError("Change is already closed")
    impact = analyze_change_impact(db, change.part_number or "", change.from_revision or "", change.to_revision or "", allowed_document_ids=allowed_document_ids)
    risk = float(impact.get("risk_score") or 0)
    change.impact_json = impact
    change.affected_parts = impact.get("impacted_parts") or []
    change.affected_document_ids = [d["id"] for d in impact.get("impacted_documents") or []]
    change.risk_level = "critical" if risk >= 70 else "high" if risk >= 45 else "medium" if risk >= 20 else "low"
    review = db.scalar(select(DesignReview).where(DesignReview.part_number == change.part_number, DesignReview.revision == change.to_revision).order_by(DesignReview.created_at.desc()))
    if review and set(review.evidence_document_ids or []).issubset(allowed_document_ids): change.design_review_id = review.id
    evidence_docs = db.scalars(select(Document).where(Document.id.in_(change.affected_document_ids or []))).all() if change.affected_document_ids else []
    evidence = sorted([{"id": d.id, "sha256": d.sha256} for d in evidence_docs], key=lambda x: x["id"])
    meta = dict(change.metadata_json or {})
    meta["impact_evidence"] = evidence
    meta["impact_evidence_fingerprint"] = hashlib.sha256(json.dumps(evidence, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    meta["impact_digest"] = _impact_digest(impact)
    change.metadata_json = meta
    change.status = "impact_review"
    with UnitOfWork(db) as uow:
        add_change_event(db, change.id, user, "IMPACT_ANALYZED", f"Impact analysis завершён: риск {risk:.0f}/100", {"risk_score": risk, "risk_level": change.risk_level, "affected_parts": len(change.affected_parts or []), "affected_documents": len(change.affected_document_ids or []), "design_review_id": change.design_review_id, "previous_version": change.row_version})
        uow.commit()
    db.refresh(change)
    return change


def submit_for_approval(db: Session, change: ChangeRequest, user: str) -> ChangeRequest:
    change = _lock_change(db, change)
    if change.status != "impact_review" or not change.impact_json: raise ValueError("Impact analysis must be completed first")
    change.status = "approval"
    with UnitOfWork(db) as uow:
        add_change_event(db, change.id, user, "SUBMITTED_FOR_APPROVAL", "Изменение отправлено на техническое согласование", {"previous_version": change.row_version})
        uow.commit()
    db.refresh(change)
    return change


def decide_change(db: Session, change: ChangeRequest, *, stage: str, decision: str, comment: str | None, user: str, is_admin: bool, allowed_document_ids: set[str] | None = None) -> ChangeRequest:
    change = _lock_change(db, change)
    if change.status != "approval": raise ValueError("Change is not awaiting approval")
    if decision not in {"approved", "rejected"}: raise ValueError("Decision must be approved or rejected")
    if stage not in {"technical_review", "final_approval"}: raise ValueError("Unsupported approval stage")
    if user == change.created_by: raise PermissionError("Author cannot approve their own change")
    if stage == "final_approval" and not is_admin: raise PermissionError("Engineering admin required for final approval")
    existing_stage_approval = db.scalar(select(ChangeApproval).where(ChangeApproval.change_id == change.id, ChangeApproval.stage == stage, ChangeApproval.decision == "approved").order_by(ChangeApproval.created_at.desc()))
    if existing_stage_approval and decision == "approved":
        raise ValueError(f"{stage} is already approved")
    if stage == "final_approval":
        technical = db.scalar(select(ChangeApproval).where(ChangeApproval.change_id == change.id, ChangeApproval.stage == "technical_review", ChangeApproval.decision == "approved").order_by(ChangeApproval.created_at.desc()))
        if not technical: raise ValueError("Technical review must be approved first")
        if technical.approver == user:
            raise PermissionError("Final approver must be different from the technical reviewer")
        expected_evidence = (change.metadata_json or {}).get("impact_evidence") or []
        current_docs = db.scalars(select(Document).where(Document.id.in_([x.get("id") for x in expected_evidence if x.get("id")]))).all() if expected_evidence else []
        current_evidence = sorted([{"id": d.id, "sha256": d.sha256} for d in current_docs], key=lambda x: x["id"])
        current_fp = hashlib.sha256(json.dumps(current_evidence, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        stale_reason = None
        if not expected_evidence or current_fp != (change.metadata_json or {}).get("impact_evidence_fingerprint"):
            stale_reason = "source document fingerprint changed"
        if allowed_document_ids is not None:
            fresh_impact = analyze_change_impact(db, change.part_number or "", change.from_revision or "", change.to_revision or "", allowed_document_ids=allowed_document_ids)
            if _impact_digest(fresh_impact) != (change.metadata_json or {}).get("impact_digest"):
                stale_reason = stale_reason or "impact scope changed"
        if stale_reason:
            change.status = "impact_review"
            with UnitOfWork(db) as uow:
                add_change_event(db, change.id, user, "IMPACT_STALE", "Доказательная база или область влияния изменилась — требуется повторный impact analysis", {"reason": stale_reason, "previous_version": change.row_version})
                uow.commit()
            raise ValueError("Impact evidence changed; rerun impact analysis before final approval")
        if change.risk_level in {"high", "critical"}:
            review = db.get(DesignReview, change.design_review_id) if change.design_review_id else None
            if not review or getattr(review.status, "value", review.status) != "approved":
                raise ValueError("High-risk change requires an approved Design Review before ECO release")
    approval = ChangeApproval(change_id=change.id, stage=stage, approver=user, decision=decision, comment=comment)
    db.add(approval)
    if decision == "rejected":
        change.status = "rejected"
    elif stage == "final_approval":
        change.status = "approved"; change.eco_code = change.eco_code or _code("ECO")
    label = "Техническое согласование" if stage == "technical_review" else "Финальное согласование"
    with UnitOfWork(db) as uow:
        add_change_event(db, change.id, user, "CHANGE_DECISION", f"{label}: {decision}", {"stage": stage, "decision": decision, "comment": comment, "eco_code": change.eco_code, "previous_version": change.row_version})
        uow.commit()
    db.refresh(change)
    return change


def start_implementation(db: Session, change: ChangeRequest, *, implementation_plan: dict, verification_plan: dict, user: str) -> ChangeRequest:
    change = _lock_change(db, change)
    if change.status != "approved": raise ValueError("ECO must be approved before implementation")
    change.implementation_plan = implementation_plan or {}; change.verification_plan = verification_plan or {}; change.owner = user; change.status = "implementation"
    with UnitOfWork(db) as uow:
        add_change_event(db, change.id, user, "IMPLEMENTATION_STARTED", f"Начато внедрение {change.eco_code or change.code}", {"implementation_plan": change.implementation_plan, "verification_plan": change.verification_plan, "previous_version": change.row_version})
        uow.commit()
    db.refresh(change)
    return change


def complete_change(db: Session, change: ChangeRequest, *, verification_result: str, user: str) -> ChangeRequest:
    change = _lock_change(db, change)
    if change.status != "implementation": raise ValueError("Change is not in implementation")
    if not verification_result.strip(): raise ValueError("Verification result is required")
    change.status = "implemented"; change.completed_at = _now(); meta = dict(change.metadata_json or {}); meta["verification_result"] = verification_result.strip(); change.metadata_json = meta
    with UnitOfWork(db) as uow:
        add_change_event(db, change.id, user, "IMPLEMENTED", f"Изменение {change.eco_code or change.code} внедрено", {"verification_result": verification_result.strip(), "previous_version": change.row_version})
        uow.commit()
    db.refresh(change)
    return change


def serialize_change(db: Session, change: ChangeRequest, include_history: bool = False) -> dict:
    approvals = db.scalars(select(ChangeApproval).where(ChangeApproval.change_id == change.id).order_by(ChangeApproval.created_at.asc())).all()
    payload = {
        "id": change.id, "row_version": change.row_version, "code": change.code, "eco_code": change.eco_code, "title": change.title, "description": change.description,
        "reason": change.reason, "part_number": change.part_number, "from_revision": change.from_revision, "to_revision": change.to_revision,
        "status": change.status, "priority": change.priority, "risk_level": change.risk_level, "owner": change.owner, "created_by": change.created_by,
        "impact": change.impact_json or {}, "affected_parts": change.affected_parts or [], "affected_document_ids": change.affected_document_ids or [],
        "design_review_id": change.design_review_id, "implementation_plan": change.implementation_plan or {}, "verification_plan": change.verification_plan or {},
        "metadata": change.metadata_json or {}, "created_at": change.created_at.isoformat(), "updated_at": change.updated_at.isoformat(),
        "completed_at": change.completed_at.isoformat() if change.completed_at else None,
        "approvals": [{"id": a.id, "stage": a.stage, "approver": a.approver, "decision": a.decision, "comment": a.comment, "created_at": a.created_at.isoformat()} for a in approvals],
    }
    if include_history:
        events, valid = change_history(db, change.id)
        payload["history_integrity_valid"] = valid
        payload["events"] = [{"id": e.id, "user": e.user, "action": e.action, "summary": e.summary, "details": e.details, "event_hash": e.event_hash, "created_at": e.created_at.isoformat()} for e in events]
    return payload
