from __future__ import annotations

from collections import Counter
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import DesignReview, Document, PartRevision, ReviewStatus
from app.services.change_impact import analyze_change_impact
from app.services.validation import validate_part


def _severity_weight(value: str) -> int:
    return {"info": 3, "warning": 12, "critical": 30}.get(value, 8)


def _doc_summary(doc: Document) -> dict:
    meta = doc.extracted_metadata or {}
    drawing = meta.get("engineering_drawing") or {}
    links = meta.get("geometry_links") or {}
    vision = meta.get("vision_inspection") or {}
    return {
        "id": doc.id,
        "filename": doc.filename,
        "doc_type": doc.doc_type,
        "sha256": doc.sha256,
        "status": doc.status.value if hasattr(doc.status, "value") else str(doc.status),
        "drawing_entities": len(drawing.get("entities") or []),
        "geometry_link_status": links.get("status") or "not_run",
        "geometry_link_coverage": links.get("coverage"),
        "vision_pages": len(vision.get("pages") or []),
    }


def _extract_values(doc: Document, kind: str) -> list[str]:
    meta = doc.extracted_metadata or {}
    values: list[str] = []
    if kind == "material":
        for key in ("material", "material_grade"):
            value = meta.get(key)
            if value not in (None, ""):
                values.append(str(value).strip())
    if kind == "thickness":
        for key in ("thickness_mm", "wall_thickness_mm"):
            value = meta.get(key)
            if value not in (None, ""):
                values.append(str(value).strip())
    drawing = meta.get("engineering_drawing") or {}
    for entity in drawing.get("entities") or []:
        et = str(entity.get("type") or "").lower()
        if kind == "material" and et == "material":
            value = entity.get("value") or entity.get("raw")
            if value: values.append(str(value).strip())
        if kind == "thickness" and et == "thickness":
            value = entity.get("value_mm") if entity.get("value_mm") is not None else entity.get("value")
            if value is not None: values.append(str(value).strip())
    return [v for v in values if v]


def _recommendations(findings: list[dict]) -> list[str]:
    codes = {f.get("code") for f in findings}
    actions: list[str] = []
    if "MISSING_CAD" in codes: actions.append("Добавить 3D-модель той же детали и ревизии.")
    if "MISSING_DRAWING" in codes: actions.append("Добавить утверждённый чертёж текущей ревизии.")
    if "MISSING_BOM" in codes: actions.append("Добавить или синхронизировать BOM для текущей ревизии.")
    if "DRAWING_CAD_LINK_NOT_RUN" in codes: actions.append("Запустить «Связать с 3D» для чертежа перед выпуском ревизии.")
    if "DRAWING_CAD_LINK_LOW_COVERAGE" in codes: actions.append("Проверить размеры, не подтверждённые 3D-моделью, и неоднозначные геометрические кандидаты.")
    if "VISION_DISAGREEMENT" in codes: actions.append("Инженеру вручную проверить области, где VLM не согласился с детерминированным парсером.")
    if "MATERIAL_CONFLICT" in codes: actions.append("Согласовать материал между чертежом, спецификацией, BOM и 3D/PLM метаданными.")
    if "THICKNESS_CONFLICT" in codes: actions.append("Согласовать толщину между чертежом и остальными источниками.")
    if any(f.get("severity") == "critical" for f in findings): actions.append("Не выпускать ревизию до disposition всех критичных замечаний.")
    if not actions: actions.append("Явных блокирующих расхождений не найдено; выполнить стандартное инженерное утверждение.")
    return actions


