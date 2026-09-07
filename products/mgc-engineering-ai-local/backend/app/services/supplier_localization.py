from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import (
    EvidencePack,
    IncomingQualityRecord,
    LaunchReadinessItem,
    LaunchTrial,
    LocalizationItem,
    PPAPSubmission,
    Problem8D,
)

TERMINAL_8D = {"closed", "cancelled"}
READY_TOOLING = {"ready", "waived", "not_required"}
READY_CAPACITY = {"confirmed", "waived"}
ACTIVE_LOCALIZATION = {"candidate", "rfq", "nominated", "tooling", "validation", "approved", "sop", "hold"}


def _dt(value):
    return value.isoformat() if value else None


def _in_area(value: str | None, manufacturing_area: str | None, allowed_area_codes: set[str] | None) -> bool:
    if manufacturing_area:
        return not value or value == manufacturing_area
    return not value or allowed_area_codes is None or value in allowed_area_codes


def _visible_evidence(ids: list[str] | None, visible_document_ids: set[str] | None) -> list[str]:
    values = list(ids or [])
    if visible_document_ids is None:
        return values
    return [x for x in values if x in visible_document_ids]


def serialize_localization_item(x: LocalizationItem, visible_document_ids: set[str] | None = None) -> dict:
    return {
        "id": x.id,
        "project_code": x.project_code,
        "manufacturing_area": x.manufacturing_area,
        "part_number": x.part_number,
        "revision": x.revision,
        "supplier_code": x.supplier_code,
        "supplier_name": x.supplier_name,
        "source_country": x.source_country,
        "local_plant": x.local_plant,
        "status": x.status,
        "localization_percent": x.localization_percent,
        "target_localization_percent": x.target_localization_percent,
        "technical_package_status": x.technical_package_status,
        "rfq_status": x.rfq_status,
        "nomination_status": x.nomination_status,
        "tooling_status": x.tooling_status,
        "capacity_status": x.capacity_status,
        "owner": x.owner,
        "planned_sop_at": _dt(x.planned_sop_at),
        "evidence_document_ids": _visible_evidence(x.evidence_document_ids, visible_document_ids),
        "notes": x.notes,
        "created_by": x.created_by,
        "metadata": x.metadata_json or {},
        "created_at": _dt(x.created_at),
        "updated_at": _dt(x.updated_at),
    }


def serialize_incoming_quality(x: IncomingQualityRecord, visible_document_ids: set[str] | None = None) -> dict:
    inspected = max(int(x.inspected_quantity or 0), 0)
    rejected = max(int(x.rejected_quantity or 0), 0)
    defects = max(int(x.defect_quantity or 0), 0)
    reject_rate = round(100.0 * rejected / inspected, 3) if inspected else None
    defect_rate = round(100.0 * defects / inspected, 3) if inspected else None
    return {
        "id": x.id,
        "project_code": x.project_code,
        "manufacturing_area": x.manufacturing_area,
        "code": x.code,
        "supplier_code": x.supplier_code,
        "supplier_name": x.supplier_name,
        "part_number": x.part_number,
        "revision": x.revision,
        "lot_reference": x.lot_reference,
        "inspection_type": x.inspection_type,
        "inspected_quantity": inspected,
        "rejected_quantity": rejected,
        "defect_quantity": defects,
        "reject_rate_pct": reject_rate,
        "defect_rate_pct": defect_rate,
        "defect_code": x.defect_code,
        "severity": x.severity,
        "status": x.status,
        "acceptance_limit_pct": x.acceptance_limit_pct,
        "linked_8d_id": x.linked_8d_id,
        "evidence_document_ids": _visible_evidence(x.evidence_document_ids, visible_document_ids),
        "notes": x.notes,
        "occurred_at": _dt(x.occurred_at),
        "created_by": x.created_by,
        "metadata": x.metadata_json or {},
        "created_at": _dt(x.created_at),
        "updated_at": _dt(x.updated_at),
    }


def _avg(values: list[float | None]) -> float | None:
    vals = [float(x) for x in values if x is not None]
    return round(sum(vals) / len(vals), 1) if vals else None


def _status_score(value: str, mapping: dict[str, float]) -> float:
    return float(mapping.get(value, 0.0))


