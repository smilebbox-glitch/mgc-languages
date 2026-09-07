from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from typing import Iterable

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.services.manufacturing_areas import ensure_project_areas, visible_project_areas

from app.db.models import (
    ChangeRequest,
    DesignReview,
    EngineeringLesson, EngineeringDecisionRecord, ChangeEffectivenessReview,
    Document,
    Project,
    Part,
    Problem8D,
    ProcessDefect,
    FieldQualityClaim,
    ValidationIssue,
)


CLOSED_CHANGE = {"implemented", "rejected", "cancelled"}
CLOSED_8D = {"closed", "cancelled"}
CLOSED_DEFECT = {"resolved", "closed", "cancelled"}
CLOSED_ISSUE = {"resolved"}
STOPWORDS = {
    "and", "or", "the", "a", "an", "to", "of", "in", "on", "for", "with", "from", "by", "is", "are", "was", "were",
    "и", "или", "в", "во", "на", "по", "для", "с", "со", "из", "от", "до", "к", "ко", "о", "об", "это", "как", "при", "что", "не",
    "part", "деталь", "изменение", "change", "issue", "problem", "проблема",
}
SOURCE_LABELS = {
    "lesson": "Валидированный урок",
    "change": "ECR/ECO",
    "8d": "8D",
    "defect": "Дефект процесса",
    "design_review": "Design Review",
    "validation_issue": "Инженерное замечание",
    "decision": "Engineering Decision",
    "effectiveness": "Change Effectiveness",
    "field_claim": "Field / Warranty Claim",
}


def _status(value) -> str:
    if value is None:
        return ""
    return value.value if hasattr(value, "value") else str(value)


def _doc_ok(ids: Iterable[str] | None, visible_document_ids: set[str]) -> bool:
    values = set(ids or [])
    return not values or values.issubset(visible_document_ids)


def _area_ok(area: str | None, requested: str | None, allowed: set[str]) -> bool:
    if area and area not in allowed:
        return False
    if requested:
        return area in {None, requested}
    return True


def _json_text(value) -> str:
    if value in (None, "", [], {}):
        return ""
    if isinstance(value, str):
        return value
    try:
        return json.dumps(value, ensure_ascii=False, sort_keys=True)
    except Exception:
        return str(value)


def _tokens(*values) -> set[str]:
    text = " ".join(_json_text(v) for v in values if v not in (None, ""))
    words = re.findall(r"[0-9A-Za-zА-Яа-яЁё][0-9A-Za-zА-Яа-яЁё._/+%-]*", text.lower())
    return {w.strip("._/+%-") for w in words if len(w.strip("._/+%-")) >= 2 and w not in STOPWORDS}


def _short(value, limit: int = 800) -> str:
    text = _json_text(value).strip()
    return text if len(text) <= limit else text[: limit - 1] + "…"


def _lesson_case(x: EngineeringLesson) -> dict:
    return {
        "case_id": f"lesson:{x.id}", "source_type": "lesson", "source_id": x.id,
        "project_code": x.project_code, "manufacturing_area": x.manufacturing_area, "part_number": x.part_number,
        "title": x.title, "problem": x.problem, "decision": x.decision or "", "outcome": x.outcome or "",
        "status": x.status, "effectiveness": x.effectiveness, "validated": x.status == "validated",
        "tags": x.tags or [], "evidence_document_ids": x.evidence_document_ids or [],
        "event_at": (x.validated_at or x.updated_at or x.created_at).isoformat(),
        "source_label": SOURCE_LABELS["lesson"], "reusable": x.status == "validated",
        "metadata": {"validated_by": x.validated_by, **(x.metadata_json or {})},
    }


