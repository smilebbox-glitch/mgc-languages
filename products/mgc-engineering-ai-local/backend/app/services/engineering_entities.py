from __future__ import annotations

import re
from typing import Any


_NUM = r"\d+(?:[.,]\d+)?"
_UNIT = r"(?:mm|мм|毫米|cm|см|in|inch|\")"

# Toleranced dimensions. The parser intentionally requires an engineering marker
# (diameter/radius or tolerance) to avoid converting arbitrary document numbers
# into dimensions.
_TOLERANCED = re.compile(
    rf"(?P<prefix>[Ø⌀Rr]?)\s*(?P<nom>{_NUM})\s*"
    rf"(?:(?:±|\+/-)\s*(?P<sym>{_NUM})|\+\s*(?P<up>{_NUM})\s*(?:/|\\)?\s*-\s*(?P<lo>{_NUM}))"
    rf"\s*(?P<unit>{_UNIT})?",
    re.IGNORECASE,
)
_DIAMETER = re.compile(rf"(?P<prefix>[Ø⌀])\s*(?P<nom>{_NUM})\s*(?P<unit>{_UNIT})?", re.IGNORECASE)
_RADIUS = re.compile(rf"\bR\s*(?P<nom>{_NUM})\s*(?P<unit>{_UNIT})?", re.IGNORECASE)
_THREAD = re.compile(
    rf"\b(?P<thread>M\s*{_NUM}(?:\s*[x×]\s*{_NUM})?(?:\s*[-x×]\s*{_NUM})?(?:\s*(?:6H|6G|4H|5H|7H|LH|RH))?)\b",
    re.IGNORECASE,
)
_ROUGHNESS = re.compile(rf"\bRa\s*(?P<value>{_NUM})\s*(?:µm|um|μm)?", re.IGNORECASE)
_THICKNESS = re.compile(
    rf"(?:\bTHK\b|\bTHICKNESS\b|\bТОЛЩИНА\b|厚度|(?<![A-Za-z])t\s*=)\s*[:=]?\s*(?P<value>{_NUM})\s*(?P<unit>{_UNIT})?",
    re.IGNORECASE,
)
_DATUM = re.compile(r"\b(?:DATUM|БАЗА)\s*[:=]?\s*(?P<datum>[A-Z])\b", re.IGNORECASE)
_STANDARD = re.compile(r"\b(?:ISO|DIN|EN|ГОСТ|GOST|GB/T|GB|JIS|SAE)\s*[A-Z0-9][A-Z0-9.\-/ :]{1,28}", re.IGNORECASE)

# Common Unicode GD&T symbols encountered after vector-PDF extraction.
_GDT_SYMBOLS = {
    "⌖": "position",
    "⏥": "flatness",
    "⌭": "cylindricity",
    "○": "circularity",
    "∥": "parallelism",
    "⟂": "perpendicularity",
    "⌯": "symmetry",
    "◎": "concentricity",
    "↗": "circular_runout",
}


def _float(value: str | None) -> float | None:
    if value is None:
        return None
    return float(value.replace(",", "."))


def _bbox(value: Any) -> list[float] | None:
    if value is None:
        return None
    try:
        vals = [round(float(x), 3) for x in value]
    except Exception:
        return None
    return vals if len(vals) == 4 else None


def _base(kind: str, raw: str, *, page: int | None, bbox: Any, source_method: str, confidence: float) -> dict:
    item = {
        "type": kind,
        "raw": raw.strip(),
        "source_method": source_method,
        "confidence": round(float(confidence), 3),
    }
    if page is not None:
        item["page"] = int(page)
    box = _bbox(bbox)
    if box:
        item["bbox"] = box
    return item


def parse_engineering_entities(
    text: str,
    *,
    page: int | None = None,
    bbox: Any = None,
    source_method: str = "text",
    confidence: float = 0.86,
) -> list[dict]:
    """Extract conservative engineering entities from a text fragment.

    This is deterministic parsing. It intentionally favors precision over recall;
    ambiguous bare numbers are ignored.
    """
    if not text:
        return []

    out: list[dict] = []
    occupied: list[tuple[int, int]] = []

    for m in _TOLERANCED.finditer(text):
        prefix = (m.group("prefix") or "").upper()
        nominal = _float(m.group("nom"))
        sym = _float(m.group("sym"))
        upper = sym if sym is not None else _float(m.group("up"))
        lower = -sym if sym is not None else (-_float(m.group("lo")) if m.group("lo") else None)
        kind = "diameter" if prefix in {"Ø", "⌀"} else "radius" if prefix == "R" else "dimension"
        item = _base(kind, m.group(0), page=page, bbox=bbox, source_method=source_method, confidence=confidence)
        item.update({"nominal": nominal, "upper_tolerance": upper, "lower_tolerance": lower, "unit": (m.group("unit") or "mm").lower()})
        out.append(item)
        occupied.append(m.span())

    def free(span: tuple[int, int]) -> bool:
        return not any(max(span[0], x0) < min(span[1], x1) for x0, x1 in occupied)

    for pattern, kind in ((_DIAMETER, "diameter"), (_RADIUS, "radius")):
        for m in pattern.finditer(text):
            if not free(m.span()):
                continue
            item = _base(kind, m.group(0), page=page, bbox=bbox, source_method=source_method, confidence=confidence)
            item.update({"nominal": _float(m.group("nom")), "unit": (m.group("unit") or "mm").lower()})
            out.append(item)
            occupied.append(m.span())

    for m in _THREAD.finditer(text):
        if free(m.span()):
            item = _base("thread", m.group(0), page=page, bbox=bbox, source_method=source_method, confidence=confidence)
            item["designation"] = re.sub(r"\s+", "", m.group("thread")).replace("×", "x").upper()
            out.append(item)

    for m in _ROUGHNESS.finditer(text):
        item = _base("surface_finish", m.group(0), page=page, bbox=bbox, source_method=source_method, confidence=confidence)
        item.update({"parameter": "Ra", "value_um": _float(m.group("value"))})
        out.append(item)

    for m in _THICKNESS.finditer(text):
        item = _base("thickness", m.group(0), page=page, bbox=bbox, source_method=source_method, confidence=confidence)
        item.update({"value": _float(m.group("value")), "unit": (m.group("unit") or "mm").lower()})
        out.append(item)

    for m in _DATUM.finditer(text):
        item = _base("datum", m.group(0), page=page, bbox=bbox, source_method=source_method, confidence=confidence)
        item["datum"] = m.group("datum").upper()
        out.append(item)

    for symbol, name in _GDT_SYMBOLS.items():
        if symbol in text:
            item = _base("gdt_symbol", text, page=page, bbox=bbox, source_method=source_method, confidence=max(0.5, confidence - 0.08))
            item.update({"symbol": symbol, "gdt_type": name})
            out.append(item)

    for m in _STANDARD.finditer(text):
        item = _base("standard", m.group(0), page=page, bbox=bbox, source_method=source_method, confidence=confidence)
        item["designation"] = re.sub(r"\s+", " ", m.group(0)).strip()
        out.append(item)

    # Stable de-duplication within a line / OCR fragment.
    unique: dict[tuple, dict] = {}
    for item in out:
        key = (
            item.get("type"), item.get("raw"), item.get("page"),
            tuple(item.get("bbox") or []), item.get("nominal"), item.get("designation"),
        )
        unique[key] = item
    return list(unique.values())


def entity_summary(entities: list[dict]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in entities:
        typ = str(item.get("type") or "unknown")
        counts[typ] = counts.get(typ, 0) + 1
    return dict(sorted(counts.items()))
