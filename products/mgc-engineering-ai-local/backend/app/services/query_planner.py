import re


def plan_query(query: str) -> dict:
    upper = query.upper()
    part = None
    for token in re.findall(r"[A-Z0-9][A-Z0-9_.\-/]{4,}", upper):
        if any(c.isdigit() for c in token) and len(token) >= 6:
            part = token.strip(".,;:()[]")
            break

    revs = [m.upper() for m in re.findall(r"(?i)\b(?:REV(?:ISION)?\b|РЕВ(?:ИЗИЯ)?\b|版本|版次)\s*[:#\-]?\s*([A-Z0-9]{1,6})\b", query)]
    # Also understand compact engineering notation: C -> D / C vs D / C→D when intent is clearly revision-related.
    compact = re.findall(r"\b([A-Z0-9]{1,4})\s*(?:->|→|VS\.?|VERSUS|ДО|TO)\s*([A-Z0-9]{1,4})\b", upper)
    if compact and len(revs) < 2:
        revs = [compact[0][0], compact[0][1]]
    rev = revs[-1] if revs else None
    baseline = revs[-2] if len(revs) >= 2 else None

    q = query.lower()
    intent = "knowledge"
    if any(x in q for x in ["pfmea", "fmea", "control plan", "контрольный план", "special characteristic", "критическ характерист", "apqp", "ppap", "8d", "8д", "рекламац"]): intent = "quality_core_tools"
    elif any(x in q for x in ["design review", "ревью", "проверь конструк", "провер конструк"]): intent = "design_review"
    elif any(x in q for x in ["impact", "влия", "затрон"]): intent = "change_impact"
    elif any(x in q for x in ["similar", "похож", "аналог"]): intent = "geometry_similarity"
    elif any(x in q for x in ["ниокр", "evidence", "доказ", "пакет"]): intent = "evidence_pack"
    elif any(x in q for x in ["сравни", "compare", "difference", "разниц"]): intent = "revision_compare"
    elif any(x in q for x in ["bom", "состав", "спецификац", "компонент"]): intent = "bom"
    elif any(x in q for x in ["ошиб", "несоответ", "conflict", "противореч", "issue"]): intent = "validation"
    elif any(x in q for x in ["размер", "volume", "объем", "объём", "масса", "area", "площад", "геометр"]): intent = "cad_facts"
    return {"intent": intent, "part_number": part, "revision": rev, "baseline_revision": baseline, "revisions": revs}