def _change_case(x: ChangeRequest, project_code: str, area: str | None) -> dict:
    verification = (x.metadata_json or {}).get("verification_result")
    implemented = x.status == "implemented"
    return {
        "case_id": f"change:{x.id}", "source_type": "change", "source_id": x.id,
        "project_code": project_code, "manufacturing_area": area, "part_number": x.part_number,
        "title": f"{x.eco_code or x.code} · {x.title}",
        "problem": _short(x.reason or x.description or x.title),
        "decision": _short(x.implementation_plan or x.impact_json or ""),
        "outcome": _short(verification or ("Изменение внедрено; явный verification result не сохранён." if implemented else f"Статус: {x.status}")),
        "status": x.status, "effectiveness": "verified" if implemented and verification else ("positive" if implemented else "unknown"),
        "validated": bool(implemented and verification), "tags": ["ecr", "eco", x.risk_level, x.priority],
        "evidence_document_ids": x.affected_document_ids or [], "event_at": (x.completed_at or x.updated_at or x.created_at).isoformat(),
        "source_label": SOURCE_LABELS["change"], "reusable": bool(implemented and verification),
        "metadata": {"from_revision": x.from_revision, "to_revision": x.to_revision, "risk_level": x.risk_level, "priority": x.priority},
    }


def _8d_case(x: Problem8D) -> dict:
    d = x.disciplines_json or {}
    decision = d.get("d5") or d.get("d6") or d.get("d7") or d.get("corrective_action") or d.get("root_cause") or ""
    outcome = d.get("d6") or d.get("verification") or d.get("effectiveness") or (x.metadata_json or {}).get("effectiveness") or ""
    validated = x.status == "closed" and bool(outcome)
    return {
        "case_id": f"8d:{x.id}", "source_type": "8d", "source_id": x.id,
        "project_code": x.project_code, "manufacturing_area": x.manufacturing_area, "part_number": x.part_number,
        "title": f"8D · {x.title}", "problem": _short(d.get("d2") or x.title),
        "decision": _short(decision), "outcome": _short(outcome or ("8D закрыт без отдельного effectiveness result." if x.status == "closed" else f"Статус: {x.status}")),
        "status": x.status, "effectiveness": "verified" if validated else ("positive" if x.status == "closed" else "unknown"),
        "validated": validated, "tags": ["8d", x.severity, *(str(k) for k in d.keys())],
        "evidence_document_ids": x.evidence_document_ids or [], "event_at": (x.updated_at or x.created_at).isoformat(),
        "source_label": SOURCE_LABELS["8d"], "reusable": validated,
        "metadata": {"severity": x.severity, "complaint_reference": x.complaint_reference, "linked_change_id": x.linked_change_id},
    }


def _defect_case(x: ProcessDefect) -> dict:
    resolved = x.status in CLOSED_DEFECT
    meta = x.metadata_json or {}
    decision = meta.get("corrective_action") or meta.get("containment") or (f"Связан с 8D {x.linked_8d_id}" if x.linked_8d_id else "")
    outcome = meta.get("verification_result") or meta.get("effectiveness") or ("Дефект закрыт." if resolved else f"Статус: {x.status}")
    return {
        "case_id": f"defect:{x.id}", "source_type": "defect", "source_id": x.id,
        "project_code": x.project_code, "manufacturing_area": x.manufacturing_area, "part_number": x.part_number,
        "title": f"{x.defect_code or 'DEFECT'} · {x.title}", "problem": x.title,
        "decision": _short(decision), "outcome": _short(outcome), "status": x.status,
        "effectiveness": "verified" if resolved and bool(meta.get("verification_result") or meta.get("effectiveness")) else ("positive" if resolved else "unknown"),
        "validated": bool(resolved and (meta.get("verification_result") or meta.get("effectiveness"))),
        "tags": ["defect", x.severity, x.defect_code or ""], "evidence_document_ids": x.evidence_document_ids or [],
        "event_at": (x.occurred_at or x.updated_at or x.created_at).isoformat(), "source_label": SOURCE_LABELS["defect"],
        "reusable": bool(resolved and (meta.get("verification_result") or meta.get("effectiveness"))),
        "metadata": {"severity": x.severity, "quantity": x.quantity, "linked_8d_id": x.linked_8d_id, "operation_id": x.operation_id},
    }


