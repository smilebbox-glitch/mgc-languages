import re
from pathlib import Path


PART_PATTERNS = [
    re.compile(r"(?i)(?:part\s*(?:number|no\.?|#)|p/n|номер\s+детали|деталь\s*№|零件号|图号)\s*[:=\-]?\s*([A-Z0-9][A-Z0-9_.\-/]{4,})"),
    re.compile(r"(?<![A-Z0-9])([0-9]{7,14})(?![A-Z0-9])"),
]
REV_PATTERNS = [
    re.compile(r"(?i)(?:rev(?:ision)?|revision|рев(?:изия)?|版本|版次)\s*[:=\-]?\s*([A-Z0-9]{1,6})"),
    re.compile(r"(?i)[_\-]REV[_\-]?([A-Z0-9]{1,6})(?:[_\-.]|$)"),
]
MATERIAL_PATTERNS = [
    re.compile(r"(?i)(?:material|материал|材料)\s*[:=\-]\s*([A-Z0-9+_.\-/ ]{2,40})"),
]
THICKNESS_PATTERNS = [
    re.compile(r"(?i)(?:thickness|толщина|厚度)\s*[:=\-]?\s*([0-9]+(?:[.,][0-9]+)?)\s*(?:mm|мм|毫米)?"),
]
MASS_PATTERNS = [
    re.compile(r"(?i)(?:mass|weight|масса|вес|重量)\s*[:=\-]?\s*([0-9]+(?:[.,][0-9]+)?)\s*(kg|кг|g|г)?"),
]


def _first(patterns, text: str):
    for p in patterns:
        m = p.search(text)
        if m:
            return m.group(1).strip(" ._-\n\t")
    return None


def classify_doc_type(filename: str, text: str, ext: str) -> str:
    low = (filename + "\n" + text[:5000]).lower()
    if ext in {".step", ".stp", ".iges", ".igs", ".stl", ".dxf"}:
        return "cad"
    if "bom" in low or "bill of material" in low or "спецификац" in low or "ведомость покупных" in low:
        return "bom"
    if "test report" in low or "испытан" in low or "validation report" in low:
        return "test_report"
    if "ecr" in low or "eco" in low or "engineering change" in low or "извещение об измен" in low:
        return "change"
    if "drawing" in low or "чертеж" in low or "чертёж" in low:
        return "drawing"
    if "requirement" in low or "технические требования" in low or "technical specification" in low:
        return "requirement"
    return "document"


def infer_metadata(filename: str, text: str, ext: str = "") -> dict:
    source = f"{filename}\n{text[:120000]}"
    result: dict = {}
    part = _first(PART_PATTERNS, source)
    rev = _first(REV_PATTERNS, source)
    material = _first(MATERIAL_PATTERNS, source)
    thickness = _first(THICKNESS_PATTERNS, source)
    mass = None
    mass_unit = None
    for p in MASS_PATTERNS:
        m = p.search(source)
        if m:
            mass = float(m.group(1).replace(",", "."))
            mass_unit = (m.group(2) or "kg").lower()
            if mass_unit in {"g", "г"}:
                mass /= 1000.0
            break
    if part:
        result["part_number"] = part.upper()
    if rev:
        result["revision"] = rev.upper()
    if material:
        result["material"] = re.split(r"[;\n\r]", material)[0].strip()
    if thickness:
        result["thickness_mm"] = float(thickness.replace(",", "."))
    if mass is not None:
        result["mass_kg"] = mass
    result["doc_type"] = classify_doc_type(filename, text, ext)
    return result
