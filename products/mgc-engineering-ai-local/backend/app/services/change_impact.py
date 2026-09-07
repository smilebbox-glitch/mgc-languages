from collections import deque
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import BOMItem, Document, Relationship, ValidationIssue
from app.services.revision_compare import compare_revisions


def analyze_change_impact(db: Session, part_number: str, from_revision: str, to_revision: str, max_depth: int = 4, allowed_document_ids: set[str] | None = None) -> dict:
    part_number = part_number.upper()
    revision_delta = compare_revisions(db, part_number, from_revision.upper(), to_revision.upper(), allowed_document_ids)
    impacted_parts: dict[str, dict] = {part_number: {"distance": 0, "reason": "changed_part"}}
    q = deque([(part_number, 0)])
    while q:
        pn, depth = q.popleft()
        if depth >= max_depth:
            continue
        parents = db.scalars(select(BOMItem).where(BOMItem.child_part_number == pn)).all()
        if allowed_document_ids is not None:
            parents = [x for x in parents if x.source_document_id in allowed_document_ids]
        for item in parents:
            parent = item.parent_part_number
            if parent not in impacted_parts:
                impacted_parts[parent] = {"distance": depth + 1, "reason": "parent_assembly", "quantity": item.quantity}
                q.append((parent, depth + 1))
    rels = db.scalars(select(Relationship).where((Relationship.subject_id == part_number) | (Relationship.object_id == part_number))).all()
    if allowed_document_ids is not None:
        rels = [r for r in rels if r.evidence_document_id is None or r.evidence_document_id in allowed_document_ids]
    related_entities = [{"subject": r.subject_id, "predicate": r.predicate, "object": r.object_id, "confidence": r.confidence} for r in rels]
    docs = db.scalars(select(Document).where(Document.part_number.in_(list(impacted_parts.keys())))).all()
    if allowed_document_ids is not None:
        docs = [d for d in docs if d.id in allowed_document_ids]
    issues = db.scalars(select(ValidationIssue).where(ValidationIssue.part_number.in_(list(impacted_parts.keys())))).all()
    if allowed_document_ids is not None:
        issues = [i for i in issues if not i.document_ids or bool(set(i.document_ids) & allowed_document_ids)]
    risk = 10 + min(45, len(revision_delta.get("metadata_changes", [])) * 6) + min(25, len(impacted_parts) * 4) + min(20, len(issues) * 3)
    return {
        "part_number": part_number, "from_revision": from_revision, "to_revision": to_revision,
        "risk_score": min(100, risk), "revision_delta": revision_delta,
        "impacted_parts": [{"part_number": k, **v} for k, v in sorted(impacted_parts.items(), key=lambda x: x[1]["distance"])],
        "impacted_documents": [{"id": d.id, "filename": d.filename, "part_number": d.part_number, "revision": d.revision, "doc_type": d.doc_type} for d in docs],
        "open_issues": [{"id": i.id, "part_number": i.part_number, "severity": i.severity.value, "title": i.title} for i in issues if getattr(i.status, "value", i.status) != "resolved"],
        "related_entities": related_entities,
    }
