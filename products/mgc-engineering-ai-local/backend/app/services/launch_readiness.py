from __future__ import annotations

from datetime import datetime, timezone
from typing import Iterable

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import (
    ChangeRequest,
    LaunchReadinessItem,
    LaunchTrial,
    ManufacturingLine,
    PPAPSubmission,
    Problem8D,
)
from app.services.process_digital_thread import process_digital_thread
from app.services.quality_core_tools import quality_workspace


READY_ITEM = {"ready", "waived"}
TERMINAL_TRIAL = {"passed", "failed", "cancelled"}
TERMINAL_CHANGE = {"implemented", "rejected", "cancelled"}
TERMINAL_8D = {"closed", "cancelled"}

CATEGORY_LABELS = {
    "tooling": "Оснастка",
    "equipment": "Оборудование",
    "supplier": "Поставщики",
    "capacity": "Мощность / Run@Rate",
    "pilot_build": "Пилотная сборка",
    "validation": "DV / PV",
    "packaging": "Упаковка",
    "logistics": "Логистика",
    "staffing": "Персонал",
    "training": "Обучение",
    "safe_launch": "Safe Launch",
    "other": "Другое",
}

AREA_LAUNCH_HINTS = {
    "body_welding": [
        "Оснастка и геометрические фикстуры готовы и проверены",
        "Сварочное оборудование, роботы и программы готовы к серии",
        "Run@Rate подтверждает требуемый такт и качество сварных соединений",
        "Safe Launch / усиленный контроль критических точек определён",
    ],
    "paint": [
        "Окрасочное оборудование и печи готовы к серийному режиму",
        "Технологические окна и параметры подтверждены пилотными кузовами",
        "Материалы, химия, masking и logistics supply подтверждены",
        "План Safe Launch и критерии окончания усиленного контроля утверждены",
    ],
    "assembly": [
        "Оснастка, torque tools и средства измерения готовы и откалиброваны",
        "Пилотная сборка подтверждает последовательность и доступ инструмента",
        "Run@Rate подтверждает требуемый такт линии",
        "Упаковка, kitting, sequencing и material flow готовы к SOP",
    ],
    "components": [
        "Критические поставщики и PPAP подтверждены",
        "Производственная мощность подтверждена на серийном процессе",
        "Упаковка и traceability согласованы",
        "Открытые supplier 8D имеют containment/corrective action",
    ],
    "logistics": [
        "Упаковка и маркировка утверждены",
        "Маршруты, supermarket/kitting/sequencing готовы",
        "Пиковая пропускная способность material flow проверена",
        "Поставщики и транспортные окна готовы к SOP",
    ],
    "quality": [
        "PPAP по применимым деталям одобрен",
        "DV/PV и pilot build evidence доступны",
        "Safe Launch и reaction plan согласованы",
        "High/Critical 8D закрыты или имеют утверждённый containment",
    ],
}


def _dt(value):
    return value.isoformat() if value else None


def _in_area(value: str | None, manufacturing_area: str | None, allowed_area_codes: set[str] | None) -> bool:
    if manufacturing_area:
        return not value or value == manufacturing_area
    return not value or allowed_area_codes is None or value in allowed_area_codes


def _part_visible(value: str | None, visible_part_numbers: set[str] | None) -> bool:
    return not value or visible_part_numbers is None or value in visible_part_numbers


def _visible_evidence(ids: Iterable[str] | None, visible_document_ids: set[str] | None) -> list[str]:
    values = list(ids or [])
    if visible_document_ids is None:
        return values
    return [x for x in values if x in visible_document_ids]


def serialize_launch_item(x: LaunchReadinessItem, visible_document_ids: set[str] | None = None) -> dict:
    return {
        "id": x.id, "project_code": x.project_code, "manufacturing_area": x.manufacturing_area,
        "line_id": x.line_id, "part_number": x.part_number, "code": x.code, "category": x.category,
        "category_label": CATEGORY_LABELS.get(x.category, x.category), "title": x.title, "required": x.required,
        "status": x.status, "owner": x.owner, "due_at": _dt(x.due_at), "supplier_code": x.supplier_code,
        "supplier_name": x.supplier_name, "criteria": x.criteria_json or {}, "result": x.result_json or {},
        "evidence_document_ids": _visible_evidence(x.evidence_document_ids, visible_document_ids), "notes": x.notes,
        "created_by": x.created_by, "metadata": x.metadata_json or {}, "created_at": _dt(x.created_at), "updated_at": _dt(x.updated_at),
    }


