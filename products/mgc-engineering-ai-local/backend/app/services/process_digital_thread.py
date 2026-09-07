from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import (
    ControlPlanItem,
    ManufacturingLine,
    PFMEAItem,
    ProcessAsset,
    ProcessDefect,
    ProcessOperation,
    ProcessParameter,
    ProcessStation, WorkInstruction,
    SpecialCharacteristic,
)


TERMINAL_DEFECT = {"resolved", "closed", "cancelled"}
ACTIVE_PROCESS = {"active", "verified"}

AREA_OPERATION_HINTS: dict[str, list[str]] = {
    "stamping": ["Blanking", "Forming", "Trimming", "Piercing", "Dimensional inspection"],
    "body_welding": ["Spot welding", "MIG/MAG welding", "Adhesive", "Hemming", "Geometry check"],
    "paint": ["Pretreatment", "E-coat", "Sealer", "Primer", "Basecoat", "Clearcoat", "Oven"],
    "assembly": ["Fastening / torque", "Press fit", "Clipping", "Fluid fill", "Functional check", "End-of-line test"],
    "components": ["Incoming", "Machining / forming", "Sub-assembly", "Functional test", "Final inspection"],
    "logistics": ["Receiving", "Storage", "Kitting", "Sequencing", "Line feeding", "Packaging"],
    "quality": ["Incoming inspection", "In-process inspection", "Audit", "Containment", "Release"],
    "manufacturing_engineering": ["Process setup", "Tooling validation", "Run at rate", "Capability review"],
    "testing": ["Test preparation", "Test execution", "Data review", "Release decision"],
    "product_engineering": ["Prototype build", "Engineering check", "Validation support"],
}


def _dt(value):
    return value.isoformat() if value else None


def _visible_evidence(ids: list[str] | None, visible_document_ids: set[str]) -> list[str]:
    return [x for x in (ids or []) if x in visible_document_ids]


def serialize_line(x: ManufacturingLine) -> dict:
    return {"id": x.id, "project_code": x.project_code, "manufacturing_area": x.manufacturing_area, "code": x.code,
            "name": x.name, "plant": x.plant, "owner": x.owner, "status": x.status, "metadata": x.metadata_json or {},
            "created_at": _dt(x.created_at), "updated_at": _dt(x.updated_at)}


def serialize_station(x: ProcessStation) -> dict:
    return {"id": x.id, "row_version": x.row_version, "line_id": x.line_id, "code": x.code, "name": x.name, "sequence": x.sequence,
            "owner": x.owner, "operator_role": x.operator_role, "headcount": x.headcount,
            "work_content": x.work_content, "takt_time_sec": x.takt_time_sec,
            "status": x.status, "metadata": x.metadata_json or {}, "created_at": _dt(x.created_at), "updated_at": _dt(x.updated_at)}


def serialize_operation(x: ProcessOperation, visible_document_ids: set[str]) -> dict:
    return {"id": x.id, "station_id": x.station_id, "code": x.code, "name": x.name, "sequence": x.sequence,
            "operation_type": x.operation_type, "part_number": x.part_number, "cycle_time_sec": x.cycle_time_sec,
            "work_instruction_document_ids": _visible_evidence(x.work_instruction_document_ids, visible_document_ids),
            "owner": x.owner, "status": x.status, "metadata": x.metadata_json or {}, "created_at": _dt(x.created_at), "updated_at": _dt(x.updated_at)}


def serialize_asset(x: ProcessAsset) -> dict:
    return {"id": x.id, "operation_id": x.operation_id, "code": x.code, "name": x.name, "asset_type": x.asset_type,
            "asset_reference": x.asset_reference, "calibration_due_at": _dt(x.calibration_due_at), "maintenance_due_at": _dt(x.maintenance_due_at),
            "status": x.status, "metadata": x.metadata_json or {}, "created_at": _dt(x.created_at), "updated_at": _dt(x.updated_at)}