def _review_case(x: DesignReview, project_code: str, area: str | None) -> dict:
    status = _status(x.status)
    report = x.report_json or {}
    decision = report.get("recommended_actions") or report.get("decision_hint") or ""
    outcome = x.summary or report.get("summary") or f"Статус review: {status}"
    return {
        "case_id": f"design_review:{x.id}", "source_type": "design_review", "source_id": x.id,
        "project_code": project_code, "manufacturing_area": area, "part_number": x.part_number,
        "title": f"Design Review · {x.part_number} Rev {x.revision}", "problem": _short(x.findings or x.summary or "Design Review"),
        "decision": _short(decision), "outcome": _short(outcome), "status": status,
        "effectiveness": "positive" if status == "approved" else ("negative" if status == "rejected" else "unknown"),
        "validated": status in {"approved", "rejected"}, "tags": ["design_review", status],
        "evidence_document_ids": x.evidence_document_ids or [], "event_at": (x.updated_at or x.created_at).isoformat(),
        "source_label": SOURCE_LABELS["design_review"], "reusable": status == "approved",
        "metadata": {"revision": x.revision, "baseline_revision": x.baseline_revision, "risk_score": x.risk_score},
    }


def _issue_case(x: ValidationIssue, project_code: str, area: str | None) -> dict:
    status = _status(x.status)
    details = x.details or {}
    decision = details.get("resolution") or details.get("action") or details.get("decision") or ""
    outcome = details.get("verification_result") or details.get("outcome") or ("Замечание закрыто." if status == "resolved" else f"Статус: {status}")
    return {
        "case_id": f"validation_issue:{x.id}", "source_type": "validation_issue", "source_id": x.id,
        "project_code": project_code, "manufacturing_area": area, "part_number": x.part_number,
        "title": f"{x.rule_code} · {x.title}", "problem": x.title, "decision": _short(decision), "outcome": _short(outcome),
        "status": status, "effectiveness": "positive" if status == "resolved" else "unknown",
        "validated": bool(status == "resolved" and decision), "tags": ["validation", x.rule_code, _status(x.severity)],
        "evidence_document_ids": x.document_ids or [], "event_at": (x.updated_at or x.created_at).isoformat(),
        "source_label": SOURCE_LABELS["validation_issue"], "reusable": bool(status == "resolved" and decision),
        "metadata": {"rule_code": x.rule_code, "severity": _status(x.severity), "revision": x.revision},
    }



def _decision_case(x: EngineeringDecisionRecord) -> dict:
    validated = x.effectiveness_status in {"effective", "ineffective"} and x.status in {"verified", "closed"}
    return {
        "case_id": f"decision:{x.id}", "source_type": "decision", "source_id": x.id,
        "project_code": x.project_code, "manufacturing_area": x.manufacturing_area, "part_number": x.part_number,
        "title": f"{x.code} · {x.title}", "problem": _short(x.problem_statement),
        "decision": _short(x.chosen_option + (" — " + x.rationale if x.rationale else "")),
        "outcome": _short(x.effectiveness_summary or x.expected_result or f"Effectiveness: {x.effectiveness_status}"),
        "status": x.status, "effectiveness": "verified" if validated else ("positive" if x.effectiveness_status == "effective" else ("negative" if x.effectiveness_status == "ineffective" else "unknown")),
        "validated": validated, "tags": ["decision", x.accepted_risk, x.effectiveness_status],
        "evidence_document_ids": x.evidence_document_ids or [], "event_at": (x.updated_at or x.created_at).isoformat(),
        "source_label": SOURCE_LABELS["decision"], "reusable": validated,
        "metadata": {"change_id": x.change_id, "accepted_risk": x.accepted_risk, "approved_by": x.approved_by},
    }


def _effectiveness_case(x: ChangeEffectivenessReview, part_number: str | None) -> dict:
    final = x.status in {"effective", "ineffective", "inconclusive"} and bool(x.reviewed_by)
    return {
        "case_id": f"effectiveness:{x.id}", "source_type": "effectiveness", "source_id": x.id,
        "project_code": x.project_code, "manufacturing_area": x.manufacturing_area, "part_number": part_number,
        "title": f"{x.code} · Change effectiveness", "problem": _short(x.target_description),
        "decision": _short(f"Change {x.change_id}"), "outcome": _short(x.conclusion or f"Observed: {x.observed_value} {x.unit or ''}"),
        "status": x.status, "effectiveness": "verified" if final and x.status == "effective" else ("negative" if final and x.status == "ineffective" else "unknown"),
        "validated": final, "tags": ["effectiveness", x.status, x.unit or ""],
        "evidence_document_ids": x.evidence_document_ids or [], "event_at": (x.reviewed_at or x.updated_at or x.created_at).isoformat(),
        "source_label": SOURCE_LABELS["effectiveness"], "reusable": final,
        "metadata": {"change_id": x.change_id, "baseline_value": x.baseline_value, "target_value": x.target_value, "observed_value": x.observed_value, "population": x.population, "reviewed_by": x.reviewed_by},
    }