def serialize_launch_trial(x: LaunchTrial, visible_document_ids: set[str] | None = None) -> dict:
    attainment = None
    if x.target_rate_per_hour and x.actual_rate_per_hour is not None and x.target_rate_per_hour > 0:
        attainment = round(100.0 * x.actual_rate_per_hour / x.target_rate_per_hour, 1)
    yield_pct = None
    if x.produced_quantity and x.good_quantity is not None and x.produced_quantity > 0:
        yield_pct = round(100.0 * x.good_quantity / x.produced_quantity, 1)
    return {
        "id": x.id, "project_code": x.project_code, "manufacturing_area": x.manufacturing_area, "line_id": x.line_id,
        "part_number": x.part_number, "code": x.code, "trial_type": x.trial_type, "title": x.title, "status": x.status,
        "owner": x.owner, "planned_at": _dt(x.planned_at), "completed_at": _dt(x.completed_at),
        "planned_quantity": x.planned_quantity, "produced_quantity": x.produced_quantity, "good_quantity": x.good_quantity,
        "target_rate_per_hour": x.target_rate_per_hour, "actual_rate_per_hour": x.actual_rate_per_hour,
        "duration_minutes": x.duration_minutes, "capacity_attainment_pct": attainment, "first_pass_yield_pct": yield_pct,
        "result": x.result_json or {}, "evidence_document_ids": _visible_evidence(x.evidence_document_ids, visible_document_ids),
        "notes": x.notes, "created_by": x.created_by, "metadata": x.metadata_json or {},
        "created_at": _dt(x.created_at), "updated_at": _dt(x.updated_at),
    }


def _score_items(items: list[LaunchReadinessItem]) -> float | None:
    relevant = [x for x in items if x.required and x.status != "cancelled"]
    if not relevant:
        return None
    ready = sum(x.status in READY_ITEM for x in relevant)
    in_progress = sum(x.status == "in_progress" for x in relevant)
    return round(100.0 * (ready + 0.5 * in_progress) / len(relevant), 1)


def _score_trials(trials: list[LaunchTrial]) -> float | None:
    relevant = [x for x in trials if x.status != "cancelled"]
    if not relevant:
        return None
    points = 0.0
    for x in relevant:
        if x.status == "passed":
            points += 1.0
        elif x.status == "in_progress":
            points += 0.5
    return round(100.0 * points / len(relevant), 1)