def serialize_parameter(x: ProcessParameter) -> dict:
    return {"id": x.id, "operation_id": x.operation_id, "code": x.code, "name": x.name, "target_value": x.target_value,
            "lower_spec_limit": x.lower_spec_limit, "upper_spec_limit": x.upper_spec_limit, "unit": x.unit,
            "special_characteristic_id": x.special_characteristic_id, "control_plan_item_id": x.control_plan_item_id,
            "measurement_method": x.measurement_method, "reaction_plan": x.reaction_plan, "status": x.status,
            "metadata": x.metadata_json or {}, "created_at": _dt(x.created_at), "updated_at": _dt(x.updated_at)}


def serialize_defect(x: ProcessDefect, visible_document_ids: set[str]) -> dict:
    return {"id": x.id, "project_code": x.project_code, "manufacturing_area": x.manufacturing_area, "line_id": x.line_id,
            "station_id": x.station_id, "operation_id": x.operation_id, "part_number": x.part_number, "defect_code": x.defect_code,
            "title": x.title, "severity": x.severity, "quantity": x.quantity, "status": x.status, "linked_8d_id": x.linked_8d_id,
            "evidence_document_ids": _visible_evidence(x.evidence_document_ids, visible_document_ids), "occurred_at": _dt(x.occurred_at),
            "created_by": x.created_by, "metadata": x.metadata_json or {}, "created_at": _dt(x.created_at), "updated_at": _dt(x.updated_at)}