def _latest_ppap(rows: list[PPAPSubmission], item: LocalizationItem) -> PPAPSubmission | None:
    matches = [x for x in rows if x.part_number == item.part_number and (not x.supplier_code or x.supplier_code == item.supplier_code)]
    matches.sort(key=lambda x: x.updated_at or x.created_at, reverse=True)
    return matches[0] if matches else None


def _best_capacity_trial(rows: list[LaunchTrial], item: LocalizationItem) -> LaunchTrial | None:
    matches = [x for x in rows if x.part_number == item.part_number and x.trial_type == "run_at_rate" and x.status != "cancelled"]
    matches.sort(key=lambda x: x.updated_at or x.created_at, reverse=True)
    return matches[0] if matches else None


def _tooling_evidence(rows: list[LaunchReadinessItem], item: LocalizationItem) -> list[LaunchReadinessItem]:
    return [x for x in rows if x.part_number == item.part_number and x.category in {"tooling", "equipment"} and (not x.supplier_code or x.supplier_code == item.supplier_code)]


def supplier_localization_workspace(
    db: Session,
    project_code: str,
    visible_document_ids: set[str],
    visible_part_numbers: set[str],
    manufacturing_area: str | None = None,
    allowed_area_codes: set[str] | None = None,
) -> dict:
    items = [x for x in db.scalars(select(LocalizationItem).where(LocalizationItem.project_code == project_code).order_by(LocalizationItem.supplier_name, LocalizationItem.part_number)).all()
             if x.part_number in visible_part_numbers and _in_area(x.manufacturing_area, manufacturing_area, allowed_area_codes)]
    incoming = [x for x in db.scalars(select(IncomingQualityRecord).where(IncomingQualityRecord.project_code == project_code).order_by(IncomingQualityRecord.occurred_at.desc())).all()
                if x.part_number in visible_part_numbers and _in_area(x.manufacturing_area, manufacturing_area, allowed_area_codes)]
    ppap = [x for x in db.scalars(select(PPAPSubmission).where(PPAPSubmission.project_code == project_code)).all()
            if x.part_number in visible_part_numbers and _in_area(x.manufacturing_area, manufacturing_area, allowed_area_codes)]
    launch_trials = [x for x in db.scalars(select(LaunchTrial).where(LaunchTrial.project_code == project_code)).all()
                     if (not x.part_number or x.part_number in visible_part_numbers) and _in_area(x.manufacturing_area, manufacturing_area, allowed_area_codes)]
    launch_items = [x for x in db.scalars(select(LaunchReadinessItem).where(LaunchReadinessItem.project_code == project_code)).all()
                    if (not x.part_number or x.part_number in visible_part_numbers) and _in_area(x.manufacturing_area, manufacturing_area, allowed_area_codes)]
    problems = [x for x in db.scalars(select(Problem8D).where(Problem8D.project_code == project_code)).all()
                if (not x.part_number or x.part_number in visible_part_numbers) and _in_area(x.manufacturing_area, manufacturing_area, allowed_area_codes)]

    configured = bool(items or incoming)
    gaps: list[dict] = []
    enriched: list[dict] = []
    gate_values: dict[str, list[float]] = {k: [] for k in ["technical_package", "rfq", "nomination", "tooling", "capacity", "ppap", "incoming_quality", "risk_closure"]}

    for item in items:
        row = serialize_localization_item(item, visible_document_ids)
        item_incoming = [x for x in incoming if x.part_number == item.part_number and x.supplier_code == item.supplier_code and x.status != "cancelled"]
        latest_ppap = _latest_ppap(ppap, item)
        capacity = _best_capacity_trial(launch_trials, item)
        tooling = _tooling_evidence(launch_items, item)
        linked_8d_ids = {x.linked_8d_id for x in item_incoming if x.linked_8d_id}
        item_8d = [x for x in problems if x.id in linked_8d_ids]

        technical = _status_score(item.technical_package_status, {"missing": 0, "in_progress": 50, "ready": 100, "waived": 100})
        rfq = _status_score(item.rfq_status, {"planned": 0, "sent": 40, "received": 70, "complete": 100, "waived": 100})
        nomination = _status_score(item.nomination_status, {"planned": 20, "approved": 100, "rejected": 0, "waived": 100})

        tooling_score = _status_score(item.tooling_status, {"planned": 20, "in_progress": 55, "ready": 100, "waived": 100, "not_required": 100, "failed": 0})
        if tooling and all(x.status in {"ready", "waived"} for x in tooling):
            tooling_score = max(tooling_score, 100)

        capacity_score = _status_score(item.capacity_status, {"planned": 20, "in_progress": 55, "confirmed": 100, "waived": 100, "failed": 0})
        capacity_ok = False
        if capacity and capacity.status == "passed":
            capacity_ok = not (capacity.target_rate_per_hour and capacity.actual_rate_per_hour is not None and capacity.actual_rate_per_hour < capacity.target_rate_per_hour)
            if capacity_ok:
                capacity_score = max(capacity_score, 100)

        ppap_score = 0.0
        if latest_ppap:
            ppap_score = _status_score(latest_ppap.status, {"draft": 20, "preparing": 35, "submitted": 65, "approved": 100, "rejected": 0})

        iq_score = 100.0
        active_iq = [x for x in item_incoming if x.status not in {"resolved", "closed", "cancelled"}]
        for iq in active_iq:
            row_iq = serialize_incoming_quality(iq, visible_document_ids)
            rate = row_iq.get("defect_rate_pct")
            if iq.severity == "critical":
                iq_score -= 45
            elif iq.severity == "high":
                iq_score -= 25
            elif iq.severity == "medium":
                iq_score -= 10
            if rate is not None and iq.acceptance_limit_pct is not None and rate > iq.acceptance_limit_pct:
                iq_score -= 25
        iq_score = max(0.0, iq_score)

        risk_score = 100.0
        for problem in item_8d:
            if problem.status not in TERMINAL_8D:
                risk_score -= 40 if problem.severity in {"high", "critical"} else 15
        for iq in active_iq:
            if iq.severity in {"high", "critical"} and not iq.linked_8d_id:
                risk_score -= 35
        risk_score = max(0.0, risk_score)

        for key, value in {
            "technical_package": technical, "rfq": rfq, "nomination": nomination, "tooling": tooling_score,
            "capacity": capacity_score, "ppap": ppap_score, "incoming_quality": iq_score, "risk_closure": risk_score,
        }.items():
            gate_values[key].append(value)

        stage_requires_maturity = item.status in {"tooling", "validation", "approved", "sop"}
        release_stage = item.status in {"approved", "sop"}
        def add_gap(kind: str, severity: str, title: str):
            gaps.append({"type": kind, "severity": severity, "id": item.id, "part_number": item.part_number, "supplier_code": item.supplier_code, "title": title})

        if item.technical_package_status == "missing": add_gap("technical_package", "critical" if stage_requires_maturity else "warning", f"{item.part_number}: технический пакет поставщика не готов")
        if item.rfq_status not in {"complete", "waived"}: add_gap("rfq", "warning", f"{item.part_number}: RFQ / техническое согласование не завершено")
        if item.nomination_status == "rejected": add_gap("nomination", "critical", f"{item.part_number}: поставщик отклонён")
        elif stage_requires_maturity and item.nomination_status not in {"approved", "waived"}: add_gap("nomination", "critical", f"{item.part_number}: поставщик ещё не номинирован")
        if item.tooling_status == "failed": add_gap("tooling", "critical", f"{item.part_number}: проблема готовности оснастки")
        elif release_stage and tooling_score < 100: add_gap("tooling", "critical", f"{item.part_number}: оснастка/оборудование поставщика не подтверждены")
        if item.capacity_status == "failed": add_gap("capacity", "critical", f"{item.part_number}: производственная мощность поставщика не подтверждена")
        elif release_stage and capacity_score < 100: add_gap("capacity", "critical", f"{item.part_number}: нет подтверждённого capacity / Run@Rate")
        if latest_ppap and latest_ppap.status == "rejected": add_gap("ppap", "critical", f"{item.part_number}: PPAP поставщика отклонён")
        elif release_stage and ppap_score < 100: add_gap("ppap", "critical", f"{item.part_number}: PPAP поставщика не одобрен")
        for iq in active_iq:
            data = serialize_incoming_quality(iq, visible_document_ids)
            if iq.severity in {"high", "critical"}:
                sev = "critical" if iq.severity == "critical" else "warning"
                add_gap("incoming_quality", sev, f"{item.part_number}: открытая проблема входного качества {iq.code}")
            rate = data.get("defect_rate_pct")
            if rate is not None and iq.acceptance_limit_pct is not None and rate > iq.acceptance_limit_pct:
                add_gap("incoming_quality_limit", "critical", f"{item.part_number}: дефектность {rate}% выше лимита {iq.acceptance_limit_pct}%")
            if iq.severity in {"high", "critical"} and not iq.linked_8d_id:
                add_gap("supplier_8d_missing", "critical", f"{item.part_number}: high/critical supplier issue не связан с 8D")

        weighted = technical*0.15 + rfq*0.10 + nomination*0.10 + tooling_score*0.15 + capacity_score*0.15 + ppap_score*0.20 + iq_score*0.10 + risk_score*0.05
        row["supplier_readiness_score"] = round(weighted, 1)
        row["derived"] = {
            "ppap": {"id": latest_ppap.id, "status": latest_ppap.status} if latest_ppap else None,
            "run_at_rate": {"id": capacity.id, "status": capacity.status, "target_rate_per_hour": capacity.target_rate_per_hour, "actual_rate_per_hour": capacity.actual_rate_per_hour, "meets_target": capacity_ok} if capacity else None,
            "tooling_checks": [{"id": x.id, "status": x.status, "title": x.title} for x in tooling],
            "incoming_quality_count": len(item_incoming),
            "open_8d_count": sum(x.status not in TERMINAL_8D for x in item_8d),
        }
        enriched.append(row)

    gates = {k: _avg(v) for k, v in gate_values.items()}
    if items:
        score = round(sum((gates[k] or 0.0) * w for k, w in {
            "technical_package": .15, "rfq": .10, "nomination": .10, "tooling": .15,
            "capacity": .15, "ppap": .20, "incoming_quality": .10, "risk_closure": .05,
        }.items()), 1)
    else:
        score = 100.0 if not incoming else max(0.0, 100.0 - 20.0 * len([x for x in incoming if x.status not in {"resolved", "closed", "cancelled"}]))

    if any(g["severity"] == "critical" for g in gaps): status = "blocked"
    elif gaps or score < 85: status = "needs_review"
    else: status = "ready"

    localization_kpi = _avg([x.localization_percent for x in items])
    localization_target = _avg([x.target_localization_percent for x in items])
    return {
        "configured": configured,
        "score": score,
        "status": status,
        "advisory_only": True,
        "localization_kpi": localization_kpi,
        "localization_target": localization_target,
        "localization_kpi_is_readiness": False,
        "gates": gates,
        "counts": {
            "localization_items": len(items),
            "suppliers": len({x.supplier_code for x in items}),
            "incoming_quality": len(incoming),
            "open_incoming_quality": sum(x.status not in {"resolved", "closed", "cancelled"} for x in incoming),
        },
        "items": enriched,
        "incoming_quality": [serialize_incoming_quality(x, visible_document_ids) for x in incoming],
        "gaps": gaps,
    }