def launch_readiness(
    db: Session,
    project_code: str,
    visible_document_ids: set[str],
    visible_part_numbers: set[str],
    manufacturing_area: str | None = None,
    allowed_area_codes: set[str] | None = None,
    *,
    quality: dict | None = None,
    process: dict | None = None,
) -> dict:
    lines = db.scalars(select(ManufacturingLine).where(ManufacturingLine.project_code == project_code)).all()
    visible_lines = [x for x in lines if _in_area(x.manufacturing_area, manufacturing_area, allowed_area_codes)]
    visible_line_ids = {x.id for x in visible_lines}

    items = [x for x in db.scalars(select(LaunchReadinessItem).where(LaunchReadinessItem.project_code == project_code).order_by(LaunchReadinessItem.category, LaunchReadinessItem.code)).all()
             if _in_area(x.manufacturing_area, manufacturing_area, allowed_area_codes)
             and _part_visible(x.part_number, visible_part_numbers)
             and (not x.line_id or x.line_id in visible_line_ids)]
    trials = [x for x in db.scalars(select(LaunchTrial).where(LaunchTrial.project_code == project_code).order_by(LaunchTrial.planned_at.desc(), LaunchTrial.code)).all()
              if _in_area(x.manufacturing_area, manufacturing_area, allowed_area_codes)
              and _part_visible(x.part_number, visible_part_numbers)
              and (not x.line_id or x.line_id in visible_line_ids)]

    configured = bool(items or trials)
    quality = quality if quality is not None else quality_workspace(db, project_code, visible_document_ids, visible_part_numbers, manufacturing_area, allowed_area_codes)
    process = process if process is not None else process_digital_thread(db, project_code, visible_document_ids, visible_part_numbers, manufacturing_area, allowed_area_codes)

    grouped: dict[str, list[LaunchReadinessItem]] = {}
    for item in items:
        grouped.setdefault(item.category, []).append(item)

    tooling_items = grouped.get("tooling", []) + grouped.get("equipment", [])
    supplier_items = grouped.get("supplier", [])
    logistics_items = grouped.get("packaging", []) + grouped.get("logistics", [])
    people_items = grouped.get("staffing", []) + grouped.get("training", [])
    safe_launch_items = grouped.get("safe_launch", [])
    capacity_items = grouped.get("capacity", [])
    pilot_items = grouped.get("pilot_build", []) + grouped.get("validation", [])

    run_trials = [x for x in trials if x.trial_type == "run_at_rate"]
    validation_trials = [x for x in trials if x.trial_type in {"pilot_build", "dv", "pv"}]
    safe_launch_trials = [x for x in trials if x.trial_type == "safe_launch"]

    tooling_score = _score_items(tooling_items)
    if tooling_score is None and process.get("configured") and process.get("counts", {}).get("assets", 0):
        asset_gaps = [g for g in process.get("gaps", []) if g.get("type") in {"asset_calibration", "asset_maintenance"}]
        tooling_score = max(0.0, 100.0 - 25.0 * sum(g.get("severity") == "critical" for g in asset_gaps) - 8.0 * sum(g.get("severity") != "critical" for g in asset_gaps))

    supplier_score = _score_items(supplier_items)
    ppap = quality.get("ppap", [])
    if ppap:
        approved = sum(x.get("status") == "approved" for x in ppap)
        ppap_score = round(100.0 * approved / len(ppap), 1)
        supplier_score = ppap_score if supplier_score is None else round((supplier_score + ppap_score) / 2.0, 1)

    capacity_score = _score_trials(run_trials)
    measurable_capacity = [x for x in run_trials if x.target_rate_per_hour and x.target_rate_per_hour > 0 and x.actual_rate_per_hour is not None]
    if measurable_capacity:
        metric_score = round(sum(min(100.0, 100.0 * float(x.actual_rate_per_hour) / float(x.target_rate_per_hour)) for x in measurable_capacity) / len(measurable_capacity), 1)
        capacity_score = metric_score if capacity_score is None else min(capacity_score, metric_score)
    item_capacity_score = _score_items(capacity_items)
    if item_capacity_score is not None:
        capacity_score = item_capacity_score if capacity_score is None else round((capacity_score + item_capacity_score) / 2.0, 1)

    pilot_score = _score_trials(validation_trials)
    item_pilot_score = _score_items(pilot_items)
    if item_pilot_score is not None:
        pilot_score = item_pilot_score if pilot_score is None else round((pilot_score + item_pilot_score) / 2.0, 1)

    logistics_score = _score_items(logistics_items)
    people_score = _score_items(people_items)

    safe_launch_score = _score_trials(safe_launch_trials)
    item_safe_score = _score_items(safe_launch_items)
    if item_safe_score is not None:
        safe_launch_score = item_safe_score if safe_launch_score is None else round((safe_launch_score + item_safe_score) / 2.0, 1)
    safe_cp = [x for x in quality.get("control_plan", []) if x.get("control_phase") == "safe_launch"]
    if safe_cp:
        cp_ready = sum(x.get("status") in {"active", "verified"} and bool((x.get("reaction_plan") or "").strip()) for x in safe_cp)
        cp_score = round(100.0 * cp_ready / len(safe_cp), 1)
        safe_launch_score = cp_score if safe_launch_score is None else round((safe_launch_score + cp_score) / 2.0, 1)

    changes = [x for x in db.scalars(select(ChangeRequest)).all() if x.part_number in visible_part_numbers and x.status not in TERMINAL_CHANGE]
    problems = [x for x in db.scalars(select(Problem8D).where(Problem8D.project_code == project_code)).all()
                if _in_area(x.manufacturing_area, manufacturing_area, allowed_area_codes)
                and _part_visible(x.part_number, visible_part_numbers)
                and x.status not in TERMINAL_8D]
    high_changes = [x for x in changes if x.priority in {"high", "urgent"} or x.risk_level in {"high", "critical"}]
    high_8d = [x for x in problems if x.severity in {"high", "critical"}]
    risk_closure_score = max(0.0, 100.0 - 15.0 * len(high_changes) - 20.0 * len(high_8d))

    gates = {
        "tooling_equipment": round(tooling_score, 1) if tooling_score is not None else None,
        "supplier_ppap": round(supplier_score, 1) if supplier_score is not None else None,
        "capacity": round(capacity_score, 1) if capacity_score is not None else None,
        "pilot_validation": round(pilot_score, 1) if pilot_score is not None else None,
        "logistics_packaging": round(logistics_score, 1) if logistics_score is not None else None,
        "people_training": round(people_score, 1) if people_score is not None else None,
        "safe_launch": round(safe_launch_score, 1) if safe_launch_score is not None else None,
        "risk_closure": round(risk_closure_score, 1) if configured else None,
    }

    scored = [float(v) for k, v in gates.items() if v is not None and (configured or k != "risk_closure")]
    score = round(sum(scored) / len(scored), 1) if configured and scored else 0.0

    gaps: list[dict] = []
    now = datetime.now(timezone.utc)
    for item in items:
        if item.required and item.status in {"blocked", "failed"}:
            gaps.append({"type": "launch_check", "severity": "critical", "id": item.id, "part_number": item.part_number,
                         "title": f"{item.code}: {item.title} — {item.status}"})
        elif item.required and item.status not in READY_ITEM:
            severity = "warning"
            if item.due_at and item.due_at.replace(tzinfo=item.due_at.tzinfo or timezone.utc) < now:
                severity = "critical"
            gaps.append({"type": "launch_check", "severity": severity, "id": item.id, "part_number": item.part_number,
                         "title": f"{item.code}: {item.title} не подтверждено"})

    for trial in trials:
        if trial.status == "failed":
            gaps.append({"type": "launch_trial", "severity": "critical", "id": trial.id, "part_number": trial.part_number,
                         "title": f"{trial.code}: {trial.title} — результат FAILED"})
        if trial.trial_type == "run_at_rate" and trial.status == "passed" and trial.target_rate_per_hour and trial.actual_rate_per_hour is not None and trial.actual_rate_per_hour < trial.target_rate_per_hour:
            gaps.append({"type": "capacity_mismatch", "severity": "critical", "id": trial.id, "part_number": trial.part_number,
                         "title": f"{trial.code}: фактическая производительность ниже целевой"})
        if trial.produced_quantity and trial.good_quantity is not None and trial.good_quantity > trial.produced_quantity:
            gaps.append({"type": "trial_data", "severity": "critical", "id": trial.id, "title": f"{trial.code}: good quantity больше produced quantity"})

    for item in ppap:
        if item.get("status") == "rejected":
            gaps.append({"type": "ppap", "severity": "critical", "id": item.get("id"), "part_number": item.get("part_number"),
                         "title": f"PPAP {item.get('part_number')}: отклонён"})
    for x in high_8d:
        gaps.append({"type": "8d", "severity": "critical" if x.severity == "critical" else "warning", "id": x.id, "part_number": x.part_number,
                     "title": f"8D: {x.title} — не закрыт"})
    for x in high_changes:
        gaps.append({"type": "change", "severity": "critical" if x.risk_level == "critical" or x.priority == "urgent" else "warning", "id": x.id, "part_number": x.part_number,
                     "title": f"{x.eco_code or x.code}: high-risk изменение не завершено"})

    if configured and any(x.status == "passed" for x in run_trials):
        for x in run_trials:
            if x.status == "passed" and not _visible_evidence(x.evidence_document_ids, visible_document_ids):
                gaps.append({"type": "capacity_evidence", "severity": "warning", "id": x.id,
                             "title": f"{x.code}: Run@Rate отмечен как passed без доступного evidence"})

    status = "not_configured"
    if configured:
        if any(g["severity"] == "critical" for g in gaps):
            status = "blocked"
        elif score >= 90 and not gaps:
            status = "candidate"
        else:
            status = "needs_review"

    return {
        "configured": configured,
        "score": score,
        "status": status,
        "advisory_only": True,
        "human_sop_approval_required": True,
        "not_mes_or_scada": True,
        "manufacturing_area": manufacturing_area,
        "gates": gates,
        "counts": {
            "checks": len(items), "trials": len(trials), "open_high_8d": len(high_8d), "open_high_changes": len(high_changes),
            "run_at_rate": len(run_trials), "pilot_validation": len(validation_trials), "gaps": len(gaps),
        },
        "gaps": gaps[:100],
        "checks": [serialize_launch_item(x, visible_document_ids) for x in items[:200]],
        "trials": [serialize_launch_trial(x, visible_document_ids) for x in trials[:200]],
        "recommended_checks": AREA_LAUNCH_HINTS.get(manufacturing_area or "", [
            "Оснастка и оборудование готовы к SOP",
            "Производственная мощность подтверждена",
            "PPAP / supplier readiness подтверждены",
            "Pilot/DV/PV evidence завершены",
            "Упаковка и логистика готовы",
            "Safe Launch и критерии выхода из него определены",
        ]),
    }
