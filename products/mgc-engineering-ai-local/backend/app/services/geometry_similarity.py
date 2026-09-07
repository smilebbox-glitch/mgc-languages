from __future__ import annotations

import math
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Document


def _f(value, default=0.0) -> float:
    try:
        return float(value)
    except Exception:
        return float(default)


def geometry_signature(metadata: dict) -> list[float] | None:
    """Deterministic, mostly scale-normalized geometry fingerprint.

    The first three dimensions remain bbox ratios for backward compatibility.
    Additional fields capture topology and surface-family distribution. No ML is
    required, which keeps candidate generation reproducible and air-gapped.
    """
    meta = metadata or {}
    b = meta.get("bounding_box_mm") or {}
    dims = sorted([_f(b.get("x")), _f(b.get("y")), _f(b.get("z"))])
    if not any(dims):
        return None
    scale = max(dims) or 1.0
    ratios = [x / scale for x in dims]
    vol = _f(meta.get("volume_mm3"))
    area = _f(meta.get("surface_area_mm2"))
    faces = _f(meta.get("face_count") or meta.get("mesh_faces"))
    edges = _f(meta.get("edge_count"))
    cyl = _f(meta.get("cylindrical_face_count"))
    plane = _f(meta.get("planar_face_count"))
    cone = _f(meta.get("conical_face_count"))
    sphere = _f(meta.get("spherical_face_count"))
    torus = _f(meta.get("toroidal_face_count"))
    compactness = _f(meta.get("compactness"))
    cyl_radii = [_f(x) / scale for x in (meta.get("cylindrical_radii_mm") or [])[:16]]
    if cyl_radii:
        r_mean = sum(cyl_radii) / len(cyl_radii)
        r_max = max(cyl_radii)
        r_min = min(cyl_radii)
    else:
        r_mean = r_max = r_min = 0.0
    denom_faces = max(faces, 1.0)
    # normalized physical descriptors + topology. Include log scale separately so
    # identical shape at a radically different size is similar but not identical.
    return [
        *ratios,
        vol / (scale ** 3) if vol else 0.0,
        area / (scale ** 2) if area else 0.0,
        math.log1p(scale),
        math.log1p(faces),
        math.log1p(edges),
        cyl / denom_faces,
        plane / denom_faces,
        cone / denom_faces,
        sphere / denom_faces,
        torus / denom_faces,
        compactness,
        r_mean,
        r_min,
        r_max,
    ]


def _distance(a: list[float], b: list[float]) -> float:
    diffs = []
    for i, (x, y) in enumerate(zip(a, b)):
        # Scale uses a slightly lower weight so shape remains the dominant signal.
        denom = max(abs(x), abs(y), 0.05)
        weight = 0.35 if i == 5 else 1.0
        diffs.append(weight * ((x - y) / denom) ** 2)
    return math.sqrt(sum(diffs) / max(sum(0.35 if i == 5 else 1.0 for i in range(len(diffs))), 1.0))


def _factor_similarity(a: float, b: float, floor: float = 0.05) -> float:
    denom = max(abs(a), abs(b), floor)
    return max(0.0, 1.0 - abs(a - b) / denom)


def explain_similarity(a: list[float], b: list[float]) -> dict:
    return {
        "bbox_shape": round(sum(_factor_similarity(a[i], b[i]) for i in range(3)) / 3, 4),
        "normalized_volume": round(_factor_similarity(a[3], b[3]), 4),
        "normalized_area": round(_factor_similarity(a[4], b[4]), 4),
        "absolute_scale": round(_factor_similarity(a[5], b[5]), 4),
        "topology": round(sum(_factor_similarity(a[i], b[i]) for i in range(6, 13)) / 7, 4),
        "cylindrical_features": round(sum(_factor_similarity(a[i], b[i]) for i in range(14, 17)) / 3, 4),
    }


def similar_cad(db: Session, document_id: str, limit: int = 10) -> list[dict]:
    source = db.get(Document, document_id)
    if not source or source.doc_type != "cad":
        return []
    sig = geometry_signature(source.extracted_metadata or {})
    if sig is None:
        return []
    rows = db.scalars(select(Document).where(Document.doc_type == "cad", Document.id != document_id)).all()
    out = []
    for doc in rows:
        other = geometry_signature(doc.extracted_metadata or {})
        if other is None:
            continue
        d = _distance(sig, other)
        similarity = max(0.0, 1.0 - d)
        out.append({
            "document_id": doc.id, "filename": doc.filename, "part_number": doc.part_number,
            "revision": doc.revision, "similarity": similarity,
            "match_factors": explain_similarity(sig, other),
            "bounding_box_mm": (doc.extracted_metadata or {}).get("bounding_box_mm"),
            "volume_mm3": (doc.extracted_metadata or {}).get("volume_mm3"),
            "surface_types": (doc.extracted_metadata or {}).get("surface_types"),
        })
    out.sort(key=lambda x: x["similarity"], reverse=True)
    return out[:limit]