def create_localization_evidence_pack(
    db: Session,
    project_code: str,
    item: LocalizationItem,
    user: str,
    visible_document_ids: set[str],
    workspace: dict,
) -> EvidencePack:
    item_view = next((x for x in workspace.get("items", []) if x.get("id") == item.id), serialize_localization_item(item, visible_document_ids))
    related_iq = [x for x in workspace.get("incoming_quality", []) if x.get("part_number") == item.part_number and x.get("supplier_code") == item.supplier_code]
    manifest = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "project_code": project_code,
        "pack_type": "supplier_localization",
        "supplier": {"code": item.supplier_code, "name": item.supplier_name, "local_plant": item.local_plant, "source_country": item.source_country},
        "localization_item": item_view,
        "incoming_quality": related_iq,
        "readiness_snapshot": {"score": item_view.get("supplier_readiness_score"), "project_localization_score": workspace.get("score"), "gaps": [g for g in workspace.get("gaps", []) if g.get("id") == item.id or g.get("part_number") == item.part_number]},
        "integrity": {"visible_evidence_document_ids": _visible_evidence(item.evidence_document_ids, visible_document_ids), "snapshot_only": True},
        "governance": {"advisory_only": True, "human_supplier_approval_required": True},
    }
    pack = EvidencePack(pack_type="supplier_localization", part_number=item.part_number, revision=item.revision, project_code=project_code, manifest=manifest, created_by=user)
    db.add(pack); db.commit(); db.refresh(pack)
    return pack