def run_design_review(db: Session, part_number: str, revision: str, baseline_revision: str | None, user: str, allowed_document_ids: set[str] | None = None) -> DesignReview:
    pn, rev = part_number.upper(), revision.upper()
    baseline = baseline_revision.upper() if baseline_revision else None
    target = db.scalar(select(PartRevision).where(PartRevision.part_number == pn, PartRevision.revision == rev))
    if not target:
        raise ValueError("Target revision not found")

    docs = db.scalars(select(Document).where(Document.part_number == pn, Document.revision == rev).order_by(Document.created_at)).all()
    if allowed_document_ids is not None:
        docs = [d for d in docs if d.id in allowed_document_ids]
    if not docs:
        raise ValueError("Target revision is not visible to the current identity")

    findings: list[dict] = []
    for issue in validate_part(db, pn, allowed_document_ids):
        if issue.revision and issue.revision != rev:
            continue
        findings.append({
            "type": "validation", "severity": issue.severity.value, "code": issue.rule_code,
            "title": issue.title, "details": issue.details, "document_ids": issue.document_ids,
        })

    impact = None
    revision_delta = None
    if baseline:
        impact = analyze_change_impact(db, pn, baseline, rev, allowed_document_ids=allowed_document_ids)
        revision_delta = impact.get("revision_delta", {})
        for change in revision_delta.get("metadata_changes", []):
            findings.append({"type": "revision_change", "severity": "info", "code": "REV_DELTA", "title": f"Изменено поле {change['field']}", "details": change})
        for change in revision_delta.get("bom_changes", []):
            findings.append({"type": "bom_change", "severity": "warning", "code": "BOM_DELTA", "title": f"Изменён BOM: {change['part_number']}", "details": change})

    by_type = Counter(d.doc_type for d in docs if d.doc_type)
    for expected in ["cad", "drawing", "bom"]:
        if not by_type.get(expected):
            findings.append({"type": "completeness", "severity": "warning", "code": f"MISSING_{expected.upper()}", "title": f"Нет обязательного источника: {expected}", "details": {"revision": rev}})

    drawings = [d for d in docs if d.doc_type == "drawing"]
    for drawing in drawings:
        meta = drawing.extracted_metadata or {}
        links = meta.get("geometry_links") or {}
        if not links or links.get("status") in {None, "not_run"}:
            findings.append({"type": "drawing_cad", "severity": "warning", "code": "DRAWING_CAD_LINK_NOT_RUN", "title": "Не выполнена проверка чертёж ↔ 3D", "details": {"document_id": drawing.id}, "document_ids": [drawing.id]})
        elif links.get("status") == "ready":
            coverage = float(links.get("coverage") or 0.0)
            ambiguous = int(links.get("linked_multiple") or 0)
            unmatched = int(links.get("unmatched") or 0)
            if coverage < 0.8 or unmatched or ambiguous:
                severity = "critical" if coverage < 0.5 else "warning"
                findings.append({"type": "drawing_cad", "severity": severity, "code": "DRAWING_CAD_LINK_LOW_COVERAGE", "title": "Не все размеры чертежа однозначно подтверждены 3D", "details": {"document_id": drawing.id, "coverage": coverage, "ambiguous": ambiguous, "unmatched": unmatched}, "document_ids": [drawing.id]})
        vision = meta.get("vision_inspection") or {}
        disagreements = len((vision.get("consensus") or {}).get("disagreements") or [])
        if disagreements:
            findings.append({"type": "vision", "severity": "warning", "code": "VISION_DISAGREEMENT", "title": "Есть расхождения между VLM и детерминированным разбором", "details": {"document_id": drawing.id, "disagreements": disagreements}, "document_ids": [drawing.id]})

    materials = sorted({v.upper() for d in docs for v in _extract_values(d, "material")})
    if len(materials) > 1:
        findings.append({"type": "consistency", "severity": "critical", "code": "MATERIAL_CONFLICT", "title": "Материал отличается между инженерными источниками", "details": {"values": materials}, "document_ids": [d.id for d in docs]})
    thicknesses = sorted({v for d in docs for v in _extract_values(d, "thickness")})
    if len(thicknesses) > 1:
        findings.append({"type": "consistency", "severity": "warning", "code": "THICKNESS_CONFLICT", "title": "Толщина отличается между инженерными источниками", "details": {"values": thicknesses}, "document_ids": [d.id for d in docs]})

    risk = sum(_severity_weight(f.get("severity", "warning")) for f in findings)
    if impact:
        risk += int(float(impact.get("risk_score", 0)) * 0.30)
    risk = min(100.0, float(risk))
    blocking = [f for f in findings if f.get("severity") in {"warning", "critical"}]
    status = ReviewStatus.review_required if blocking else ReviewStatus.approved

    checklist = [
        {"item": "3D-модель", "status": "ok" if by_type.get("cad") else "missing"},
        {"item": "Чертёж", "status": "ok" if by_type.get("drawing") else "missing"},
        {"item": "BOM", "status": "ok" if by_type.get("bom") else "missing"},
        {"item": "Чертёж ↔ 3D", "status": "ok" if drawings and all(((d.extracted_metadata or {}).get("geometry_links") or {}).get("status") == "ready" for d in drawings) else "review"},
        {"item": "Критичные замечания", "status": "review" if any(f.get("severity") == "critical" for f in findings) else "ok"},
    ]
    recommendations = _recommendations(findings)
    evidence = [_doc_summary(d) for d in docs]
    report = {
        "title": f"Design Review · {pn} Rev {rev}",
        "part_number": pn,
        "revision": rev,
        "baseline_revision": baseline,
        "risk_score": risk,
        "decision_hint": "Требуется решение инженера" if blocking else "Автоматических блокеров не найдено",
        "checklist": checklist,
        "recommended_actions": recommendations,
        "evidence": evidence,
        "revision_delta": revision_delta,
        "change_impact": impact,
        "finding_counts": dict(Counter(f.get("severity", "warning") for f in findings)),
    }
    summary = f"{pn} Rev {rev}: риск {risk:.0f}/100, замечаний {len(findings)}, из них критичных {report['finding_counts'].get('critical', 0)}."
    if blocking:
        summary += " Требуется инженерное рассмотрение перед утверждением."
    else:
        summary += " Автоматических блокирующих расхождений не найдено."

    review = DesignReview(
        part_number=pn, revision=rev, baseline_revision=baseline,
        status=status, risk_score=risk, summary=summary, findings=findings,
        evidence_document_ids=[d.id for d in docs], report_json=report, created_by=user,
    )
    db.add(review); db.commit(); db.refresh(review)
    return review
