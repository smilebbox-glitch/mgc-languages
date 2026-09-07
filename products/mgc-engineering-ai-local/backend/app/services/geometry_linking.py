from __future__ import annotations

import math
import re
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Document


LINKABLE_TYPES = {"diameter", "radius", "dimension", "thickness", "thread"}


def _num(value: Any) -> float | None:
    try:
        value = float(value)
        return value if math.isfinite(value) else None
    except Exception:
        return None


def _tolerance(entity: dict, nominal: float) -> float:
    explicit = max(abs(_num(entity.get("upper_tolerance")) or 0.0), abs(_num(entity.get("lower_tolerance")) or 0.0))
    # CAD geometry should normally agree much more closely than drawing tolerance.
    # The cap prevents a wide manufacturing tolerance from linking unrelated geometry.
    return max(0.02, min(0.25, explicit * 0.25 if explicit else 0.0, ) if explicit else max(0.02, abs(nominal) * 0.001))


def _candidate_score(nominal: float, actual: float, threshold: float, semantic_weight: float) -> float:
    delta = abs(actual - nominal)
    if delta > threshold:
        return 0.0
    numeric = max(0.0, 1.0 - delta / max(threshold, 1e-9))
    return round(min(0.995, 0.65 * numeric + 0.35 * semantic_weight), 3)


def _bbox_features(meta: dict) -> list[dict]:
    box = meta.get("bounding_box_mm") or {}
    out: list[dict] = []
    for axis in ("x", "y", "z"):
        value = _num(box.get(axis))
        if value is not None:
            out.append({
                "feature_id": f"bbox:{axis}",
                "kind": "bounding_box_dimension",
                "axis": axis,
                "value_mm": value,
            })
    thin = _num(meta.get("bbox_min_thickness_candidate_mm"))
    if meta.get("thin_part_candidate") and thin is not None:
        out.append({
            "feature_id": "shape:thin-thickness",
            "kind": "thin_part_thickness_candidate",
            "value_mm": thin,
        })
    return out


def _to_mm(value: float | None, unit: Any) -> float | None:
    if value is None:
        return None
    u = str(unit or "mm").strip().lower()
    if u in {"mm", "мм", "毫米"}:
        return value
    if u in {"cm", "см"}:
        return value * 10.0
    if u in {"in", "inch", '"'}:
        return value * 25.4
    return None


def _thread_nominal(entity: dict) -> float | None:
    designation = str(entity.get("designation") or entity.get("raw") or "")
    m = re.search(r"\bM\s*(\d+(?:[.,]\d+)?)", designation, re.IGNORECASE)
    return float(m.group(1).replace(",", ".")) if m else None


def _geometry_candidates(cad_meta: dict, entity: dict) -> list[dict]:
    kind = entity.get("type")
    nominal = _to_mm(_num(entity.get("nominal")), entity.get("unit"))
    if kind == "thickness":
        nominal = _to_mm(_num(entity.get("value")), entity.get("unit"))
    elif kind == "thread":
        nominal = _thread_nominal(entity)
    if nominal is None or nominal <= 0:
        return []

    threshold = _tolerance(entity, nominal)
    faces = list(cad_meta.get("geometry_features") or [])
    bbox_features = _bbox_features(cad_meta)
    matches: list[dict] = []

    def add(feature: dict, actual: float | None, semantic_weight: float, relation: str):
        if actual is None:
            return
        score = _candidate_score(nominal, actual, threshold, semantic_weight)
        if score <= 0:
            return
        matches.append({
            "feature_id": feature.get("feature_id"),
            "feature_kind": feature.get("kind"),
            "relation": relation,
            "drawing_value_mm": round(nominal, 6),
            "cad_value_mm": round(actual, 6),
            "delta_mm": round(actual - nominal, 6),
            "score": score,
            "center_mm": feature.get("center_mm"),
            "axis_direction": feature.get("axis_direction"),
            "bounding_box_mm": feature.get("bounding_box_mm"),
        })

    if kind == "diameter":
        for f in faces:
            if f.get("kind") == "cylindrical_face":
                add(f, _num(f.get("diameter_mm")), 1.0, "diameter_matches_cylindrical_face")
    elif kind == "radius":
        for f in faces:
            if f.get("kind") == "cylindrical_face":
                add(f, _num(f.get("radius_mm")), 0.95, "radius_matches_cylindrical_face")
    elif kind == "thickness":
        for f in bbox_features:
            if f.get("kind") == "thin_part_thickness_candidate":
                add(f, _num(f.get("value_mm")), 0.92, "thickness_matches_thin_part_extent")
    elif kind == "thread":
        # STEP without semantic PMI usually does not preserve thread designation.
        # Match only the nominal cylindrical diameter and keep confidence reduced.
        for f in faces:
            if f.get("kind") == "cylindrical_face":
                add(f, _num(f.get("diameter_mm")), 0.70, "thread_nominal_matches_cylindrical_face")
    elif kind == "dimension":
        for f in bbox_features:
            if f.get("kind") == "bounding_box_dimension":
                add(f, _num(f.get("value_mm")), 0.88, "dimension_matches_part_extent")

    matches.sort(key=lambda x: (-x["score"], abs(x["delta_mm"]), str(x.get("feature_id"))))
    return matches[:12]


