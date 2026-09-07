import re

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.db.models import BOMItem, Document, Part, PartRevision, Relationship


def _revision_key(value: str | None):
    if not value:
        return ()
    return tuple(int(x) if x.isdigit() else x for x in re.findall(r"\d+|[A-Z]+", value.upper()))


DOCUMENT_SCOPED_KEYS = {"engineering_drawing", "vision_inspection", "object_store"}


def _merge_truth(old: dict, new: dict) -> dict:
    out = dict(old or {})
    provenance = dict(out.get("_provenance") or {})
    for key, value in (new or {}).items():
        if key.startswith("_") or key in DOCUMENT_SCOPED_KEYS or value in (None, "", [], {}):
            continue
        if key not in out:
            out[key] = value
    if provenance:
        out["_provenance"] = provenance
    return out


def register_document(db: Session, doc: Document, *, commit: bool = True) -> None:
    if not doc.part_number:
        return
    part = db.scalar(select(Part).where(Part.part_number == doc.part_number))
    if not part:
        part = Part(part_number=doc.part_number, project_code=doc.project_code, latest_revision=doc.revision, metadata_json={})
        db.add(part)
    if doc.revision and (not part.latest_revision or _revision_key(doc.revision) > _revision_key(part.latest_revision)):
        part.latest_revision = doc.revision
    part.metadata_json = _merge_truth(part.metadata_json, doc.extracted_metadata)
    areas = set((part.metadata_json or {}).get("manufacturing_areas") or [])
    if getattr(doc, "manufacturing_area", None):
        areas.add(doc.manufacturing_area)
    if areas:
        part.metadata_json = {**(part.metadata_json or {}), "manufacturing_areas": sorted(areas)}

    if doc.revision:
        rev = db.scalar(select(PartRevision).where(PartRevision.part_number == doc.part_number, PartRevision.revision == doc.revision))
        if not rev:
            rev = PartRevision(part_number=doc.part_number, revision=doc.revision, metadata_json={}, document_ids=[])
            db.add(rev)
        ids = set(rev.document_ids or [])
        ids.add(doc.id)
        rev.document_ids = sorted(ids)
        rev.metadata_json = _merge_truth(rev.metadata_json, doc.extracted_metadata)

    exists = db.scalar(select(Relationship).where(
        Relationship.subject_type == "part", Relationship.subject_id == doc.part_number,
        Relationship.predicate == "HAS_DOCUMENT", Relationship.object_type == "document", Relationship.object_id == doc.id
    ))
    if not exists:
        db.add(Relationship(
            subject_type="part", subject_id=doc.part_number, predicate="HAS_DOCUMENT", object_type="document", object_id=doc.id,
            evidence_document_id=doc.id, confidence=1.0, metadata_json={"doc_type": doc.doc_type, "revision": doc.revision}
        ))
    if commit:
        db.commit()


def part_graph(db: Session, part_number: str, allowed_document_ids: set[str] | None = None) -> dict:
    docs = db.scalars(select(Document).where(Document.part_number == part_number)).all()
    if allowed_document_ids is not None:
        docs = [d for d in docs if d.id in allowed_document_ids]
    rels = db.scalars(select(Relationship).where((Relationship.subject_id == part_number) | (Relationship.object_id == part_number))).all()
    if allowed_document_ids is not None:
        rels = [r for r in rels if r.evidence_document_id is None or r.evidence_document_id in allowed_document_ids]
    bom_out = db.scalars(select(BOMItem).where(BOMItem.parent_part_number == part_number)).all()
    bom_in = db.scalars(select(BOMItem).where(BOMItem.child_part_number == part_number)).all()
    nodes = [{"id": f"part:{part_number}", "type": "part", "label": part_number}]
    edges = []
    for d in docs:
        nodes.append({"id": f"doc:{d.id}", "type": d.doc_type or "document", "label": d.filename, "revision": d.revision})
        edges.append({"source": f"part:{part_number}", "target": f"doc:{d.id}", "predicate": "HAS_DOCUMENT"})
    for item in bom_out:
        nodes.append({"id": f"part:{item.child_part_number}", "type": "part", "label": item.child_part_number})
        edges.append({"source": f"part:{part_number}", "target": f"part:{item.child_part_number}", "predicate": "CONTAINS", "quantity": item.quantity})
    for item in bom_in:
        nodes.append({"id": f"part:{item.parent_part_number}", "type": "part", "label": item.parent_part_number})
        edges.append({"source": f"part:{item.parent_part_number}", "target": f"part:{part_number}", "predicate": "CONTAINS", "quantity": item.quantity})
    unique = {n["id"]: n for n in nodes}
    return {"nodes": list(unique.values()), "edges": edges, "relationships": [
        {"subject": r.subject_id, "predicate": r.predicate, "object": r.object_id, "confidence": r.confidence} for r in rels
    ]}