def _field_claim_case(x: FieldQualityClaim) -> dict:
    closed=x.status in {"closed","cancelled"}
    return {
        "case_id":f"field_claim:{x.id}","source_type":"field_claim","source_id":x.id,
        "project_code":x.project_code,"manufacturing_area":x.manufacturing_area,"part_number":x.part_number,
        "title":f"Field · {x.failure_mode}","problem":_short(x.failure_mode),
        "decision":_short(f"Linked 8D {x.linked_8d_id}" if x.linked_8d_id else "Field investigation required"),
        "outcome":_short((x.metadata_json or {}).get("outcome") or f"Status: {x.status}"),
        "status":x.status,"effectiveness":"unknown","validated":False,
        "tags":["field","warranty",x.severity,x.supplier_code or "",x.failure_family or "",x.market or "",x.climate_zone or ""],"evidence_document_ids":x.evidence_document_ids or [],
        "event_at":(x.claim_at or x.updated_at or x.created_at).isoformat(),"source_label":SOURCE_LABELS["field_claim"],"reusable":closed and bool((x.metadata_json or {}).get("verified_outcome")),
        "metadata":{"claim_reference":x.claim_reference,"vehicle_identifier":x.vehicle_identifier,"supplier_code":x.supplier_code,"revision":x.revision,"failure_family":x.failure_family,"mileage_km":x.mileage_km,"market":x.market,"climate_zone":x.climate_zone,"repair_method":x.repair_method,"repeat_repair":bool(x.repeat_repair),"no_trouble_found":bool(x.no_trouble_found),"linked_8d_id":x.linked_8d_id,"cost_estimate":x.cost_estimate,"currency":x.currency},
    }


def _part_area_map(db: Session, project_code: str, visible_document_ids: set[str]) -> dict[str, str | None]:
    # Prefer a stable part-level area tag if provided in part metadata; document-derived area is
    # intentionally not queried here to avoid widening access beyond the already supplied ACL context.
    rows = db.scalars(select(Part).where(Part.project_code == project_code)).all()
    return {p.part_number: (p.metadata_json or {}).get("manufacturing_area") for p in rows}


def accessible_memory_contexts(
    db: Session,
    current_project: Project,
    identity_groups: Iterable[str],
    visible_documents: Iterable[Document],
    manufacturing_area: str | None = None,
    scope: str = "project",
) -> list[tuple[Project, set[str], set[str], set[str]]]:
    """Build ACL-safe project contexts from documents already visible to the caller.

    The caller is responsible for document ACL filtering; this function adds Project and
    Manufacturing Area ACL and never widens the supplied visible-document set.
    """
    if scope not in {"project", "portfolio"}:
        raise ValueError("Unknown memory scope")
    groups = set(identity_groups) | {"all"}
    projects = [current_project] if scope == "project" else [
        p for p in db.scalars(select(Project)).all()
        if bool(set(p.acl_groups or ["all"]) & groups)
    ]
    docs_all = list(visible_documents)
    out: list[tuple[Project, set[str], set[str], set[str]]] = []
    for project in projects:
        ensure_project_areas(db, project)
        allowed_areas = {a.code for a in visible_project_areas(db, project, list(identity_groups))}
        if manufacturing_area and manufacturing_area not in allowed_areas:
            if project.code == current_project.code:
                raise LookupError("Manufacturing area not found")
            continue
        docs = [d for d in docs_all if d.project_code == project.code and (not d.manufacturing_area or d.manufacturing_area in allowed_areas)]
        if manufacturing_area:
            explicit = {d.part_number for d in docs if d.manufacturing_area == manufacturing_area and d.part_number}
            docs = [d for d in docs if d.manufacturing_area == manufacturing_area or (not d.manufacturing_area and (not d.part_number or d.part_number in explicit or d.doc_type == "bom"))]
        out.append((project, {d.id for d in docs}, {d.part_number for d in docs if d.part_number}, allowed_areas))
    return out