def link_entities_to_geometry(drawing: dict, cad_meta: dict) -> dict:
    """Link coordinate-backed drawing entities to deterministic B-Rep candidates.

    This v1 linker deliberately does not claim spatial identity when several equal
    CAD features exist. Numeric+semantic agreement can produce a candidate group;
    a unique result is marked verified only when one B-Rep candidate remains.
    """
    links: list[dict] = []
    entities = list(drawing.get("entities") or [])
    for idx, entity in enumerate(entities):
        typ = str(entity.get("type") or "")
        if typ not in LINKABLE_TYPES:
            continue
        candidates = _geometry_candidates(cad_meta, entity)
        if not candidates:
            status = "unmatched"
            confidence = 0.0
        elif len(candidates) == 1:
            status = "linked_unique"
            confidence = candidates[0]["score"]
        else:
            status = "linked_multiple"
            confidence = min(0.79, candidates[0]["score"])
        links.append({
            "link_id": f"drawing-entity:{idx:04d}",
            "entity_index": idx,
            "entity_type": typ,
            "raw": entity.get("raw"),
            "page": entity.get("page"),
            "bbox": entity.get("bbox"),
            "source_method": entity.get("source_method"),
            "status": status,
            "confidence": round(float(confidence), 3),
            "verified": status == "linked_unique" and bool(entity.get("bbox")),
            "candidate_count": len(candidates),
            "candidates": candidates,
        })

    total = len(links)
    unique = sum(x["status"] == "linked_unique" for x in links)
    multiple = sum(x["status"] == "linked_multiple" for x in links)
    unmatched = sum(x["status"] == "unmatched" for x in links)
    coordinate_backed = sum(bool(x.get("bbox")) for x in links)
    return {
        "engine": "MGC Drawing-CAD Linker v1",
        "strategy": "deterministic_numeric_semantic_brep",
        "linkable_entities": total,
        "linked_unique": unique,
        "linked_multiple": multiple,
        "unmatched": unmatched,
        "coordinate_backed": coordinate_backed,
        "coverage": round((unique + multiple) / total, 4) if total else 0.0,
        "verified_coverage": round(unique / total, 4) if total else 0.0,
        "links": links,
        "limitations": [
            "Equal-size repeated features remain an ambiguous candidate group unless semantic PMI or spatial view mapping disambiguates them.",
            "Mesh/STL geometry is not accepted as dimensional authority for face-level linking.",
        ],
    }


def _select_cad_document(db: Session, drawing_doc: Document, cad_document_id: str | None, allowed_document_ids: set[str] | None) -> tuple[Document | None, str]:
    if cad_document_id:
        cad = db.get(Document, cad_document_id)
        if not cad or cad.doc_type != "cad" or (allowed_document_ids is not None and cad.id not in allowed_document_ids):
            return None, "requested_cad_not_available"
        return cad, "explicit"

    if not drawing_doc.part_number:
        return None, "drawing_has_no_part_number"
    q = select(Document).where(
        Document.part_number == drawing_doc.part_number,
        Document.doc_type == "cad",
        Document.status == "ready",
    )
    rows = list(db.scalars(q).all())
    if allowed_document_ids is not None:
        rows = [d for d in rows if d.id in allowed_document_ids]
    exact = [d for d in rows if drawing_doc.revision and d.revision == drawing_doc.revision]
    if len(exact) == 1:
        return exact[0], "exact_part_revision"
    if len(exact) > 1:
        brep = [d for d in exact if (d.extracted_metadata or {}).get("geometry_authority") == "deterministic_brep"]
        if len(brep) == 1:
            return brep[0], "exact_part_revision_brep"
        return None, "multiple_cad_models_for_revision"
    if not drawing_doc.revision and len(rows) == 1:
        return rows[0], "single_part_cad_without_revision"
    return None, "no_exact_cad_revision"


def link_drawing_document(
    db: Session,
    drawing_doc: Document,
    *,
    cad_document_id: str | None = None,
    allowed_document_ids: set[str] | None = None,
    persist: bool = True,
) -> dict:
    drawing = (drawing_doc.extracted_metadata or {}).get("engineering_drawing") or {}
    if not drawing.get("entities"):
        return {"status": "not_ready", "reason": "drawing_has_no_engineering_entities", "links": []}

    cad, source_match = _select_cad_document(db, drawing_doc, cad_document_id, allowed_document_ids)
    if not cad:
        return {
            "status": "cad_required",
            "reason": source_match,
            "drawing_document_id": drawing_doc.id,
            "part_number": drawing_doc.part_number,
            "revision": drawing_doc.revision,
            "links": [],
        }
    cad_meta = cad.extracted_metadata or {}
    if cad_meta.get("geometry_authority") != "deterministic_brep":
        return {
            "status": "unsupported_cad_authority",
            "reason": str(cad_meta.get("geometry_authority") or "unknown"),
            "drawing_document_id": drawing_doc.id,
            "cad_document_id": cad.id,
            "links": [],
        }

    result = link_entities_to_geometry(drawing, cad_meta)
    result.update({
        "status": "ready",
        "source_match": source_match,
        "drawing_document_id": drawing_doc.id,
        "drawing_filename": drawing_doc.filename,
        "cad_document_id": cad.id,
        "cad_filename": cad.filename,
        "part_number": drawing_doc.part_number or cad.part_number,
        "revision": drawing_doc.revision or cad.revision,
        "cad_geometry_authority": cad_meta.get("geometry_authority"),
    })
    if persist:
        drawing_doc.extracted_metadata = {**(drawing_doc.extracted_metadata or {}), "geometry_links": result}
        db.commit()
    return result
