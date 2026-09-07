from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from app.services.engineering_entities import entity_summary, parse_engineering_entities
from app.services.vector_drawing import analyze_vector_pdf, title_block_value


_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tif", ".tiff"}


def _clean_material(value: str | None) -> str | None:
    if not value:
        return None
    value = re.split(r"[;|\n\r]", value)[0].strip(" :-")
    return value[:80] or None


def _parse_float_from_text(value: str | None) -> float | None:
    if not value:
        return None
    m = re.search(r"\d+(?:[.,]\d+)?", value)
    return float(m.group(0).replace(",", ".")) if m else None


def analyze_drawing(path: Path, extracted_text: str, max_pages: int = 30) -> dict:
    """Build deterministic drawing intelligence from vector content + parsed text.

    For PDFs, coordinate-aware vector text is preferred. For scans/images, the
    document parser's OCR text remains usable but is explicitly marked as OCR/text
    derived and therefore lower-confidence.
    """
    ext = path.suffix.lower()
    result: dict[str, Any] = {
        "engine": "MGC Engineering Drawing Intelligence v1",
        "source_file": path.name,
        "entities": [],
        "entity_counts": {},
        "title_block": {},
        "provenance": {"authoritative": False, "methods": []},
    }

    vector_text = ""
    vector_meta: dict = {}
    if ext == ".pdf":
        try:
            vector_text, vector_meta = analyze_vector_pdf(path, max_pages=max_pages)
            result["vector_pdf"] = vector_meta
            result["title_block"] = vector_meta.get("title_block") or {}
            result["entities"].extend(vector_meta.get("entities") or [])
            result["provenance"]["methods"].append("pymupdf_vector")
        except Exception as exc:
            result["vector_pdf"] = {"error": f"{type(exc).__name__}: {exc}"}

    # Parse the Docling/OCR/plain-text output too, but avoid duplicating the same
    # vector text at lower confidence when the PDF already contains a useful text layer.
    should_parse_text = bool(extracted_text.strip()) and not (
        ext == ".pdf" and (vector_meta.get("content_layer") in {"vector", "text"}) and len(vector_text) >= max(50, int(len(extracted_text) * 0.35))
    )
    if should_parse_text:
        source_method = "docling_or_ocr_text" if ext in {".pdf", *_IMAGE_EXTENSIONS} else "document_text"
        result["entities"].extend(parse_engineering_entities(extracted_text[:250000], source_method=source_method, confidence=0.78))
        result["provenance"]["methods"].append(source_method)

    result["entity_counts"] = entity_summary(result["entities"])
    vector_layer = vector_meta.get("content_layer")
    result["provenance"].update({
        "authoritative": vector_layer in {"vector", "text"},
        "coordinate_evidence_available": any(bool(x.get("bbox")) for x in result["entities"]),
        "vector_text_available": vector_layer in {"vector", "text"},
        "ocr_or_docling_text_used": should_parse_text,
    })

    # Conservative top-level facts from explicit title-block labels only.
    material = _clean_material(title_block_value(vector_meta, "material"))
    revision = title_block_value(vector_meta, "revision")
    part_number = title_block_value(vector_meta, "part_number")
    mass = _parse_float_from_text(title_block_value(vector_meta, "mass"))
    result["normalized_facts"] = {
        "material": material,
        "revision": revision.upper() if isinstance(revision, str) and revision else None,
        "part_number": part_number.upper() if isinstance(part_number, str) and part_number else None,
        "mass_kg_candidate": mass,
    }

    # Thickness can come from explicit THK/t= annotations. Do not pick arbitrary
    # dimensions. If several different thicknesses exist, retain all and mark conflict.
    thicknesses = sorted({float(x["value"]) for x in result["entities"] if x.get("type") == "thickness" and x.get("value") is not None})
    result["normalized_facts"]["thickness_mm"] = thicknesses[0] if len(thicknesses) == 1 else None
    result["normalized_facts"]["thickness_candidates_mm"] = thicknesses
    result["normalized_facts"]["thickness_conflict"] = len(thicknesses) > 1
    return result