def collect_project_cases(
    db: Session,
    project_code: str,
    visible_document_ids: set[str],
    visible_part_numbers: set[str],
    manufacturing_area: str | None = None,
    allowed_area_codes: set[str] | None = None,
    include_open: bool = True,
) -> list[dict]:
    """Collect ACL-safe historical/current engineering cases for one project."""
    allowed = set(allowed_area_codes or [])
    area_by_part = _part_area_map(db, project_code, visible_document_ids)
    cases: list[dict] = []

    lessons = db.scalars(select(EngineeringLesson).where(EngineeringLesson.project_code == project_code).order_by(EngineeringLesson.updated_at.desc())).all()
    for x in lessons:
        if x.status == "archived" or (x.part_number and x.part_number not in visible_part_numbers):
            continue
        if not _area_ok(x.manufacturing_area, manufacturing_area, allowed) or not _doc_ok(x.evidence_document_ids, visible_document_ids):
            continue
        cases.append(_lesson_case(x))

    if visible_part_numbers:
        changes = db.scalars(select(ChangeRequest).where(ChangeRequest.part_number.in_(visible_part_numbers)).order_by(ChangeRequest.updated_at.desc())).all()
        for x in changes:
            if not include_open and x.status not in CLOSED_CHANGE:
                continue
            if not _doc_ok(x.affected_document_ids, visible_document_ids):
                continue
            area = area_by_part.get(x.part_number)
            if not _area_ok(area, manufacturing_area, allowed):
                continue
            cases.append(_change_case(x, project_code, area))

        reviews = db.scalars(select(DesignReview).where(DesignReview.part_number.in_(visible_part_numbers)).order_by(DesignReview.updated_at.desc())).all()
        for x in reviews:
            if not include_open and _status(x.status) not in {"approved", "rejected"}:
                continue
            if not _doc_ok(x.evidence_document_ids, visible_document_ids):
                continue
            area = area_by_part.get(x.part_number)
            if not _area_ok(area, manufacturing_area, allowed):
                continue
            cases.append(_review_case(x, project_code, area))

        issues = db.scalars(select(ValidationIssue).where(ValidationIssue.part_number.in_(visible_part_numbers)).order_by(ValidationIssue.updated_at.desc())).all()
        for x in issues:
            if not include_open and _status(x.status) not in CLOSED_ISSUE:
                continue
            if not _doc_ok(x.document_ids, visible_document_ids):
                continue
            area = area_by_part.get(x.part_number)
            if not _area_ok(area, manufacturing_area, allowed):
                continue
            cases.append(_issue_case(x, project_code, area))

    problems = db.scalars(select(Problem8D).where(Problem8D.project_code == project_code).order_by(Problem8D.updated_at.desc())).all()
    for x in problems:
        if x.part_number and x.part_number not in visible_part_numbers:
            continue
        if not include_open and x.status not in CLOSED_8D:
            continue
        if not _area_ok(x.manufacturing_area, manufacturing_area, allowed) or not _doc_ok(x.evidence_document_ids, visible_document_ids):
            continue
        cases.append(_8d_case(x))

    defects = db.scalars(select(ProcessDefect).where(ProcessDefect.project_code == project_code).order_by(ProcessDefect.occurred_at.desc())).all()
    for x in defects:
        if x.part_number and x.part_number not in visible_part_numbers:
            continue
        if not include_open and x.status not in CLOSED_DEFECT:
            continue
        if not _area_ok(x.manufacturing_area, manufacturing_area, allowed) or not _doc_ok(x.evidence_document_ids, visible_document_ids):
            continue
        cases.append(_defect_case(x))


    # v5.7 field/warranty feedback becomes searchable engineering memory, still with ACL fail-closed.
    claims = db.scalars(select(FieldQualityClaim).where(FieldQualityClaim.project_code == project_code).order_by(FieldQualityClaim.claim_at.desc())).all()
    for x in claims:
        if x.part_number and x.part_number not in visible_part_numbers:
            continue
        if not include_open and x.status not in {"closed","cancelled"}:
            continue
        if not _area_ok(x.manufacturing_area, manufacturing_area, allowed) or not _doc_ok(x.evidence_document_ids, visible_document_ids):
            continue
        cases.append(_field_claim_case(x))

    # v5.3 closes the loop: human-reviewed decisions/effectiveness become searchable historical evidence.
    decisions = db.scalars(select(EngineeringDecisionRecord).where(EngineeringDecisionRecord.project_code == project_code).order_by(EngineeringDecisionRecord.updated_at.desc())).all()
    for x in decisions:
        if x.part_number and x.part_number not in visible_part_numbers:
            continue
        if not _area_ok(x.manufacturing_area, manufacturing_area, allowed) or not _doc_ok(x.evidence_document_ids, visible_document_ids):
            continue
        cases.append(_decision_case(x))

    changes_by_id = {c.id: c for c in db.scalars(select(ChangeRequest)).all()}
    reviews = db.scalars(select(ChangeEffectivenessReview).where(ChangeEffectivenessReview.project_code == project_code).order_by(ChangeEffectivenessReview.updated_at.desc())).all()
    for x in reviews:
        change = changes_by_id.get(x.change_id)
        pn = change.part_number if change else None
        if pn and pn not in visible_part_numbers:
            continue
        if not include_open and x.status not in {"effective", "ineffective", "inconclusive"}:
            continue
        if not _area_ok(x.manufacturing_area, manufacturing_area, allowed) or not _doc_ok(x.evidence_document_ids, visible_document_ids):
            continue
        cases.append(_effectiveness_case(x, pn))

    # Exact source identity is retained; duplicate lesson + source records are intentional so users
    # can see both the raw historical case and the human-validated reusable lesson.
    return cases


