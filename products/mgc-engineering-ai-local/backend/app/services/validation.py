import hashlib
import json
from collections import defaultdict

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import BOMItem, Document, IssueSeverity, ValidationIssue
from app.services.geometry_linking import link_drawing_document


TRUTH_FIELDS = ["material", "thickness_mm", "mass_kg"]


def _fp(rule: str, part: str | None, rev: str | None, details: dict) -> str:
    raw = json.dumps([rule, part, rev, details], sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha256(raw.encode()).hexdigest()


def _upsert(db: Session, part, rev, severity, rule, title, details, doc_ids):
    fingerprint = _fp(rule, part, rev, details)
    issue = db.scalar(select(ValidationIssue).where(ValidationIssue.fingerprint == fingerprint))
    if issue:
        return issue
    issue = ValidationIssue(part_number=part, revision=rev, severity=severity, rule_code=rule, title=title,
                            details=details, document_ids=sorted(set(doc_ids)), fingerprint=fingerprint)
    db.add(issue); db.commit(); db.refresh(issue)
    return issue


def validate_part(db: Session, part_number: str, allowed_document_ids: set[str] | None = None) -> list[ValidationIssue]:
    docs = db.scalars(select(Document).where(Document.part_number == part_number, Document.status == "ready")).all()
    if allowed_document_ids is not None:
        docs = [d for d in docs if d.id in allowed_document_ids]
    created: list[ValidationIssue] = []
    by_rev = defaultdict(list)
    for d in docs:
        by_rev[d.revision or "UNSPECIFIED"].append(d)
    for rev, group in by_rev.items():
        for d in group:
            drawing = (d.extracted_metadata or {}).get("engineering_drawing") or {}
            facts = drawing.get("normalized_facts") or {}
            provenance = drawing.get("provenance") or {}
            if facts.get("thickness_conflict"):
                details = {"document": d.filename, "candidates_mm": facts.get("thickness_candidates_mm") or []}
                created.append(_upsert(db, part_number, None if rev == "UNSPECIFIED" else rev, IssueSeverity.warning,
                    "DRAWING_THICKNESS_AMBIGUOUS", "Drawing contains multiple explicit thickness values", details, [d.id]))
            if drawing.get("entities") and not provenance.get("coordinate_evidence_available"):
                details = {"document": d.filename, "methods": provenance.get("methods") or [], "entity_count": len(drawing.get("entities") or [])}
                created.append(_upsert(db, part_number, None if rev == "UNSPECIFIED" else rev, IssueSeverity.warning,
                    "DRAWING_REVIEW_REQUIRED", "Drawing facts require visual review", details, [d.id]))

            if drawing.get("entities"):
                link_result = link_drawing_document(db, d, allowed_document_ids=allowed_document_ids, persist=True)
                if link_result.get("status") == "cad_required":
                    details = {"document": d.filename, "reason": link_result.get("reason")}
                    created.append(_upsert(db, part_number, None if rev == "UNSPECIFIED" else rev, IssueSeverity.warning,
                        "DRAWING_CAD_PAIR_MISSING", "Drawing cannot be cross-checked against an exact CAD revision", details, [d.id]))
                elif link_result.get("status") == "ready":
                    unmatched = [x for x in link_result.get("links", []) if x.get("status") == "unmatched"]
                    ambiguous = [x for x in link_result.get("links", []) if x.get("status") == "linked_multiple"]
                    cad_id = link_result.get("cad_document_id")
                    doc_ids = [d.id] + ([cad_id] if cad_id else [])
                    if unmatched:
                        details = {
                            "drawing": d.filename, "cad": link_result.get("cad_filename"),
                            "count": len(unmatched),
                            "entities": [{"raw": x.get("raw"), "page": x.get("page")} for x in unmatched[:20]],
                        }
                        created.append(_upsert(db, part_number, None if rev == "UNSPECIFIED" else rev, IssueSeverity.warning,
                            "DRAWING_CAD_DIMENSION_UNMATCHED", "Some drawing dimensions do not match deterministic CAD candidates", details, doc_ids))
                    if ambiguous:
                        details = {
                            "drawing": d.filename, "cad": link_result.get("cad_filename"),
                            "count": len(ambiguous),
                            "entities": [{"raw": x.get("raw"), "candidates": x.get("candidate_count")} for x in ambiguous[:20]],
                        }
                        created.append(_upsert(db, part_number, None if rev == "UNSPECIFIED" else rev, IssueSeverity.info,
                            "DRAWING_CAD_LINK_AMBIGUOUS", "Repeated CAD features require spatial or PMI disambiguation", details, doc_ids))

        for field in TRUTH_FIELDS:
            vals = defaultdict(list)
            for d in group:
                v = (d.extracted_metadata or {}).get(field)
                if v is not None:
                    key = str(v).strip().upper() if isinstance(v, str) else round(float(v), 6)
                    vals[key].append(d)
            if len(vals) > 1:
                details = {"field": field, "values": {str(v): [d.filename for d in ds] for v, ds in vals.items()}}
                created.append(_upsert(db, part_number, None if rev == "UNSPECIFIED" else rev, IssueSeverity.critical,
                    f"CONFLICT_{field.upper()}", f"Conflicting {field} values", details, [d.id for ds in vals.values() for d in ds]))

    bom = db.scalars(select(BOMItem).where(BOMItem.parent_part_number == part_number)).all()
    if allowed_document_ids is not None:
        bom = [x for x in bom if x.source_document_id in allowed_document_ids]
    for item in bom:
        child_query = select(Document.id).where(Document.part_number == item.child_part_number)
        if allowed_document_ids is not None:
            child_query = child_query.where(Document.id.in_(allowed_document_ids))
        child_exists = db.scalar(child_query.limit(1))
        if not child_exists:
            details = {"child_part_number": item.child_part_number, "quantity": item.quantity}
            created.append(_upsert(db, part_number, item.parent_revision, IssueSeverity.warning, "BOM_CHILD_NO_DOCUMENT",
                "BOM component has no indexed documentation", details, [item.source_document_id]))
    return created
