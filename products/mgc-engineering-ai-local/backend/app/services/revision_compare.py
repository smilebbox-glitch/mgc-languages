from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import BOMItem, Document, PartRevision


NUMERIC_KEYS = ["volume_mm3", "surface_area_mm2", "thickness_mm", "mass_kg", "estimated_mass_kg", "solid_count", "face_count", "edge_count"]
TEXT_KEYS = ["material", "doc_type"]
DOCUMENT_SCOPED_KEYS = {"engineering_drawing", "vision_inspection", "object_store"}


def _delta(a, b):
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        pct = None if a == 0 else (b - a) / abs(a) * 100.0
        return {"from": a, "to": b, "delta": b - a, "percent": pct}
    return {"from": a, "to": b}


def _visible_metadata(docs: list[Document]) -> dict:
    out = {}
    conflicts = {}
    for d in docs:
        for key, value in (d.extracted_metadata or {}).items():
            if key.startswith("_") or key in DOCUMENT_SCOPED_KEYS or value in (None, "", [], {}):
                continue
            if key not in out:
                out[key] = value
            elif out[key] != value:
                conflicts.setdefault(key, [out[key]])
                if value not in conflicts[key]:
                    conflicts[key].append(value)
    for key, vals in conflicts.items():
        out[key] = {"conflict": vals}
    return out


def compare_revisions(db: Session, part_number: str, left: str, right: str, allowed_document_ids: set[str] | None = None) -> dict:
    l = db.scalar(select(PartRevision).where(PartRevision.part_number == part_number, PartRevision.revision == left))
    r = db.scalar(select(PartRevision).where(PartRevision.part_number == part_number, PartRevision.revision == right))
    if not l or not r:
        return {"part_number": part_number, "left": left, "right": right, "error": "One or both revisions are missing"}

    docs_l = db.scalars(select(Document).where(Document.part_number == part_number, Document.revision == left)).all()
    docs_r = db.scalars(select(Document).where(Document.part_number == part_number, Document.revision == right)).all()
    if allowed_document_ids is not None:
        docs_l = [d for d in docs_l if d.id in allowed_document_ids]
        docs_r = [d for d in docs_r if d.id in allowed_document_ids]
        if not docs_l or not docs_r:
            return {"part_number": part_number, "left": left, "right": right, "error": "One or both revisions are not visible to the current identity"}
        left_meta, right_meta = _visible_metadata(docs_l), _visible_metadata(docs_r)
    else:
        left_meta, right_meta = (l.metadata_json or {}), (r.metadata_json or {})

    changes = []
    keys = sorted(set(left_meta.keys()) | set(right_meta.keys()))
    for key in keys:
        if key.startswith("_") or key in DOCUMENT_SCOPED_KEYS:
            continue
        a, b = left_meta.get(key), right_meta.get(key)
        if a != b:
            changes.append({"field": key, **_delta(a, b)})

    bom_l = db.scalars(select(BOMItem).where(BOMItem.parent_part_number == part_number, BOMItem.parent_revision == left)).all()
    bom_r = db.scalars(select(BOMItem).where(BOMItem.parent_part_number == part_number, BOMItem.parent_revision == right)).all()
    if allowed_document_ids is not None:
        bom_l = [x for x in bom_l if x.source_document_id in allowed_document_ids]
        bom_r = [x for x in bom_r if x.source_document_id in allowed_document_ids]
    bl = {x.child_part_number: x.quantity for x in bom_l}; br = {x.child_part_number: x.quantity for x in bom_r}
    bom_changes = []
    for pn in sorted(set(bl) | set(br)):
        if bl.get(pn) != br.get(pn):
            bom_changes.append({"part_number": pn, "from_qty": bl.get(pn), "to_qty": br.get(pn)})
    geometry_keys = [
        "volume_mm3", "surface_area_mm2", "solid_count", "face_count", "edge_count",
        "cylindrical_face_count", "planar_face_count", "conical_face_count", "compactness",
        "bbox_min_thickness_candidate_mm",
    ]
    geometry_changes = []
    for key in geometry_keys:
        a, b = left_meta.get(key), right_meta.get(key)
        if a != b and (a is not None or b is not None):
            geometry_changes.append({"field": key, **_delta(a, b)})
    bbox_changes = []
    lb, rb = left_meta.get("bounding_box_mm") or {}, right_meta.get("bounding_box_mm") or {}
    for axis in ("x", "y", "z"):
        a, b = lb.get(axis), rb.get(axis)
        if a != b and (a is not None or b is not None):
            bbox_changes.append({"field": f"bbox_{axis}_mm", **_delta(a, b)})
    surface_changes = []
    ls, rs = left_meta.get("surface_types") or {}, right_meta.get("surface_types") or {}
    for typ in sorted(set(ls) | set(rs)):
        if ls.get(typ, 0) != rs.get(typ, 0):
            surface_changes.append({"surface_type": typ, "from": ls.get(typ, 0), "to": rs.get(typ, 0)})

    return {
        "part_number": part_number, "left": left, "right": right, "metadata_changes": changes,
        "geometry_changes": geometry_changes + bbox_changes, "surface_type_changes": surface_changes,
        "bom_changes": bom_changes,
        "documents": {
            "left": [{"id": d.id, "filename": d.filename, "doc_type": d.doc_type} for d in docs_l],
            "right": [{"id": d.id, "filename": d.filename, "doc_type": d.doc_type} for d in docs_r],
        },
    }