def _score_case(case: dict, query_tokens: set[str], part_number: str | None, manufacturing_area: str | None, source_types: set[str] | None = None) -> tuple[float, list[str]]:
    if source_types and case["source_type"] not in source_types:
        return 0.0, []
    case_tokens = _tokens(case.get("title"), case.get("problem"), case.get("decision"), case.get("outcome"), case.get("tags"), case.get("metadata"))
    reasons: list[str] = []
    score = 0.0
    if query_tokens:
        overlap = len(query_tokens & case_tokens)
        union = max(len(query_tokens | case_tokens), 1)
        lexical = overlap / union
        containment = overlap / max(len(query_tokens), 1)
        text_score = 0.55 * containment + 0.45 * lexical
        score += 0.48 * text_score
        if overlap:
            common = sorted(query_tokens & case_tokens)[:6]
            reasons.append("совпадают признаки: " + ", ".join(common))
    else:
        score += 0.10
    if part_number and case.get("part_number") == part_number:
        score += 0.28
        reasons.append("та же деталь")
    elif part_number and case.get("part_number"):
        # Shared normalized prefix helps part-family searches but never asserts equivalence.
        a = re.split(r"[-_/]", part_number)[0]
        b = re.split(r"[-_/]", case["part_number"])[0]
        if a and b and a == b and len(a) >= 4:
            score += 0.08
            reasons.append("похожий номер/семейство детали")
    if manufacturing_area and case.get("manufacturing_area") == manufacturing_area:
        score += 0.10
        reasons.append("та же производственная зона")
    if case.get("source_type") == "lesson" and case.get("validated"):
        score += 0.08
        reasons.append("валидированный Lessons Learned")
    elif case.get("validated"):
        score += 0.04
        reasons.append("есть подтверждённый результат")
    if case.get("effectiveness") in {"verified", "positive"}:
        score += 0.02
    return min(round(score, 4), 1.0), reasons


def search_cases(cases: list[dict], query: str = "", part_number: str | None = None, manufacturing_area: str | None = None, source_types: Iterable[str] | None = None, limit: int = 12, include_open: bool = True) -> list[dict]:
    q_tokens = _tokens(query)
    pn = part_number.strip().upper() if part_number else None
    wanted = set(source_types or []) or None
    ranked: list[dict] = []
    for case in cases:
        if not include_open and case.get("source_type") != "lesson" and case.get("status") not in {"implemented", "closed", "resolved", "approved", "rejected", "cancelled"}:
            continue
        score, reasons = _score_case(case, q_tokens, pn, manufacturing_area, wanted)
        # With a text query require some actual lexical signal unless the exact part matches.
        if q_tokens and score < 0.08 and case.get("part_number") != pn:
            continue
        row = dict(case)
        row["similarity"] = score
        row["why_similar"] = reasons or ["исторический кейс в доступной инженерной области"]
        ranked.append(row)
    ranked.sort(key=lambda x: (x["similarity"], bool(x.get("validated")), x.get("event_at") or ""), reverse=True)
    return ranked[: max(1, min(int(limit or 12), 50))]


