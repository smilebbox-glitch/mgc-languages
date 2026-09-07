from __future__ import annotations

from datetime import datetime, timezone
from typing import Iterable

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import APQPDeliverable, ControlPlanItem, PFMEAItem, PPAPSubmission, Problem8D, SpecialCharacteristic


TERMINAL_8D = {"closed", "cancelled"}
TERMINAL_APQP = {"done", "waived"}
ACTIVE_CP = {"active", "verified"}
CLOSED_PFMEA = {"controlled", "closed"}
APPROVED_PPAP = {"approved"}


def _dt(value):
    return value.isoformat() if value else None


def _in_area(value: str | None, manufacturing_area: str | None, allowed_area_codes: set[str] | None = None) -> bool:
    if manufacturing_area:
        return not value or value == manufacturing_area
    return not value or allowed_area_codes is None or value in allowed_area_codes


def _part_visible(part_number: str | None, visible_part_numbers: set[str] | None) -> bool:
    if not part_number or visible_part_numbers is None:
        return True
    return part_number in visible_part_numbers


def _evidence_visible(ids: Iterable[str] | None, visible_document_ids: set[str] | None) -> list[str]:
    values = list(ids or [])
    if visible_document_ids is None:
        return values
    return [x for x in values if x in visible_document_ids]


def internal_pfmea_risk_band(item: PFMEAItem) -> str:
    """Internal advisory band only. This is not an AIAG/VDA Action Priority calculation."""
    s, o, d = int(item.severity or 1), int(item.occurrence or 1), int(item.detection or 1)
    if s >= 9 or (s >= 8 and o >= 5):
        return "critical"
    score = s * o * d
    if score >= 180 or (s >= 7 and o >= 5):
        return "high"
    if score >= 80:
        return "medium"
    return "low"


def serialize_apqp(x: APQPDeliverable, visible_document_ids: set[str] | None = None) -> dict:
    return {"id": x.id, "project_code": x.project_code, "manufacturing_area": x.manufacturing_area, "code": x.code,
            "phase": x.phase, "title": x.title, "owner": x.owner, "due_at": _dt(x.due_at), "status": x.status,
            "linked_part_numbers": x.linked_part_numbers or [], "evidence_document_ids": _evidence_visible(x.evidence_document_ids, visible_document_ids),
            "notes": x.notes, "metadata": x.metadata_json or {}, "created_at": _dt(x.created_at), "updated_at": _dt(x.updated_at)}


def serialize_characteristic(x: SpecialCharacteristic, visible_document_ids: set[str] | None = None) -> dict:
    source = x.source_document_id if visible_document_ids is None or x.source_document_id in visible_document_ids else None
    return {"id": x.id, "project_code": x.project_code, "manufacturing_area": x.manufacturing_area, "part_number": x.part_number,
            "revision": x.revision, "code": x.code, "category": x.category, "symbol": x.symbol, "description": x.description,
            "specification": x.specification, "unit": x.unit, "source_document_id": source, "source_reference": x.source_reference_json or {},
            "owner": x.owner, "status": x.status, "metadata": x.metadata_json or {}, "created_at": _dt(x.created_at), "updated_at": _dt(x.updated_at)}


def serialize_pfmea(x: PFMEAItem, visible_document_ids: set[str] | None = None) -> dict:
    return {"id": x.id, "project_code": x.project_code, "manufacturing_area": x.manufacturing_area, "part_number": x.part_number,
            "process_step": x.process_step, "process_operation_id": x.process_operation_id, "function": x.function, "failure_mode": x.failure_mode, "effect": x.effect, "cause": x.cause,
            "prevention_control": x.prevention_control, "detection_control": x.detection_control, "severity": x.severity,
            "occurrence": x.occurrence, "detection": x.detection, "action_priority": x.action_priority,
            "internal_risk_band": internal_pfmea_risk_band(x), "recommended_action": x.recommended_action, "action_owner": x.action_owner,
            "due_at": _dt(x.due_at), "status": x.status, "special_characteristic_ids": x.special_characteristic_ids or [],
            "evidence_document_ids": _evidence_visible(x.evidence_document_ids, visible_document_ids), "metadata": x.metadata_json or {},
            "created_at": _dt(x.created_at), "updated_at": _dt(x.updated_at)}


def serialize_control_plan(x: ControlPlanItem, visible_document_ids: set[str] | None = None) -> dict:
    return {"id": x.id, "project_code": x.project_code, "manufacturing_area": x.manufacturing_area, "part_number": x.part_number,
            "process_step": x.process_step, "process_operation_id": x.process_operation_id, "characteristic_id": x.characteristic_id, "characteristic": x.characteristic,
            "specification": x.specification, "measurement_method": x.measurement_method, "sample_size": x.sample_size,
            "frequency": x.frequency, "reaction_plan": x.reaction_plan, "control_phase": x.control_phase, "owner": x.owner,
            "status": x.status, "evidence_document_ids": _evidence_visible(x.evidence_document_ids, visible_document_ids),
            "metadata": x.metadata_json or {}, "created_at": _dt(x.created_at), "updated_at": _dt(x.updated_at)}


