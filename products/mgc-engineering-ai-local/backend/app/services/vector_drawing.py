from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from app.services.engineering_entities import entity_summary, parse_engineering_entities


TITLE_KEYS: dict[str, tuple[str, ...]] = {
    "part_number": ("part number", "part no", "part no.", "p/n", "drawing no", "dwg no", "номер детали", "обозначение", "图号", "零件号"),
    "revision": ("revision", "rev", "rev.", "ревизия", "изм.", "版本", "版次"),
    "material": ("material", "материал", "材料"),
    "scale": ("scale", "масштаб", "比例"),
    "mass": ("mass", "weight", "масса", "重量"),
    "title": ("title", "description", "наименование", "名称"),
}


def _rect_union(boxes: list[tuple[float, float, float, float]]) -> list[float]:
    return [
        round(min(b[0] for b in boxes), 3), round(min(b[1] for b in boxes), 3),
        round(max(b[2] for b in boxes), 3), round(max(b[3] for b in boxes), 3),
    ]


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


def _title_value(line: str, aliases: tuple[str, ...]) -> str | None:
    low = line.lower()
    for alias in aliases:
        idx = low.find(alias)
        if idx < 0:
            continue
        raw = line[idx + len(alias):].lstrip(" :;=-\t")
        if raw:
            return _norm(raw)[:120]
    return None


def _extract_title_block(lines: list[dict], page_height: float, page_width: float) -> dict:
    # Engineering title blocks are commonly at the bottom or right side. We do not
    # assume a specific OEM template: the region only increases confidence.
    candidates = [
        x for x in lines
        if x["bbox"][1] >= page_height * 0.60 or x["bbox"][0] >= page_width * 0.55
    ]
    result: dict[str, dict] = {}
    for line in candidates:
        for field, aliases in TITLE_KEYS.items():
            value = _title_value(line["text"], aliases)
            if value and field not in result:
                result[field] = {
                    "value": value,
                    "page": line["page"],
                    "bbox": line["bbox"],
                    "source_method": "vector_text",
                    "confidence": 0.96,
                }
    return result


def analyze_vector_pdf(path: Path, max_pages: int = 30) -> tuple[str, dict]:
    """Extract coordinate-aware text and vector structure from a PDF.

    No raster OCR is performed here. The result can therefore be used as an
    authoritative transcription layer for vector-exported CAD drawings.
    """
    import fitz

    doc = fitz.open(str(path))
    all_lines: list[dict] = []
    all_entities: list[dict] = []
    page_stats: list[dict] = []
    title_block: dict[str, dict] = {}
    total_words = 0
    total_paths = 0
    total_vector_items = 0

    try:
        for pidx in range(min(len(doc), max(1, max_pages))):
            page = doc[pidx]
            words = page.get_text("words", sort=True)
            grouped: dict[tuple[int, int], list[tuple]] = {}
            for word in words:
                # x0,y0,x1,y1,text,block,line,word
                grouped.setdefault((int(word[5]), int(word[6])), []).append(word)
            lines: list[dict] = []
            for _, items in sorted(grouped.items(), key=lambda kv: (min(w[1] for w in kv[1]), min(w[0] for w in kv[1]))):
                items = sorted(items, key=lambda w: (w[0], w[7]))
                text = _norm(" ".join(str(w[4]) for w in items))
                if not text:
                    continue
                bbox = _rect_union([(float(w[0]), float(w[1]), float(w[2]), float(w[3])) for w in items])
                line = {"page": pidx + 1, "text": text, "bbox": bbox}
                lines.append(line)
                all_lines.append(line)
                all_entities.extend(parse_engineering_entities(text, page=pidx + 1, bbox=bbox, source_method="vector_text", confidence=0.97))

            try:
                drawings = page.get_drawings()
            except Exception:
                drawings = []
            path_count = len(drawings)
            vector_items = sum(len(x.get("items") or []) for x in drawings)
            total_words += len(words)
            total_paths += path_count
            total_vector_items += vector_items

            local_title = _extract_title_block(lines, float(page.rect.height), float(page.rect.width))
            for k, v in local_title.items():
                title_block.setdefault(k, v)

            page_stats.append({
                "page": pidx + 1,
                "width_pt": round(float(page.rect.width), 3),
                "height_pt": round(float(page.rect.height), 3),
                "word_count": len(words),
                "line_count": len(lines),
                "vector_path_count": path_count,
                "vector_item_count": vector_items,
            })
    finally:
        doc.close()

    vector_text = "\n".join(x["text"] for x in all_lines)
    # Classify the source without pretending that every vector PDF is a CAD drawing.
    if total_words >= 10 and total_vector_items >= 10:
        layer = "vector"
    elif total_words >= 10:
        layer = "text"
    elif total_vector_items >= 10:
        layer = "vector_graphics_only"
    else:
        layer = "raster_or_sparse"

    engineering_signal = min(
        1.0,
        0.15 * len(title_block)
        + 0.04 * min(len(all_entities), 10)
        + (0.25 if total_vector_items >= 30 else 0.0),
    )
    meta = {
        "parser": "pymupdf_vector",
        "content_layer": layer,
        "page_count_analyzed": len(page_stats),
        "word_count": total_words,
        "vector_path_count": total_paths,
        "vector_item_count": total_vector_items,
        "engineering_signal_score": round(engineering_signal, 3),
        "page_stats": page_stats,
        "title_block": title_block,
        "entities": all_entities[:3000],
        "entity_counts": entity_summary(all_entities),
        "provenance": {
            "authoritative_for_text_positions": layer in {"vector", "text"},
            "ocr_used": False,
            "coordinate_system": "PDF points; origin top-left in extracted bbox representation",
        },
    }
    return vector_text, meta


def title_block_value(meta: dict, field: str) -> Any:
    item = (meta or {}).get("title_block", {}).get(field)
    return item.get("value") if isinstance(item, dict) else None