def recurrence_signals(cases: list[dict], limit: int = 8) -> list[dict]:
    current = [c for c in cases if c["source_type"] in {"defect", "8d", "change", "validation_issue", "field_claim"} and c.get("status") not in {"implemented", "closed", "resolved", "rejected", "cancelled"}][:120]
    history = [c for c in cases if c.get("reusable") or (c["source_type"] in {"defect", "8d", "change", "validation_issue", "field_claim"} and c.get("status") in {"implemented", "closed", "resolved"})][:600]
    out: list[dict] = []
    for cur in current:
        q = " ".join([cur.get("title", ""), cur.get("problem", ""), " ".join(cur.get("tags") or [])])
        matches = search_cases(history, q, cur.get("part_number"), cur.get("manufacturing_area"), limit=3, include_open=False)
        matches = [m for m in matches if m.get("case_id") != cur.get("case_id") and m.get("similarity", 0) >= 0.34]
        if not matches:
            continue
        best = matches[0]
        out.append({
            "current_case": {k: cur.get(k) for k in ("case_id", "source_type", "title", "part_number", "project_code", "manufacturing_area", "status")},
            "historical_case": {k: best.get(k) for k in ("case_id", "source_type", "title", "part_number", "project_code", "manufacturing_area", "status", "decision", "outcome", "effectiveness")},
            "similarity": best["similarity"], "why_similar": best["why_similar"],
            "severity": "high" if best["similarity"] >= 0.60 else "medium",
            "note": "Похожий исторический кейс найден. Это сигнал для проверки повторяемости, а не доказательство одинаковой первопричины.",
        })
    out.sort(key=lambda x: x["similarity"], reverse=True)
    return out[:limit]


def memory_metrics(cases: list[dict]) -> dict:
    historical = [c for c in cases if c["source_type"] != "lesson"]
    closed = [c for c in historical if c.get("status") in {"implemented", "closed", "resolved", "approved", "rejected", "cancelled"}]
    with_outcome = [c for c in closed if (c.get("outcome") or "").strip() and c.get("outcome") not in {"Дефект закрыт.", "Замечание закрыто."}]
    lessons = [c for c in cases if c["source_type"] == "lesson"]
    validated = [c for c in lessons if c.get("validated")]
    coverage = round(100.0 * len(with_outcome) / len(closed), 1) if closed else 0.0
    return {
        "historical_cases": len(historical), "closed_cases": len(closed), "closed_with_outcome": len(with_outcome),
        "lessons": len(lessons), "validated_lessons": len(validated), "outcome_capture_pct": coverage,
        "governance": "Historical case != validated lesson. Reuse requires engineer judgement; validated lessons remain advisory.",
    }


def build_memory_answer(query: str, matches: list[dict]) -> str:
    if not matches:
        return "В доступной Engineering Knowledge Memory похожих исторических кейсов не найдено. Это не означает, что аналогов в компании нет: часть проектов или evidence может быть недоступна текущему пользователю."
    lines = [f"Найдено похожих кейсов: {len(matches)}."]
    strong = [m for m in matches if m.get("similarity", 0) >= 0.45]
    if strong:
        lines.append(f"Кейсов с высокой/средней похожестью: {len(strong)}.")
    lines.append("Наиболее релевантные исторические решения:")
    for i, m in enumerate(matches[:5], 1):
        result = (m.get("outcome") or "результат отдельно не зафиксирован").strip()
        decision = (m.get("decision") or "решение отдельно не зафиксировано").strip()
        validation = "валидировано" if m.get("validated") else "требует инженерной оценки"
        lines.append(f"{i}. {m['title']} [{m['project_code']}] — {decision}. Результат: {result}. Статус знания: {validation}.")
    lines.append("Важно: похожесть не доказывает одинаковую первопричину. Перед повторным применением решения проверьте ревизию, вариант автомобиля, процесс, поставщика и evidence.")
    return "\n".join(lines)