def serialize_ppap(x: PPAPSubmission, visible_document_ids: set[str] | None = None) -> dict:
    return {"id": x.id, "project_code": x.project_code, "manufacturing_area": x.manufacturing_area, "part_number": x.part_number,
            "revision": x.revision, "supplier_code": x.supplier_code, "supplier_name": x.supplier_name, "customer": x.customer,
            "submission_level": x.submission_level, "status": x.status, "due_at": _dt(x.due_at), "submitted_at": _dt(x.submitted_at),
            "approved_at": _dt(x.approved_at), "element_status": x.element_status_json or {},
            "evidence_document_ids": _evidence_visible(x.evidence_document_ids, visible_document_ids), "notes": x.notes,
            "metadata": x.metadata_json or {}, "created_by": x.created_by, "created_at": _dt(x.created_at), "updated_at": _dt(x.updated_at)}


def serialize_8d(x: Problem8D, visible_document_ids: set[str] | None = None) -> dict:
    return {"id": x.id, "project_code": x.project_code, "manufacturing_area": x.manufacturing_area, "part_number": x.part_number,
            "complaint_reference": x.complaint_reference, "title": x.title, "severity": x.severity, "status": x.status,
            "owner": x.owner, "team": x.team_json or [], "disciplines": x.disciplines_json or {}, "linked_change_id": x.linked_change_id,
            "evidence_document_ids": _evidence_visible(x.evidence_document_ids, visible_document_ids), "metadata": x.metadata_json or {},
            "created_by": x.created_by, "created_at": _dt(x.created_at), "updated_at": _dt(x.updated_at)}