def process_digital_thread(
    db: Session,
    project_code: str,
    visible_document_ids: set[str],
    visible_part_numbers: set[str],
    manufacturing_area: str | None = None,
    allowed_area_codes: set[str] | None = None,
) -> dict:
    lines = db.scalars(select(ManufacturingLine).where(ManufacturingLine.project_code == project_code).order_by(ManufacturingLine.code)).all()
    if manufacturing_area:
        lines = [x for x in lines if x.manufacturing_area == manufacturing_area]
    elif allowed_area_codes is not None:
        lines = [x for x in lines if x.manufacturing_area in allowed_area_codes]
    line_ids = {x.id for x in lines}

    stations = [x for x in db.scalars(select(ProcessStation).order_by(ProcessStation.sequence, ProcessStation.code)).all() if x.line_id in line_ids]
    station_ids = {x.id for x in stations}
    operations = [x for x in db.scalars(select(ProcessOperation).order_by(ProcessOperation.sequence, ProcessOperation.code)).all()
                  if x.station_id in station_ids and (not x.part_number or x.part_number in visible_part_numbers)]
    operation_ids = {x.id for x in operations}

    instructions = db.scalars(select(WorkInstruction).where(WorkInstruction.project_code == project_code).order_by(WorkInstruction.updated_at.desc())).all()
    instructions = [x for x in instructions
                    if (not manufacturing_area or x.manufacturing_area == manufacturing_area)
                    and (manufacturing_area is not None or allowed_area_codes is None or x.manufacturing_area in allowed_area_codes)
                    and (not x.source_document_id or x.source_document_id in visible_document_ids)
                    and ((x.operation_id and x.operation_id in operation_ids) or (x.station_id and x.station_id in station_ids))]
    instructions_by_op: dict[str, list[WorkInstruction]] = {}
    instructions_by_station: dict[str, list[WorkInstruction]] = {}
    for wi in instructions:
        if wi.operation_id:
            instructions_by_op.setdefault(wi.operation_id, []).append(wi)
        if wi.station_id:
            instructions_by_station.setdefault(wi.station_id, []).append(wi)

    assets = [x for x in db.scalars(select(ProcessAsset).order_by(ProcessAsset.code)).all() if x.operation_id in operation_ids]
    parameters = [x for x in db.scalars(select(ProcessParameter).order_by(ProcessParameter.code)).all() if x.operation_id in operation_ids]
    defects = [x for x in db.scalars(select(ProcessDefect).where(ProcessDefect.project_code == project_code).order_by(ProcessDefect.occurred_at.desc())).all()
               if (not manufacturing_area or not x.manufacturing_area or x.manufacturing_area == manufacturing_area)
               and (manufacturing_area is not None or allowed_area_codes is None or not x.manufacturing_area or x.manufacturing_area in allowed_area_codes)
               and (not x.part_number or x.part_number in visible_part_numbers)
               and (not x.operation_id or x.operation_id in operation_ids)]

    pfmea = [x for x in db.scalars(select(PFMEAItem).where(PFMEAItem.project_code == project_code)).all()
             if (not manufacturing_area or not x.manufacturing_area or x.manufacturing_area == manufacturing_area)
             and (manufacturing_area is not None or allowed_area_codes is None or not x.manufacturing_area or x.manufacturing_area in allowed_area_codes)
             and (not x.part_number or x.part_number in visible_part_numbers)]
    control = [x for x in db.scalars(select(ControlPlanItem).where(ControlPlanItem.project_code == project_code)).all()
               if (not manufacturing_area or not x.manufacturing_area or x.manufacturing_area == manufacturing_area)
               and (manufacturing_area is not None or allowed_area_codes is None or not x.manufacturing_area or x.manufacturing_area in allowed_area_codes)
               and (not x.part_number or x.part_number in visible_part_numbers)]
    chars = [x for x in db.scalars(select(SpecialCharacteristic).where(SpecialCharacteristic.project_code == project_code)).all()
             if (not manufacturing_area or not x.manufacturing_area or x.manufacturing_area == manufacturing_area)
             and (manufacturing_area is not None or allowed_area_codes is None or not x.manufacturing_area or x.manufacturing_area in allowed_area_codes)
             and (not x.part_number or x.part_number in visible_part_numbers)]

    pfmea_by_op: dict[str, list[PFMEAItem]] = {}
    cp_by_op: dict[str, list[ControlPlanItem]] = {}
    for x in pfmea:
        if x.process_operation_id in operation_ids:
            pfmea_by_op.setdefault(x.process_operation_id, []).append(x)
    for x in control:
        if x.process_operation_id in operation_ids:
            cp_by_op.setdefault(x.process_operation_id, []).append(x)
    char_ids = {x.id for x in chars}
    cp_ids = {x.id for x in control}

    gaps: list[dict] = []
    for op in operations:
        linked_wi = instructions_by_op.get(op.id, []) + instructions_by_station.get(op.station_id, [])
        if not _visible_evidence(op.work_instruction_document_ids, visible_document_ids) and not linked_wi:
            gaps.append({"type": "work_instruction", "severity": "warning", "id": op.id, "part_number": op.part_number,
                         "title": f"{op.code}: нет доступной рабочей инструкции"})
        elif linked_wi and not any(x.status == "approved" for x in linked_wi):
            gaps.append({"type": "work_instruction_approval", "severity": "warning", "id": op.id, "part_number": op.part_number,
                         "title": f"{op.code}: рабочая инструкция есть, но нет утверждённой версии"})
        if not pfmea_by_op.get(op.id):
            gaps.append({"type": "operation_pfmea", "severity": "warning", "id": op.id, "part_number": op.part_number,
                         "title": f"{op.code}: операция не связана с PFMEA"})
        if not cp_by_op.get(op.id):
            gaps.append({"type": "operation_control_plan", "severity": "warning", "id": op.id, "part_number": op.part_number,
                         "title": f"{op.code}: операция не связана с Control Plan"})

    for p in parameters:
        if p.special_characteristic_id and p.special_characteristic_id in char_ids and not p.control_plan_item_id:
            gaps.append({"type": "parameter_control_plan", "severity": "critical", "id": p.id,
                         "title": f"{p.code}: специальная характеристика не связана с Control Plan"})
        if p.control_plan_item_id and p.control_plan_item_id not in cp_ids:
            gaps.append({"type": "parameter_hidden_control_plan", "severity": "warning", "id": p.id,
                         "title": f"{p.code}: связанный Control Plan недоступен в текущем контексте"})
        if p.status in ACTIVE_PROCESS and not (p.reaction_plan or "").strip():
            gaps.append({"type": "parameter_reaction", "severity": "warning", "id": p.id,
                         "title": f"{p.code}: для параметра не указан reaction plan"})
        if p.target_value is None and p.lower_spec_limit is None and p.upper_spec_limit is None:
            gaps.append({"type": "parameter_spec", "severity": "warning", "id": p.id,
                         "title": f"{p.code}: не задан target/пределы процесса"})

    now = datetime.now(timezone.utc)
    for asset in assets:
        cal = asset.calibration_due_at
        maint = asset.maintenance_due_at
        if cal and cal.replace(tzinfo=cal.tzinfo or timezone.utc) < now and asset.status == "active":
            gaps.append({"type": "asset_calibration", "severity": "critical" if asset.asset_type in {"gauge", "measurement"} else "warning", "id": asset.id,
                         "title": f"{asset.code}: просрочена калибровка"})
        if maint and maint.replace(tzinfo=maint.tzinfo or timezone.utc) < now and asset.status == "active":
            gaps.append({"type": "asset_maintenance", "severity": "warning", "id": asset.id,
                         "title": f"{asset.code}: просрочено обслуживание"})

    open_defects = [x for x in defects if x.status not in TERMINAL_DEFECT]
    for defect in open_defects:
        if defect.severity in {"high", "critical"}:
            gaps.append({"type": "process_defect", "severity": "critical" if defect.severity == "critical" else "warning", "id": defect.id,
                         "part_number": defect.part_number, "title": f"Дефект процесса: {defect.title}"})
        if defect.severity in {"high", "critical"} and not defect.linked_8d_id:
            gaps.append({"type": "defect_8d", "severity": "warning", "id": defect.id, "part_number": defect.part_number,
                         "title": f"{defect.title}: high/critical дефект не связан с 8D"})

    configured = bool(lines or stations or operations)
    if configured:
        critical_count = sum(x["severity"] == "critical" for x in gaps)
        warning_count = sum(x["severity"] == "warning" for x in gaps)
        score = max(0.0, round(100.0 - critical_count * 20.0 - warning_count * 4.0, 1))
    else:
        score = 0.0

    stations_by_line: dict[str, list[ProcessStation]] = {}
    ops_by_station: dict[str, list[ProcessOperation]] = {}
    assets_by_op: dict[str, list[ProcessAsset]] = {}
    params_by_op: dict[str, list[ProcessParameter]] = {}
    for x in stations: stations_by_line.setdefault(x.line_id, []).append(x)
    for x in operations: ops_by_station.setdefault(x.station_id, []).append(x)
    for x in assets: assets_by_op.setdefault(x.operation_id, []).append(x)
    for x in parameters: params_by_op.setdefault(x.operation_id, []).append(x)

    tree = []
    for line in lines:
        line_data = serialize_line(line)
        line_data["stations"] = []
        for st in stations_by_line.get(line.id, []):
            st_data = serialize_station(st)
            st_data["operations"] = []
            for op in ops_by_station.get(st.id, []):
                op_data = serialize_operation(op, visible_document_ids)
                op_data["pfmea_count"] = len(pfmea_by_op.get(op.id, []))
                op_data["control_plan_count"] = len(cp_by_op.get(op.id, []))
                linked_wi = instructions_by_op.get(op.id, []) + instructions_by_station.get(op.station_id, [])
                op_data["work_instructions"] = [{"id": x.id, "code": x.code, "title": x.title, "revision": x.revision,
                                                   "status": x.status, "source_language": x.source_language,
                                                   "translation_status": x.translation_status} for x in linked_wi]
                op_data["approved_work_instruction_count"] = sum(x.status == "approved" for x in linked_wi)
                op_data["assets"] = [serialize_asset(x) for x in assets_by_op.get(op.id, [])]
                op_data["parameters"] = [serialize_parameter(x) for x in params_by_op.get(op.id, [])]
                st_data["operations"].append(op_data)
            line_data["stations"].append(st_data)
        tree.append(line_data)

    return {
        "configured": configured,
        "score": score,
        "advisory_only": True,
        "not_mes_or_scada": True,
        "manufacturing_area": manufacturing_area,
        "counts": {"lines": len(lines), "stations": len(stations), "operations": len(operations), "work_instructions": len(instructions),
                   "approved_work_instructions": sum(x.status == "approved" for x in instructions), "assets": len(assets),
                   "parameters": len(parameters), "open_defects": len(open_defects), "gaps": len(gaps)},
        "gaps": gaps[:100],
        "tree": tree,
        "defects": [serialize_defect(x, visible_document_ids) for x in defects[:100]],
        "recommended_operation_types": AREA_OPERATION_HINTS.get(manufacturing_area or "", []),
    }