def knowledge_memory_workspace(cases: list[dict], query: str = "", part_number: str | None = None, manufacturing_area: str | None = None, source_types: Iterable[str] | None = None, limit: int = 12) -> dict:
    matches = search_cases(cases, query, part_number, manufacturing_area, source_types, limit, include_open=True)
    recurrences = recurrence_signals(cases)
    validated_lessons = [c for c in cases if c["source_type"] == "lesson" and c.get("validated")]
    draft_lessons = [c for c in cases if c["source_type"] == "lesson" and c.get("status") == "draft"]
    validated_lessons.sort(key=lambda x: x.get("event_at") or "", reverse=True)
    draft_lessons.sort(key=lambda x: x.get("event_at") or "", reverse=True)
    return {
        "metrics": memory_metrics(cases),
        "matches": matches,
        "validated_lessons": validated_lessons[:12],
        "draft_lessons": draft_lessons[:12],
        "recurrence_signals": recurrences,
        "source_types": SOURCE_LABELS,
        "query": query, "part_number": part_number, "manufacturing_area": manufacturing_area,
        "deterministic_similarity": True,
        "cpu_only_core": True,
        "historical_case_is_not_recommendation": True,
        "human_validation_required": True,
        "advisory_only": True,
    }


def create_lesson_from_case(db: Session, case: dict, *, created_by: str, title: str | None = None, problem: str | None = None, decision: str | None = None, outcome: str | None = None, effectiveness: str = "unknown", tags: list[str] | None = None) -> EngineeringLesson:
    if case.get("source_type") == "lesson":
        raise ValueError("A lesson cannot be promoted from another lesson")
    existing = db.scalar(select(EngineeringLesson).where(
        EngineeringLesson.project_code == case["project_code"],
        EngineeringLesson.source_type == case["source_type"],
        EngineeringLesson.source_id == case["source_id"],
    ))
    if existing:
        return existing
    row = EngineeringLesson(
        project_code=case["project_code"], manufacturing_area=case.get("manufacturing_area"), part_number=case.get("part_number"),
        source_type=case["source_type"], source_id=case["source_id"], title=(title or case.get("title") or "Lessons Learned")[:512],
        problem=(problem or case.get("problem") or case.get("title") or "Historical engineering case"),
        decision=decision if decision is not None else case.get("decision"), outcome=outcome if outcome is not None else case.get("outcome"),
        effectiveness=effectiveness if effectiveness != "unknown" else (case.get("effectiveness") or "unknown"),
        status="draft", tags=sorted({x for x in ((tags or []) + (case.get("tags") or [])) if x}),
        evidence_document_ids=case.get("evidence_document_ids") or [], created_by=created_by,
        metadata_json={"source_case_id": case["case_id"], "source_snapshot_at": datetime.now(timezone.utc).isoformat()},
    )
    db.add(row); db.commit(); db.refresh(row)
    return row


def validate_lesson(db: Session, lesson: EngineeringLesson, *, validator: str, status: str, outcome: str | None = None, effectiveness: str | None = None) -> EngineeringLesson:
    if status not in {"draft", "validated", "archived"}:
        raise ValueError("Unsupported lesson status")
    if outcome is not None:
        lesson.outcome = outcome.strip()
    if effectiveness is not None:
        lesson.effectiveness = effectiveness
    lesson.status = status
    if status == "validated":
        if not (lesson.outcome or "").strip():
            raise ValueError("Validated lesson requires an explicit outcome")
        if lesson.effectiveness not in {"positive", "mixed", "negative", "verified"}:
            raise ValueError("Validated lesson requires explicit effectiveness")
        lesson.validated_by = validator
        lesson.validated_at = datetime.now(timezone.utc)
    elif status == "draft":
        lesson.validated_by = None
        lesson.validated_at = None
    # archived lessons retain prior validation provenance when present.
    db.commit(); db.refresh(lesson)
    return lesson


def serialize_lesson(x: EngineeringLesson) -> dict:
    return _lesson_case(x)