def quality_workspace(db: Session, project_code: str, visible_document_ids: set[str], visible_part_numbers: set[str], manufacturing_area: str | None = None, allowed_area_codes: set[str] | None = None) -> dict:
    apqp = [x for x in db.scalars(select(APQPDeliverable).where(APQPDeliverable.project_code == project_code).order_by(APQPDeliverable.due_at, APQPDeliverable.code)).all()
            if _in_area(x.manufacturing_area, manufacturing_area, allowed_area_codes)]
    chars = [x for x in db.scalars(select(SpecialCharacteristic).where(SpecialCharacteristic.project_code == project_code).order_by(SpecialCharacteristic.code)).all()
             if _in_area(x.manufacturing_area, manufacturing_area, allowed_area_codes) and _part_visible(x.part_number, visible_part_numbers)
             and (not x.source_document_id or x.source_document_id in visible_document_ids)]
    pfmea = [x for x in db.scalars(select(PFMEAItem).where(PFMEAItem.project_code == project_code).order_by(PFMEAItem.updated_at.desc())).all()
             if _in_area(x.manufacturing_area, manufacturing_area, allowed_area_codes) and _part_visible(x.part_number, visible_part_numbers)]
    control = [x for x in db.scalars(select(ControlPlanItem).where(ControlPlanItem.project_code == project_code).order_by(ControlPlanItem.updated_at.desc())).all()
               if _in_area(x.manufacturing_area, manufacturing_area, allowed_area_codes) and _part_visible(x.part_number, visible_part_numbers)]
    ppap = [x for x in db.scalars(select(PPAPSubmission).where(PPAPSubmission.project_code == project_code).order_by(PPAPSubmission.updated_at.desc())).all()
            if _in_area(x.manufacturing_area, manufacturing_area, allowed_area_codes) and _part_visible(x.part_number, visible_part_numbers)]
    problems = [x for x in db.scalars(select(Problem8D).where(Problem8D.project_code == project_code).order_by(Problem8D.updated_at.desc())).all()
                if _in_area(x.manufacturing_area, manufacturing_area, allowed_area_codes) and _part_visible(x.part_number, visible_part_numbers)]

    visible_characteristic_ids = {x.id for x in chars}

    pfmea_by_char: dict[str, list[PFMEAItem]] = {}
    for item in pfmea:
        for cid in item.special_characteristic_ids or []:
            pfmea_by_char.setdefault(cid, []).append(item)
    cp_by_char: dict[str, list[ControlPlanItem]] = {}
    for item in control:
        if item.characteristic_id:
            cp_by_char.setdefault(item.characteristic_id, []).append(item)

    gaps: list[dict] = []
    for ch in chars:
        if not pfmea_by_char.get(ch.id):
            gaps.append({"type": "characteristic_pfmea", "severity": "critical" if ch.category in {"safety", "regulatory"} else "warning", "id": ch.id,
                         "part_number": ch.part_number, "title": f"{ch.code}: критическая характеристика не связана с PFMEA"})
        if not any(cp.status in ACTIVE_CP for cp in cp_by_char.get(ch.id, [])):
            gaps.append({"type": "characteristic_control_plan", "severity": "critical" if ch.category in {"safety", "regulatory"} else "warning", "id": ch.id,
                         "part_number": ch.part_number, "title": f"{ch.code}: нет активного Control Plan"})

    for item in pfmea:
        band = internal_pfmea_risk_band(item)
        if band in {"critical", "high"} and item.status not in CLOSED_PFMEA:
            gaps.append({"type": "pfmea", "severity": "critical" if band == "critical" else "warning", "id": item.id,
                         "part_number": item.part_number, "title": f"PFMEA: высокий незакрытый риск — {item.failure_mode[:120]}"})

    for item in control:
        if item.status in ACTIVE_CP and not (item.reaction_plan or "").strip():
            gaps.append({"type": "control_plan", "severity": "warning", "id": item.id, "part_number": item.part_number,
                         "title": f"Control Plan: нет reaction plan — {item.characteristic[:120]}"})

    now = datetime.now(timezone.utc)
    overdue_apqp = [x for x in apqp if x.due_at and x.due_at.replace(tzinfo=x.due_at.tzinfo or timezone.utc) < now and x.status not in TERMINAL_APQP]
    for item in overdue_apqp:
        gaps.append({"type": "apqp", "severity": "warning", "id": item.id, "title": f"APQP: просрочено — {item.title}"})

    rejected_ppap = [x for x in ppap if x.status == "rejected"]
    for item in rejected_ppap:
        gaps.append({"type": "ppap", "severity": "critical", "id": item.id, "part_number": item.part_number, "title": "PPAP отклонён"})

    open_severe_8d = [x for x in problems if x.status not in TERMINAL_8D and x.severity in {"high", "critical"}]
    for item in open_severe_8d:
        gaps.append({"type": "8d", "severity": "critical" if item.severity == "critical" else "warning", "id": item.id,
                     "part_number": item.part_number, "title": f"Открытый 8D: {item.title}"})
    for item in problems:
        d7 = (item.disciplines_json or {}).get("d7")
        if item.status in {"verification", "closed"} and not item.linked_change_id and not d7:
            gaps.append({"type": "8d_prevention", "severity": "warning", "id": item.id, "part_number": item.part_number,
                         "title": f"8D: не зафиксировано предотвращение повторения / связь с ECR-ECO — {item.title}"})

    apqp_score = 100.0 if not apqp else 100.0 * sum(x.status in TERMINAL_APQP for x in apqp) / len(apqp)
    char_coverage_den = max(len(chars) * 2, 1)
    char_coverage_num = sum(bool(pfmea_by_char.get(ch.id)) for ch in chars) + sum(any(cp.status in ACTIVE_CP for cp in cp_by_char.get(ch.id, [])) for ch in chars)
    core_tools_score = 100.0 if not chars else 100.0 * char_coverage_num / char_coverage_den
    ppap_score = 100.0 if not ppap else 100.0 * sum(x.status in APPROVED_PPAP for x in ppap) / len(ppap)
    problem_score = max(0.0, 100.0 - 25.0 * sum(x.severity == "critical" for x in open_severe_8d) - 10.0 * sum(x.severity == "high" for x in open_severe_8d))
    score = round(apqp_score * 0.25 + core_tools_score * 0.45 + ppap_score * 0.20 + problem_score * 0.10, 1)

    return {
        "score": score,
        "advisory_only": True,
        "standards_profile": {
            "apqp": "AIAG APQP 3rd Edition aligned workflow",
            "control_plan": "AIAG Control Plan 1st Edition aligned workflow",
            "pfmea": "AIAG/VDA FMEA compatible data model; Action Priority is user/customer configured",
            "ppap": "PPAP evidence/submission workflow",
            "problem_solving": "8D / effective problem solving workflow",
            "copyright_note": "No proprietary AIAG/VDA forms or copyrighted tables are embedded; customer-specific requirements must be configured by the organization.",
        },
        "gates": {"apqp": round(apqp_score, 1), "core_tools": round(core_tools_score, 1), "ppap": round(ppap_score, 1), "problem_solving": round(problem_score, 1)},
        "counts": {"apqp": len(apqp), "special_characteristics": len(chars), "pfmea": len(pfmea), "control_plan": len(control), "ppap": len(ppap), "problems_8d": len(problems), "gaps": len(gaps)},
        "gaps": gaps[:100],
        "apqp": [serialize_apqp(x, visible_document_ids) for x in apqp],
        "special_characteristics": [serialize_characteristic(x, visible_document_ids) for x in chars],
        "pfmea": [dict(serialize_pfmea(x, visible_document_ids), special_characteristic_ids=[cid for cid in (x.special_characteristic_ids or []) if cid in visible_characteristic_ids]) for x in pfmea],
        "control_plan": [dict(serialize_control_plan(x, visible_document_ids), characteristic_id=x.characteristic_id if x.characteristic_id in visible_characteristic_ids else None) for x in control],
        "ppap": [serialize_ppap(x, visible_document_ids) for x in ppap],
        "problems_8d": [serialize_8d(x, visible_document_ids) for x in problems],
    }
