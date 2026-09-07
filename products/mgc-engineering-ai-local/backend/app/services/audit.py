import hashlib
import json
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import AuditEvent, Document, DocumentActivity, DocumentActivityState


def add_audit_event(db: Session, user: str, action: str, entity_type: str | None = None, entity_id: str | None = None, details: dict | None = None) -> AuditEvent:
    row = AuditEvent(user=user, action=action, entity_type=entity_type, entity_id=entity_id, details=details or {})
    db.add(row)
    return row


def log_event(db: Session, user: str, action: str, entity_type: str | None = None, entity_id: str | None = None, details: dict | None = None):
    row = add_audit_event(db, user, action, entity_type, entity_id, details)
    db.commit()
    return row


def _activity_digest(document_id: str, user: str, action: str, summary: str, details: dict, created_at: datetime, previous_hash: str) -> str:
    payload = {
        "document_id": document_id,
        "user": user,
        "action": action,
        "summary": summary,
        "details": details,
        "created_at": created_at.astimezone(timezone.utc).isoformat(),
        "previous_hash": previous_hash,
    }
    canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def log_document_activity(
    db: Session, document_id: str, user: str, action: str, summary: str, details: dict | None = None
) -> DocumentActivity:
    # Serialize the audit head per document on PostgreSQL. SQLite ignores FOR UPDATE,
    # which is acceptable for local single-process tests/pilots.
    document = db.scalar(select(Document).where(Document.id == document_id).with_for_update())
    if not document:
        raise ValueError(f"Document not found: {document_id}")

    state = db.get(DocumentActivityState, document_id)
    if state is None:
        # v3.5 creates state with the first event. If rows already exist without a
        # state, initialize from their verified tail rather than silently discarding it.
        existing = db.scalars(
            select(DocumentActivity)
            .where(DocumentActivity.document_id == document_id)
            .order_by(DocumentActivity.created_at.asc(), DocumentActivity.id.asc())
        ).all()
        state = DocumentActivityState(
            document_id=document_id,
            head_hash=existing[-1].event_hash if existing else "",
            event_count=len(existing),
        )
        db.add(state)
        db.flush()

    previous_hash = state.head_hash or ""
    created_at = datetime.now(timezone.utc)
    clean_details = details or {}
    event_hash = _activity_digest(document_id, user, action, summary, clean_details, created_at, previous_hash)
    row = DocumentActivity(
        document_id=document_id, user=user, action=action, summary=summary, details=clean_details,
        previous_hash=previous_hash, event_hash=event_hash, created_at=created_at,
    )
    db.add(row)
    state.head_hash = event_hash
    state.event_count = int(state.event_count or 0) + 1
    state.updated_at = created_at
    db.commit()
    db.refresh(row)
    return row

def document_activity_history(db: Session, document_id: str, limit: int = 200) -> tuple[list[DocumentActivity], bool]:
    # Verify the complete chain and its separately stored head/count anchor, then
    # return only the requested tail. The anchor catches deletion of the newest row.
    all_rows = db.scalars(
        select(DocumentActivity)
        .where(DocumentActivity.document_id == document_id)
        .order_by(DocumentActivity.created_at.asc(), DocumentActivity.id.asc())
    ).all()
    previous_hash = ""
    valid = True
    for row in all_rows:
        expected = _activity_digest(row.document_id, row.user, row.action, row.summary, row.details or {}, row.created_at, previous_hash)
        if row.previous_hash != previous_hash or row.event_hash != expected:
            valid = False
        previous_hash = row.event_hash

    state = db.get(DocumentActivityState, document_id)
    if all_rows:
        if state is None or state.head_hash != previous_hash or int(state.event_count or 0) != len(all_rows):
            valid = False
    elif state is not None and (state.head_hash or int(state.event_count or 0)):
        valid = False

    return list(reversed(all_rows[-max(1, min(limit, 500)):])), valid

