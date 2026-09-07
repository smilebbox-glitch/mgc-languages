from datetime import datetime, timezone
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import AuditEvent, BOMItem, Document, EvidencePack, PartRevision, ValidationIssue


def build_evidence_pack(db: Session, part_number: str, revision: str | None, user: str, pack_type: str = "engineering", allowed_document_ids: set[str] | None = None) -> EvidencePack:
    pn = part_number.upper()
    q = select(Document).where(Document.part_number == pn)
    if revision:
        q = q.where(Document.revision == revision.upper())
    docs = db.scalars(q).all()
    if allowed_document_ids is not None:
        docs = [d for d in docs if d.id in allowed_document_ids]
    if not docs:
        raise ValueError("No visible evidence for requested part/revision")
    bom_q = select(BOMItem).where(BOMItem.parent_part_number == pn)
    if revision:
        bom_q = bom_q.where(BOMItem.parent_revision == revision.upper())
    bom = db.scalars(bom_q).all()
    if allowed_document_ids is not None:
        bom = [x for x in bom if x.source_document_id in allowed_document_ids]
    issues = db.scalars(select(ValidationIssue).where(ValidationIssue.part_number == pn)).all()
    if allowed_document_ids is not None:
        issues = [i for i in issues if not i.document_ids or bool(set(i.document_ids) & allowed_document_ids)]
    revs = db.scalars(select(PartRevision).where(PartRevision.part_number == pn)).all()
    manifest = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "part_number": pn, "revision": revision.upper() if revision else None,
        "documents": [{"id": d.id, "filename": d.filename, "sha256": d.sha256, "doc_type": d.doc_type, "revision": d.revision, "status": d.status.value} for d in docs],
        "bom": [{"child_part_number": x.child_part_number, "quantity": x.quantity, "unit": x.unit} for x in bom],
        "revisions": [{"revision": r.revision, "document_ids": [x for x in (r.document_ids or []) if allowed_document_ids is None or x in allowed_document_ids], "metadata": {}} for r in revs if any((allowed_document_ids is None or x in allowed_document_ids) for x in (r.document_ids or []))],
        "issues": [{"id": i.id, "severity": i.severity.value, "status": i.status.value, "rule_code": i.rule_code, "title": i.title} for i in issues],
        "integrity": {"document_count": len(docs), "all_sha256_present": all(bool(d.sha256) for d in docs)},
    }
    pack = EvidencePack(pack_type=pack_type, part_number=pn, revision=revision.upper() if revision else None, manifest=manifest, created_by=user)
    db.add(pack); db.commit(); db.refresh(pack)
    return pack
