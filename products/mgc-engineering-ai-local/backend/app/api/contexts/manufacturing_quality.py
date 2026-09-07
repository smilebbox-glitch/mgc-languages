"""Manufacturing Quality HTTP handlers — v6.2.2.

Extracted from the former 3k-line route monolith. Public paths are unchanged.
"""
from fastapi import APIRouter, Header, Request
from app.api import context_shared as _shared

# Preserve the mature shared handler namespace without duplicating service imports.
globals().update({k: v for k, v in vars(_shared).items() if not k.startswith("__")})
from app.api.lazy_service import lazy_service
from app.db.unit_of_work import UnitOfWork, require_expected_version
from app.schemas.api import WorkInstructionRevisionCreateRequest, ManufacturingLayoutRevisionCreateRequest

launch_readiness = lazy_service("app.services.launch_readiness", "launch_readiness")
log_event = lazy_service("app.services.audit", "log_event")
add_audit_event = lazy_service("app.services.audit", "add_audit_event")
process_digital_thread = lazy_service("app.services.process_digital_thread", "process_digital_thread")
quality_workspace = lazy_service("app.services.quality_core_tools", "quality_workspace")
serialize_8d = lazy_service("app.services.quality_core_tools", "serialize_8d")
serialize_apqp = lazy_service("app.services.quality_core_tools", "serialize_apqp")
serialize_asset = lazy_service("app.services.process_digital_thread", "serialize_asset")
serialize_build = lazy_service("app.services.vehicle_build_launch_intelligence", "serialize_build")
serialize_capability = lazy_service("app.services.series_quality_manufacturing_intelligence", "serialize_capability")
serialize_characteristic = lazy_service("app.services.quality_core_tools", "serialize_characteristic")
serialize_containment = lazy_service("app.services.series_quality_manufacturing_intelligence", "serialize_containment")
serialize_control_plan = lazy_service("app.services.quality_core_tools", "serialize_control_plan")
serialize_defect = lazy_service("app.services.process_digital_thread", "serialize_defect")
serialize_genealogy = lazy_service("app.services.vehicle_build_launch_intelligence", "serialize_genealogy")
serialize_launch_item = lazy_service("app.services.launch_readiness", "serialize_launch_item")
serialize_launch_trial = lazy_service("app.services.launch_readiness", "serialize_launch_trial")
serialize_line = lazy_service("app.services.cost_economics", "serialize_line")
serialize_operation = lazy_service("app.services.process_digital_thread", "serialize_operation")
serialize_parameter = lazy_service("app.services.process_digital_thread", "serialize_parameter")
serialize_pfmea = lazy_service("app.services.quality_core_tools", "serialize_pfmea")
serialize_ppap = lazy_service("app.services.quality_core_tools", "serialize_ppap")
serialize_safe_launch = lazy_service("app.services.vehicle_build_launch_intelligence", "serialize_safe_launch")
serialize_series_observation = lazy_service("app.services.series_quality_manufacturing_intelligence", "serialize_series_observation")
serialize_station = lazy_service("app.services.process_digital_thread", "serialize_station")
series_intelligence_answer = lazy_service("app.services.series_quality_manufacturing_intelligence", "series_intelligence_answer")
series_quality_workspace = lazy_service("app.services.series_quality_manufacturing_intelligence", "series_quality_workspace")
suspect_population = lazy_service("app.services.series_quality_manufacturing_intelligence", "suspect_population")
vehicle_build_launch_workspace = lazy_service("app.services.vehicle_build_launch_intelligence", "vehicle_build_launch_workspace")
visible_project_areas = lazy_service("app.services.manufacturing_areas", "visible_project_areas")
work_instruction_workspace = lazy_service("app.services.work_instructions", "workspace")
serialize_work_instruction = lazy_service("app.services.work_instructions", "serialize_instruction")
serialize_manufacturing_layout = lazy_service("app.services.work_instructions", "serialize_layout")
import_work_instruction_document = lazy_service("app.services.work_instructions", "import_document_text")
translate_work_instruction = lazy_service("app.services.work_instructions", "translate_instruction")
ask_work_instructions = lazy_service("app.services.work_instructions", "ask_instructions")
translation_is_current = lazy_service("app.services.work_instructions", "translation_is_current")
detect_instruction_language = lazy_service("app.services.engineering_translation", "detect_language")
clone_work_instruction_revision = lazy_service("app.services.revision_control", "clone_work_instruction")
clone_manufacturing_layout_revision = lazy_service("app.services.revision_control", "clone_layout")
work_instruction_visual_diff = lazy_service("app.services.revision_control", "work_instruction_diff")
manufacturing_layout_visual_diff = lazy_service("app.services.revision_control", "layout_diff")
idempotency_lookup = lazy_service("app.services.revision_control", "idempotency_lookup")
store_idempotency = lazy_service("app.services.revision_control", "store_idempotency")
record_revision_snapshot = lazy_service("app.services.revision_control", "record_snapshot")
resolve_governance_policy = lazy_service("app.services.approval_governance", "resolve_policy")


router = APIRouter(tags=["context:manufacturing_quality"])

@router.get("/projects/{project_code}/quality")
def project_quality_workspace(project_code: str, manufacturing_area: str | None = None, identity: Identity = Depends(get_identity), db: Session = Depends(get_db)):
    project, visible_doc_ids, visible_parts = _quality_project_context(db, project_code, identity, manufacturing_area)
    allowed_areas = {a.code for a in visible_project_areas(db, project, identity.groups)}
    return quality_workspace(db, project.code, visible_doc_ids, visible_parts, manufacturing_area, allowed_areas)

@router.post("/projects/{project_code}/quality/apqp")
def create_apqp_deliverable(project_code: str, req: APQPDeliverableCreateRequest, identity: Identity = Depends(get_identity), db: Session = Depends(get_db)):
    project, visible_doc_ids, visible_parts = _quality_project_context(db, project_code, identity)
    _validate_quality_area(db, project, identity, req.manufacturing_area)
    code = req.code.upper()
    if db.scalar(select(APQPDeliverable).where(APQPDeliverable.project_code == project.code, APQPDeliverable.code == code)):
        raise HTTPException(409, "APQP deliverable code already exists")
    linked_parts = [_validate_quality_part(x, visible_parts) for x in req.linked_part_numbers]
    row = APQPDeliverable(project_code=project.code, manufacturing_area=req.manufacturing_area, code=code, phase=req.phase,
                          title=req.title.strip(), owner=req.owner or identity.user, due_at=_parse_iso_datetime(req.due_at),
                          linked_part_numbers=[x for x in linked_parts if x], evidence_document_ids=_validate_quality_evidence(db, project, visible_doc_ids, req.evidence_document_ids), notes=req.notes)
    db.add(row); db.commit(); db.refresh(row)
    log_event(db, identity.user, "APQP_DELIVERABLE_CREATED", "project", project.code, {"id": row.id, "code": row.code, "area": row.manufacturing_area})
    return serialize_apqp(row, visible_doc_ids)

@router.patch("/projects/{project_code}/quality/apqp/{item_id}")
def update_apqp_deliverable(project_code: str, item_id: str, req: APQPDeliverableUpdateRequest, identity: Identity = Depends(get_identity), db: Session = Depends(get_db)):
    project, visible_doc_ids, visible_parts = _quality_project_context(db, project_code, identity)
    row = db.get(APQPDeliverable, item_id)
    if not row or row.project_code != project.code: raise HTTPException(404)
    _validate_quality_area(db, project, identity, row.manufacturing_area)
    values = req.model_dump(exclude_unset=True)
    if "manufacturing_area" in values: _validate_quality_area(db, project, identity, values["manufacturing_area"])
    if "due_at" in values: values["due_at"] = _parse_iso_datetime(values["due_at"])
    if "linked_part_numbers" in values: values["linked_part_numbers"] = [_validate_quality_part(x, visible_parts) for x in values["linked_part_numbers"]]
    if "evidence_document_ids" in values: values["evidence_document_ids"] = _validate_quality_evidence(db, project, visible_doc_ids, values["evidence_document_ids"])
    for k,v in values.items(): setattr(row,k,v)
    db.commit(); db.refresh(row); log_event(db, identity.user, "APQP_DELIVERABLE_UPDATED", "project", project.code, {"id": row.id, "fields": sorted(values)})
    return serialize_apqp(row, visible_doc_ids)

@router.post("/projects/{project_code}/quality/characteristics")
def create_special_characteristic(project_code: str, req: SpecialCharacteristicCreateRequest, identity: Identity = Depends(get_identity), db: Session = Depends(get_db)):
    project, visible_doc_ids, visible_parts = _quality_project_context(db, project_code, identity)
    _validate_quality_area(db, project, identity, req.manufacturing_area)
    code=req.code.upper()
    if db.scalar(select(SpecialCharacteristic).where(SpecialCharacteristic.project_code==project.code, SpecialCharacteristic.code==code)):
        raise HTTPException(409, "Characteristic code already exists")
    pn=_validate_quality_part(req.part_number, visible_parts)
    source=req.source_document_id
    if source: _validate_quality_evidence(db, project, visible_doc_ids, [source])
    row=SpecialCharacteristic(project_code=project.code, manufacturing_area=req.manufacturing_area, part_number=pn, revision=req.revision,
                              code=code, category=req.category, symbol=req.symbol, description=req.description.strip(), specification=req.specification,
                              unit=req.unit, source_document_id=source, source_reference_json=req.source_reference, owner=req.owner or identity.user)
    db.add(row); db.commit(); db.refresh(row); log_event(db, identity.user, "SPECIAL_CHARACTERISTIC_CREATED", "project", project.code, {"id":row.id,"code":row.code})
    return serialize_characteristic(row, visible_doc_ids)

@router.patch("/projects/{project_code}/quality/characteristics/{item_id}")
def update_special_characteristic(project_code: str, item_id: str, req: SpecialCharacteristicUpdateRequest, identity: Identity = Depends(get_identity), db: Session = Depends(get_db)):
    project, visible_doc_ids, visible_parts = _quality_project_context(db, project_code, identity)
    row=db.get(SpecialCharacteristic,item_id)
    if not row or row.project_code!=project.code or (row.part_number and row.part_number not in visible_parts): raise HTTPException(404)
    _validate_quality_area(db, project, identity, row.manufacturing_area)
    values=req.model_dump(exclude_unset=True)
    if "manufacturing_area" in values: _validate_quality_area(db, project, identity, values["manufacturing_area"])
    if "part_number" in values: values["part_number"]=_validate_quality_part(values["part_number"], visible_parts)
    if "source_document_id" in values and values["source_document_id"]: _validate_quality_evidence(db, project, visible_doc_ids, [values["source_document_id"]])
    if "source_reference" in values: values["source_reference_json"]=values.pop("source_reference")
    for k,v in values.items(): setattr(row,k,v)
    db.commit(); db.refresh(row); log_event(db, identity.user, "SPECIAL_CHARACTERISTIC_UPDATED", "project", project.code, {"id":row.id,"fields":sorted(values)})
    return serialize_characteristic(row, visible_doc_ids)

@router.post("/projects/{project_code}/quality/pfmea")
def create_pfmea_item(project_code: str, req: PFMEAItemCreateRequest, identity: Identity = Depends(get_identity), db: Session = Depends(get_db)):
    project, visible_doc_ids, visible_parts = _quality_project_context(db, project_code, identity)
    _validate_quality_area(db, project, identity, req.manufacturing_area)
    process_operation_id=_validate_process_operation_ref(db,project,identity,visible_parts,req.process_operation_id,req.manufacturing_area)
    row=PFMEAItem(project_code=project.code, manufacturing_area=req.manufacturing_area, part_number=_validate_quality_part(req.part_number,visible_parts),
                  process_step=req.process_step.strip(), process_operation_id=process_operation_id, function=req.function, failure_mode=req.failure_mode.strip(), effect=req.effect, cause=req.cause,
                  prevention_control=req.prevention_control, detection_control=req.detection_control, severity=req.severity, occurrence=req.occurrence,
                  detection=req.detection, action_priority=req.action_priority.upper() if req.action_priority else None, recommended_action=req.recommended_action,
                  action_owner=req.action_owner or identity.user, due_at=_parse_iso_datetime(req.due_at),
                  special_characteristic_ids=_validate_characteristic_refs(db,project.code,req.special_characteristic_ids,visible_parts),
                  evidence_document_ids=_validate_quality_evidence(db,project,visible_doc_ids,req.evidence_document_ids))
    db.add(row); db.commit(); db.refresh(row); log_event(db, identity.user, "PFMEA_ITEM_CREATED", "project", project.code, {"id":row.id,"part":row.part_number})
    return serialize_pfmea(row,visible_doc_ids)

@router.patch("/projects/{project_code}/quality/pfmea/{item_id}")
def update_pfmea_item(project_code: str, item_id: str, req: PFMEAItemUpdateRequest, identity: Identity = Depends(get_identity), db: Session = Depends(get_db)):
    project, visible_doc_ids, visible_parts=_quality_project_context(db,project_code,identity)
    row=db.get(PFMEAItem,item_id)
    if not row or row.project_code!=project.code or (row.part_number and row.part_number not in visible_parts): raise HTTPException(404)
    _validate_quality_area(db, project, identity, row.manufacturing_area)
    values=req.model_dump(exclude_unset=True)
    if "manufacturing_area" in values: _validate_quality_area(db,project,identity,values["manufacturing_area"])
    if "part_number" in values: values["part_number"]=_validate_quality_part(values["part_number"],visible_parts)
    if "due_at" in values: values["due_at"]=_parse_iso_datetime(values["due_at"])
    if "process_operation_id" in values: values["process_operation_id"]=_validate_process_operation_ref(db,project,identity,visible_parts,values["process_operation_id"],values.get("manufacturing_area",row.manufacturing_area))
    if values.get("action_priority"): values["action_priority"]=values["action_priority"].upper()
    if "special_characteristic_ids" in values: values["special_characteristic_ids"]=_validate_characteristic_refs(db,project.code,values["special_characteristic_ids"],visible_parts)
    if "evidence_document_ids" in values: values["evidence_document_ids"]=_validate_quality_evidence(db,project,visible_doc_ids,values["evidence_document_ids"])
    for k,v in values.items(): setattr(row,k,v)
    db.commit(); db.refresh(row); log_event(db,identity.user,"PFMEA_ITEM_UPDATED","project",project.code,{"id":row.id,"fields":sorted(values)})
    return serialize_pfmea(row,visible_doc_ids)

@router.post("/projects/{project_code}/quality/control-plan")
def create_control_plan_item(project_code: str, req: ControlPlanItemCreateRequest, identity: Identity = Depends(get_identity), db: Session = Depends(get_db)):
    project, visible_doc_ids, visible_parts=_quality_project_context(db,project_code,identity)
    _validate_quality_area(db,project,identity,req.manufacturing_area)
    cid=req.characteristic_id
    if cid: _validate_characteristic_refs(db,project.code,[cid],visible_parts)
    process_operation_id=_validate_process_operation_ref(db,project,identity,visible_parts,req.process_operation_id,req.manufacturing_area)
    row=ControlPlanItem(project_code=project.code,manufacturing_area=req.manufacturing_area,part_number=_validate_quality_part(req.part_number,visible_parts),
                        process_step=req.process_step.strip(),process_operation_id=process_operation_id,characteristic_id=cid,characteristic=req.characteristic.strip(),specification=req.specification,
                        measurement_method=req.measurement_method,sample_size=req.sample_size,frequency=req.frequency,reaction_plan=req.reaction_plan,
                        control_phase=req.control_phase,owner=req.owner or identity.user,status=req.status,
                        evidence_document_ids=_validate_quality_evidence(db,project,visible_doc_ids,req.evidence_document_ids))
    db.add(row); db.commit(); db.refresh(row); log_event(db,identity.user,"CONTROL_PLAN_ITEM_CREATED","project",project.code,{"id":row.id,"part":row.part_number})
    return serialize_control_plan(row,visible_doc_ids)

@router.patch("/projects/{project_code}/quality/control-plan/{item_id}")
def update_control_plan_item(project_code: str, item_id: str, req: ControlPlanItemUpdateRequest, identity: Identity = Depends(get_identity), db: Session = Depends(get_db)):
    project, visible_doc_ids, visible_parts=_quality_project_context(db,project_code,identity)
    row=db.get(ControlPlanItem,item_id)
    if not row or row.project_code!=project.code or (row.part_number and row.part_number not in visible_parts): raise HTTPException(404)
    _validate_quality_area(db, project, identity, row.manufacturing_area)
    values=req.model_dump(exclude_unset=True)
    if "manufacturing_area" in values: _validate_quality_area(db,project,identity,values["manufacturing_area"])
    if "part_number" in values: values["part_number"]=_validate_quality_part(values["part_number"],visible_parts)
    if "process_operation_id" in values: values["process_operation_id"]=_validate_process_operation_ref(db,project,identity,visible_parts,values["process_operation_id"],values.get("manufacturing_area",row.manufacturing_area))
    if values.get("characteristic_id"): _validate_characteristic_refs(db,project.code,[values["characteristic_id"]],visible_parts)
    if "evidence_document_ids" in values: values["evidence_document_ids"]=_validate_quality_evidence(db,project,visible_doc_ids,values["evidence_document_ids"])
    for k,v in values.items(): setattr(row,k,v)
    db.commit(); db.refresh(row); log_event(db,identity.user,"CONTROL_PLAN_ITEM_UPDATED","project",project.code,{"id":row.id,"fields":sorted(values)})
    return serialize_control_plan(row,visible_doc_ids)

@router.post("/projects/{project_code}/quality/ppap")
def create_ppap(project_code: str, req: PPAPCreateRequest, identity: Identity = Depends(get_identity), db: Session = Depends(get_db)):
    project, visible_doc_ids, visible_parts=_quality_project_context(db,project_code,identity)
    _validate_quality_area(db,project,identity,req.manufacturing_area)
    row=PPAPSubmission(project_code=project.code,manufacturing_area=req.manufacturing_area,part_number=_validate_quality_part(req.part_number,visible_parts),
                       revision=req.revision,supplier_code=req.supplier_code,supplier_name=req.supplier_name,customer=req.customer,submission_level=req.submission_level,
                       due_at=_parse_iso_datetime(req.due_at),element_status_json=req.element_status,
                       evidence_document_ids=_validate_quality_evidence(db,project,visible_doc_ids,req.evidence_document_ids),notes=req.notes,created_by=identity.user)
    db.add(row); db.commit(); db.refresh(row); log_event(db,identity.user,"PPAP_CREATED","project",project.code,{"id":row.id,"part":row.part_number})
    return serialize_ppap(row,visible_doc_ids)

@router.patch("/projects/{project_code}/quality/ppap/{item_id}")
def update_ppap(project_code: str, item_id: str, req: PPAPUpdateRequest, identity: Identity = Depends(get_identity), db: Session = Depends(get_db)):
    project, visible_doc_ids, visible_parts=_quality_project_context(db,project_code,identity)
    row=db.get(PPAPSubmission,item_id)
    if not row or row.project_code!=project.code or row.part_number not in visible_parts: raise HTTPException(404)
    _validate_quality_area(db, project, identity, row.manufacturing_area)
    values=req.model_dump(exclude_unset=True)
    if "manufacturing_area" in values: _validate_quality_area(db,project,identity,values["manufacturing_area"])
    if "due_at" in values: values["due_at"]=_parse_iso_datetime(values["due_at"])
    if "element_status" in values: values["element_status_json"]=values.pop("element_status")
    if "evidence_document_ids" in values: values["evidence_document_ids"]=_validate_quality_evidence(db,project,visible_doc_ids,values["evidence_document_ids"])
    status=values.get("status")
    if status=="submitted" and not row.submitted_at: values["submitted_at"]=datetime.now().astimezone()
    if status=="approved": values["approved_at"]=datetime.now().astimezone()
    for k,v in values.items(): setattr(row,k,v)
    db.commit(); db.refresh(row); log_event(db,identity.user,"PPAP_UPDATED","project",project.code,{"id":row.id,"fields":sorted(values)})
    return serialize_ppap(row,visible_doc_ids)

@router.post("/projects/{project_code}/quality/8d")
def create_problem_8d(project_code: str, req: Problem8DCreateRequest, identity: Identity = Depends(get_identity), db: Session = Depends(get_db)):
    project, visible_doc_ids, visible_parts=_quality_project_context(db,project_code,identity)
    _validate_quality_area(db,project,identity,req.manufacturing_area)
    if req.linked_change_id:
        ch=db.get(ChangeRequest,req.linked_change_id)
        if not ch or (ch.part_number and ch.part_number not in visible_parts): raise HTTPException(404,"Linked change not found")
    row=Problem8D(project_code=project.code,manufacturing_area=req.manufacturing_area,part_number=_validate_quality_part(req.part_number,visible_parts),
                  complaint_reference=req.complaint_reference,title=req.title.strip(),severity=req.severity,owner=req.owner or identity.user,team_json=req.team,
                  disciplines_json={},linked_change_id=req.linked_change_id,evidence_document_ids=_validate_quality_evidence(db,project,visible_doc_ids,req.evidence_document_ids),created_by=identity.user)
    db.add(row); db.commit(); db.refresh(row); log_event(db,identity.user,"PROBLEM_8D_CREATED","project",project.code,{"id":row.id,"part":row.part_number})
    return serialize_8d(row,visible_doc_ids)

@router.patch("/projects/{project_code}/quality/8d/{item_id}")
def update_problem_8d(project_code: str, item_id: str, req: Problem8DUpdateRequest, identity: Identity = Depends(get_identity), db: Session = Depends(get_db)):
    project, visible_doc_ids, visible_parts=_quality_project_context(db,project_code,identity)
    row=db.get(Problem8D,item_id)
    if not row or row.project_code!=project.code or (row.part_number and row.part_number not in visible_parts): raise HTTPException(404)
    _validate_quality_area(db, project, identity, row.manufacturing_area)
    values=req.model_dump(exclude_unset=True)
    if "manufacturing_area" in values: _validate_quality_area(db,project,identity,values["manufacturing_area"])
    if "part_number" in values: values["part_number"]=_validate_quality_part(values["part_number"],visible_parts)
    if "team" in values: values["team_json"]=values.pop("team")
    if "disciplines" in values:
        merged=dict(row.disciplines_json or {}); merged.update(values.pop("disciplines") or {}); values["disciplines_json"]=merged
    if values.get("linked_change_id"):
        ch=db.get(ChangeRequest,values["linked_change_id"])
        if not ch or (ch.part_number and ch.part_number not in visible_parts): raise HTTPException(404,"Linked change not found")
    if "evidence_document_ids" in values: values["evidence_document_ids"]=_validate_quality_evidence(db,project,visible_doc_ids,values["evidence_document_ids"])
    if values.get("status")=="closed":
        disciplines=values.get("disciplines_json",row.disciplines_json or {})
        missing=[f"d{i}" for i in range(1,9) if not disciplines.get(f"d{i}")]
        if missing: raise HTTPException(400,f"8D cannot be closed; incomplete disciplines: {', '.join(missing)}")
    for k,v in values.items(): setattr(row,k,v)
    db.commit(); db.refresh(row); log_event(db,identity.user,"PROBLEM_8D_UPDATED","project",project.code,{"id":row.id,"fields":sorted(values)})
    return serialize_8d(row,visible_doc_ids)

@router.get("/projects/{project_code}/process-thread")
def get_process_thread(project_code: str, manufacturing_area: str | None = None, identity: Identity = Depends(get_identity), db: Session = Depends(get_db)):
    project, visible_doc_ids, visible_parts = _quality_project_context(db, project_code, identity, manufacturing_area)
    allowed_areas = {a.code for a in visible_project_areas(db, project, identity.groups)}
    return process_digital_thread(db, project.code, visible_doc_ids, visible_parts, manufacturing_area, allowed_areas)

@router.post("/projects/{project_code}/process/lines")
def create_manufacturing_line(project_code: str, req: ManufacturingLineCreateRequest, identity: Identity = Depends(get_identity), db: Session = Depends(get_db)):
    project, _, _ = _quality_project_context(db, project_code, identity)
    _validate_quality_area(db, project, identity, req.manufacturing_area)
    code = req.code.upper()
    if db.scalar(select(ManufacturingLine).where(ManufacturingLine.project_code == project.code, ManufacturingLine.code == code)):
        raise HTTPException(409, "Manufacturing line code already exists")
    row = ManufacturingLine(project_code=project.code, manufacturing_area=req.manufacturing_area, code=code, name=req.name.strip(),
                            plant=req.plant, owner=req.owner or identity.user)
    db.add(row); db.commit(); db.refresh(row)
    log_event(db, identity.user, "PROCESS_LINE_CREATED", "project", project.code, {"id": row.id, "code": row.code, "area": row.manufacturing_area})
    return serialize_line(row)

@router.post("/projects/{project_code}/process/lines/{line_id}/stations")
def create_process_station(project_code: str, line_id: str, req: ProcessStationCreateRequest, identity: Identity = Depends(get_identity), db: Session = Depends(get_db)):
    project = _get_visible_project(db, project_code, identity)
    line = _process_line_context(db, project, identity, line_id)
    code = req.code.upper()
    if db.scalar(select(ProcessStation).where(ProcessStation.line_id == line.id, ProcessStation.code == code)):
        raise HTTPException(409, "Station code already exists on this line")
    row = ProcessStation(line_id=line.id, code=code, name=req.name.strip(), sequence=req.sequence, owner=req.owner or identity.user,
                         operator_role=req.operator_role, headcount=req.headcount, work_content=req.work_content, takt_time_sec=req.takt_time_sec)
    db.add(row); db.commit(); db.refresh(row)
    log_event(db, identity.user, "PROCESS_STATION_CREATED", "project", project.code, {"id": row.id, "line": line.code, "code": row.code})
    return serialize_station(row)

@router.post("/projects/{project_code}/process/stations/{station_id}/operations")
def create_process_operation(project_code: str, station_id: str, req: ProcessOperationCreateRequest, identity: Identity = Depends(get_identity), db: Session = Depends(get_db)):
    project, visible_doc_ids, visible_parts = _quality_project_context(db, project_code, identity)
    station, line = _process_station_context(db, project, identity, station_id)
    part_number = _validate_quality_part(req.part_number, visible_parts)
    evidence = _validate_quality_evidence(db, project, visible_doc_ids, req.work_instruction_document_ids)
    code = req.code.upper()
    if db.scalar(select(ProcessOperation).where(ProcessOperation.station_id == station.id, ProcessOperation.code == code)):
        raise HTTPException(409, "Operation code already exists on this station")
    row = ProcessOperation(station_id=station.id, code=code, name=req.name.strip(), sequence=req.sequence, operation_type=req.operation_type,
                           part_number=part_number, cycle_time_sec=req.cycle_time_sec, work_instruction_document_ids=evidence, owner=req.owner or identity.user)
    db.add(row); db.commit(); db.refresh(row)
    log_event(db, identity.user, "PROCESS_OPERATION_CREATED", "project", project.code, {"id": row.id, "line": line.code, "station": station.code, "code": row.code})
    return serialize_operation(row, visible_doc_ids)

@router.post("/projects/{project_code}/process/operations/{operation_id}/assets")
def create_process_asset(project_code: str, operation_id: str, req: ProcessAssetCreateRequest, identity: Identity = Depends(get_identity), db: Session = Depends(get_db)):
    project, _, visible_parts = _quality_project_context(db, project_code, identity)
    op, _, _ = _process_operation_context(db, project, identity, visible_parts, operation_id)
    code = req.code.upper()
    if db.scalar(select(ProcessAsset).where(ProcessAsset.operation_id == op.id, ProcessAsset.code == code)):
        raise HTTPException(409, "Asset code already exists on this operation")
    row = ProcessAsset(operation_id=op.id, code=code, name=req.name.strip(), asset_type=req.asset_type, asset_reference=req.asset_reference,
                       calibration_due_at=_parse_iso_datetime(req.calibration_due_at), maintenance_due_at=_parse_iso_datetime(req.maintenance_due_at))
    db.add(row); db.commit(); db.refresh(row)
    log_event(db, identity.user, "PROCESS_ASSET_CREATED", "project", project.code, {"id": row.id, "operation": op.code, "asset": row.code})
    return serialize_asset(row)

@router.post("/projects/{project_code}/process/operations/{operation_id}/parameters")
def create_process_parameter(project_code: str, operation_id: str, req: ProcessParameterCreateRequest, identity: Identity = Depends(get_identity), db: Session = Depends(get_db)):
    project, _, visible_parts = _quality_project_context(db, project_code, identity)
    op, _, line = _process_operation_context(db, project, identity, visible_parts, operation_id)
    characteristic = None
    if req.special_characteristic_id:
        characteristic = db.get(SpecialCharacteristic, req.special_characteristic_id)
        if not characteristic or characteristic.project_code != project.code or (characteristic.part_number and characteristic.part_number not in visible_parts):
            raise HTTPException(404, "Special characteristic not found")
        if characteristic.manufacturing_area and characteristic.manufacturing_area != line.manufacturing_area:
            raise HTTPException(400, "Special characteristic belongs to another manufacturing area")
    cp = None
    if req.control_plan_item_id:
        cp = db.get(ControlPlanItem, req.control_plan_item_id)
        if not cp or cp.project_code != project.code or (cp.part_number and cp.part_number not in visible_parts):
            raise HTTPException(404, "Control Plan item not found")
        if cp.process_operation_id and cp.process_operation_id != op.id:
            raise HTTPException(400, "Control Plan item is linked to another process operation")
    code = req.code.upper()
    if db.scalar(select(ProcessParameter).where(ProcessParameter.operation_id == op.id, ProcessParameter.code == code)):
        raise HTTPException(409, "Parameter code already exists on this operation")
    row = ProcessParameter(operation_id=op.id, code=code, name=req.name.strip(), target_value=req.target_value,
                           lower_spec_limit=req.lower_spec_limit, upper_spec_limit=req.upper_spec_limit, unit=req.unit,
                           special_characteristic_id=req.special_characteristic_id, control_plan_item_id=req.control_plan_item_id,
                           measurement_method=req.measurement_method, reaction_plan=req.reaction_plan)
    db.add(row); db.commit(); db.refresh(row)
    log_event(db, identity.user, "PROCESS_PARAMETER_CREATED", "project", project.code, {"id": row.id, "operation": op.code, "parameter": row.code})
    return serialize_parameter(row)

@router.post("/projects/{project_code}/process/defects")
def create_process_defect(project_code: str, req: ProcessDefectCreateRequest, identity: Identity = Depends(get_identity), db: Session = Depends(get_db)):
    project, visible_doc_ids, visible_parts = _quality_project_context(db, project_code, identity)
    if req.manufacturing_area:
        _validate_quality_area(db, project, identity, req.manufacturing_area)
    part_number = _validate_quality_part(req.part_number, visible_parts)
    evidence = _validate_quality_evidence(db, project, visible_doc_ids, req.evidence_document_ids)
    operation = station = line = None
    if req.operation_id:
        operation, station, line = _process_operation_context(db, project, identity, visible_parts, req.operation_id)
    elif req.station_id:
        station, line = _process_station_context(db, project, identity, req.station_id)
    elif req.line_id:
        line = _process_line_context(db, project, identity, req.line_id)
    if req.line_id and line and req.line_id != line.id: raise HTTPException(400, "Line/station/operation mismatch")
    if req.station_id and station and req.station_id != station.id: raise HTTPException(400, "Station/operation mismatch")
    area = req.manufacturing_area or (line.manufacturing_area if line else None)
    if area: _validate_quality_area(db, project, identity, area)
    if line and area != line.manufacturing_area: raise HTTPException(400, "Defect manufacturing area does not match process line")
    if req.linked_8d_id:
        problem = db.get(Problem8D, req.linked_8d_id)
        if not problem or problem.project_code != project.code or (problem.part_number and problem.part_number not in visible_parts):
            raise HTTPException(404, "Linked 8D not found")
    row = ProcessDefect(project_code=project.code, manufacturing_area=area, line_id=line.id if line else None,
                        station_id=station.id if station else None, operation_id=operation.id if operation else None,
                        part_number=part_number, defect_code=req.defect_code.upper() if req.defect_code else None, title=req.title.strip(),
                        severity=req.severity, quantity=req.quantity, linked_8d_id=req.linked_8d_id, evidence_document_ids=evidence,
                        occurred_at=_parse_iso_datetime(req.occurred_at) or datetime.now().astimezone(), created_by=identity.user)
    db.add(row); db.commit(); db.refresh(row)
    log_event(db, identity.user, "PROCESS_DEFECT_CREATED", "project", project.code, {"id": row.id, "title": row.title, "severity": row.severity, "area": row.manufacturing_area})
    return serialize_defect(row, visible_doc_ids)

@router.patch("/projects/{project_code}/process/defects/{defect_id}")
def update_process_defect(project_code: str, defect_id: str, req: ProcessDefectUpdateRequest, identity: Identity = Depends(get_identity), db: Session = Depends(get_db)):
    project, visible_doc_ids, visible_parts = _quality_project_context(db, project_code, identity)
    row = db.get(ProcessDefect, defect_id)
    if not row or row.project_code != project.code or (row.part_number and row.part_number not in visible_parts):
        raise HTTPException(404, "Process defect not found")
    if row.manufacturing_area: _validate_quality_area(db, project, identity, row.manufacturing_area)
    values = req.model_dump(exclude_unset=True)
    if values.get("linked_8d_id"):
        problem = db.get(Problem8D, values["linked_8d_id"])
        if not problem or problem.project_code != project.code or (problem.part_number and problem.part_number not in visible_parts):
            raise HTTPException(404, "Linked 8D not found")
    for key, value in values.items(): setattr(row, key, value)
    db.commit(); db.refresh(row)
    log_event(db, identity.user, "PROCESS_DEFECT_UPDATED", "project", project.code, {"id": row.id, "fields": sorted(values), "status": row.status})
    return serialize_defect(row, visible_doc_ids)

@router.get("/projects/{project_code}/launch-readiness")
def project_launch_readiness(project_code: str, manufacturing_area: str | None = None, identity: Identity = Depends(get_identity), db: Session = Depends(get_db)):
    project, visible_doc_ids, visible_parts, allowed_areas = _launch_project_context(db, project_code, identity, manufacturing_area)
    return launch_readiness(db, project.code, visible_doc_ids, visible_parts, manufacturing_area, allowed_areas)

@router.post("/projects/{project_code}/launch/checks")
def create_launch_check(project_code: str, req: LaunchReadinessItemCreateRequest, identity: Identity = Depends(get_identity), db: Session = Depends(get_db)):
    project, visible_doc_ids, visible_parts, _ = _launch_project_context(db, project_code, identity)
    _validate_quality_area(db, project, identity, req.manufacturing_area)
    line_id = _validate_launch_line(db, project, identity, req.line_id, req.manufacturing_area)
    part_number = _validate_quality_part(req.part_number, visible_parts)
    evidence = _validate_quality_evidence(db, project, visible_doc_ids, req.evidence_document_ids)
    code = req.code.upper()
    if db.scalar(select(LaunchReadinessItem).where(LaunchReadinessItem.project_code == project.code, LaunchReadinessItem.code == code)):
        raise HTTPException(409, "Launch readiness code already exists")
    row = LaunchReadinessItem(project_code=project.code, manufacturing_area=req.manufacturing_area, line_id=line_id, part_number=part_number,
                              code=code, category=req.category, title=req.title.strip(), required=req.required, owner=req.owner or identity.user,
                              due_at=_parse_iso_datetime(req.due_at), supplier_code=req.supplier_code, supplier_name=req.supplier_name,
                              criteria_json=req.criteria, result_json=req.result, evidence_document_ids=evidence, notes=req.notes, created_by=identity.user)
    db.add(row); db.commit(); db.refresh(row)
    log_event(db, identity.user, "LAUNCH_CHECK_CREATED", "project", project.code, {"id": row.id, "code": row.code, "category": row.category, "area": row.manufacturing_area})
    return serialize_launch_item(row, visible_doc_ids)

@router.patch("/projects/{project_code}/launch/checks/{item_id}")
def update_launch_check(project_code: str, item_id: str, req: LaunchReadinessItemUpdateRequest, identity: Identity = Depends(get_identity), db: Session = Depends(get_db)):
    project, visible_doc_ids, visible_parts, _ = _launch_project_context(db, project_code, identity)
    row = db.get(LaunchReadinessItem, item_id)
    if not row or row.project_code != project.code or (row.part_number and row.part_number not in visible_parts):
        raise HTTPException(404, "Launch readiness item not found")
    _validate_quality_area(db, project, identity, row.manufacturing_area)
    values = req.model_dump(exclude_unset=True)
    requested_area = values.get("manufacturing_area", row.manufacturing_area)
    if "manufacturing_area" in values: _validate_quality_area(db, project, identity, values["manufacturing_area"])
    if "line_id" in values: values["line_id"] = _validate_launch_line(db, project, identity, values["line_id"], requested_area)
    if "part_number" in values: values["part_number"] = _validate_quality_part(values["part_number"], visible_parts)
    if "due_at" in values: values["due_at"] = _parse_iso_datetime(values["due_at"])
    if "evidence_document_ids" in values: values["evidence_document_ids"] = _validate_quality_evidence(db, project, visible_doc_ids, values["evidence_document_ids"])
    if "criteria" in values: values["criteria_json"] = values.pop("criteria")
    if "result" in values: values["result_json"] = values.pop("result")
    for key, value in values.items(): setattr(row, key, value)
    db.commit(); db.refresh(row)
    log_event(db, identity.user, "LAUNCH_CHECK_UPDATED", "project", project.code, {"id": row.id, "fields": sorted(values), "status": row.status})
    return serialize_launch_item(row, visible_doc_ids)

@router.post("/projects/{project_code}/launch/trials")
def create_launch_trial(project_code: str, req: LaunchTrialCreateRequest, identity: Identity = Depends(get_identity), db: Session = Depends(get_db)):
    project, visible_doc_ids, visible_parts, _ = _launch_project_context(db, project_code, identity)
    _validate_quality_area(db, project, identity, req.manufacturing_area)
    line_id = _validate_launch_line(db, project, identity, req.line_id, req.manufacturing_area)
    part_number = _validate_quality_part(req.part_number, visible_parts)
    evidence = _validate_quality_evidence(db, project, visible_doc_ids, req.evidence_document_ids)
    code = req.code.upper()
    if db.scalar(select(LaunchTrial).where(LaunchTrial.project_code == project.code, LaunchTrial.code == code)):
        raise HTTPException(409, "Launch trial code already exists")
    row = LaunchTrial(project_code=project.code, manufacturing_area=req.manufacturing_area, line_id=line_id, part_number=part_number,
                      code=code, trial_type=req.trial_type, title=req.title.strip(), owner=req.owner or identity.user, planned_at=_parse_iso_datetime(req.planned_at),
                      planned_quantity=req.planned_quantity, target_rate_per_hour=req.target_rate_per_hour, evidence_document_ids=evidence, notes=req.notes, created_by=identity.user)
    db.add(row); db.commit(); db.refresh(row)
    log_event(db, identity.user, "LAUNCH_TRIAL_CREATED", "project", project.code, {"id": row.id, "code": row.code, "type": row.trial_type, "area": row.manufacturing_area})
    return serialize_launch_trial(row, visible_doc_ids)

@router.patch("/projects/{project_code}/launch/trials/{trial_id}")
def update_launch_trial(project_code: str, trial_id: str, req: LaunchTrialUpdateRequest, identity: Identity = Depends(get_identity), db: Session = Depends(get_db)):
    project, visible_doc_ids, visible_parts, _ = _launch_project_context(db, project_code, identity)
    row = db.get(LaunchTrial, trial_id)
    if not row or row.project_code != project.code or (row.part_number and row.part_number not in visible_parts):
        raise HTTPException(404, "Launch trial not found")
    _validate_quality_area(db, project, identity, row.manufacturing_area)
    values = req.model_dump(exclude_unset=True)
    for key in ("planned_at", "completed_at"):
        if key in values: values[key] = _parse_iso_datetime(values[key])
    if values.get("status") in {"passed", "failed"} and "completed_at" not in values:
        values["completed_at"] = datetime.now().astimezone()
    if "evidence_document_ids" in values: values["evidence_document_ids"] = _validate_quality_evidence(db, project, visible_doc_ids, values["evidence_document_ids"])
    if "result" in values: values["result_json"] = values.pop("result")
    for key, value in values.items(): setattr(row, key, value)
    db.commit(); db.refresh(row)
    log_event(db, identity.user, "LAUNCH_TRIAL_UPDATED", "project", project.code, {"id": row.id, "fields": sorted(values), "status": row.status})
    return serialize_launch_trial(row, visible_doc_ids)

@router.get("/projects/{project_code}/build-launch-intelligence")
def get_build_launch_intelligence(project_code: str, manufacturing_area: str | None = None, vehicle_identifier: str | None = None, identity: Identity = Depends(get_identity), db: Session = Depends(get_db)):
    project, visible_doc_ids, visible_parts, allowed_areas = _launch_project_context(db, project_code, identity, manufacturing_area)
    return vehicle_build_launch_workspace(db, project.code, visible_doc_ids, visible_parts, manufacturing_area, allowed_areas, vehicle_identifier)

@router.post("/projects/{project_code}/build-launch-intelligence/builds")
def create_vehicle_build(project_code: str, req: VehicleBuildCreateRequest, identity: Identity = Depends(get_identity), db: Session = Depends(get_db)):
    _assurance_admin(identity)
    project, visible_doc_ids, visible_parts, _ = _launch_project_context(db, project_code, identity, req.manufacturing_area)
    _validate_quality_area(db, project, identity, req.manufacturing_area)
    if req.variant_id: _get_variant(db, project, req.variant_id, identity, visible_doc_ids)
    if req.line_id:
        line=db.get(ManufacturingLine, req.line_id)
        if not line or line.project_code!=project.code: raise HTTPException(404, "Manufacturing line not found")
    if req.release_baseline_id:
        base=db.get(ReleaseBaseline, req.release_baseline_id)
        if not base or base.project_code!=project.code: raise HTTPException(404, "Release baseline not found")
    evidence=_validate_quality_evidence(db,project,visible_doc_ids,req.evidence_document_ids)
    row=VehicleBuild(project_code=project.code,manufacturing_area=req.manufacturing_area,code=req.code.upper(),vehicle_identifier=req.vehicle_identifier,variant_id=req.variant_id,plant=req.plant,line_id=req.line_id,build_type=req.build_type,build_sequence=req.build_sequence,planned_at=_parse_iso_datetime(req.planned_at),completed_at=_parse_iso_datetime(req.completed_at),status=req.status,release_baseline_id=req.release_baseline_id,evidence_document_ids=evidence,notes=req.notes,metadata_json=req.metadata,created_by=identity.user)
    db.add(row)
    try: db.commit()
    except Exception as exc: db.rollback(); raise HTTPException(409, "Build code or vehicle identifier already exists") from exc
    db.refresh(row); log_event(db,identity.user,"VEHICLE_BUILD_CREATED","project",project.code,{"build_id":row.id,"code":row.code,"vehicle_identifier":row.vehicle_identifier})
    return serialize_build(row)

@router.post("/projects/{project_code}/build-launch-intelligence/builds/{build_id}/genealogy")
def add_build_genealogy(project_code: str, build_id: str, req: BuildGenealogyCreateRequest, identity: Identity = Depends(get_identity), db: Session = Depends(get_db)):
    _assurance_admin(identity)
    project, visible_doc_ids, visible_parts, _ = _launch_project_context(db, project_code, identity, req.manufacturing_area)
    build=db.get(VehicleBuild,build_id)
    if not build or build.project_code!=project.code: raise HTTPException(404,"Build not found")
    pn=req.part_number.strip().upper()
    if pn not in visible_parts: raise HTTPException(404,"Part not found")
    evidence=_validate_quality_evidence(db,project,visible_doc_ids,req.evidence_document_ids)
    row=BuildGenealogyItem(build_id=build.id,manufacturing_area=req.manufacturing_area,part_number=pn,revision=req.revision,supplier_code=req.supplier_code,lot_number=req.lot_number,serial_number=req.serial_number,quantity=req.quantity,installed_at=_parse_iso_datetime(req.installed_at),source_system=req.source_system,evidence_document_ids=evidence,metadata_json=req.metadata,created_by=identity.user)
    db.add(row)
    try: db.commit()
    except Exception as exc: db.rollback(); raise HTTPException(409,"Genealogy item already exists") from exc
    db.refresh(row); return serialize_genealogy(row)

@router.post("/projects/{project_code}/build-launch-intelligence/builds/{build_id}/defects")
def link_build_defect(project_code: str, build_id: str, req: BuildDefectLinkCreateRequest, identity: Identity = Depends(get_identity), db: Session = Depends(get_db)):
    _assurance_admin(identity)
    project, visible_doc_ids, visible_parts, _ = _launch_project_context(db, project_code, identity)
    build=db.get(VehicleBuild,build_id); defect=db.get(ProcessDefect,req.defect_id)
    if not build or build.project_code!=project.code: raise HTTPException(404,"Build not found")
    if not defect or defect.project_code!=project.code or (defect.part_number and defect.part_number.upper() not in visible_parts) or not set(defect.evidence_document_ids or []).issubset(visible_doc_ids): raise HTTPException(404,"Defect not found")
    evidence=_validate_quality_evidence(db,project,visible_doc_ids,req.evidence_document_ids)
    row=BuildDefectLink(build_id=build.id,defect_id=defect.id,detection_stage=req.detection_stage,containment_status=req.containment_status,evidence_document_ids=evidence,notes=req.notes,created_by=identity.user)
    db.add(row)
    try: db.commit()
    except Exception as exc: db.rollback(); raise HTTPException(409,"Defect already linked to build") from exc
    return {"id":row.id,"build_id":build.id,"defect_id":defect.id,"linked":True}

@router.post("/projects/{project_code}/build-launch-intelligence/safe-launch")
def create_safe_launch_control(project_code: str, req: SafeLaunchControlCreateRequest, identity: Identity = Depends(get_identity), db: Session = Depends(get_db)):
    _assurance_admin(identity)
    project, visible_doc_ids, visible_parts, _ = _launch_project_context(db, project_code, identity, req.manufacturing_area)
    _validate_quality_area(db,project,identity,req.manufacturing_area)
    pn=req.part_number.strip().upper() if req.part_number else None
    if pn and pn not in visible_parts: raise HTTPException(404,"Part not found")
    evidence=_validate_quality_evidence(db,project,visible_doc_ids,req.evidence_document_ids)
    row=SafeLaunchControl(project_code=project.code,manufacturing_area=req.manufacturing_area,code=req.code.upper(),part_number=pn,supplier_code=req.supplier_code,characteristic=req.characteristic,status=req.status,inspected_quantity=req.inspected_quantity,defect_quantity=req.defect_quantity,consecutive_clean_builds=req.consecutive_clean_builds,required_clean_builds=req.required_clean_builds,required_inspected_quantity=req.required_inspected_quantity,exit_criteria_json=req.exit_criteria,evidence_document_ids=evidence,notes=req.notes,metadata_json=req.metadata,created_by=identity.user)
    if req.status=="exited" and not serialize_safe_launch(row)["exit_candidate"]: raise HTTPException(400,"Safe Launch exit criteria are not satisfied")
    db.add(row)
    try: db.commit()
    except Exception as exc: db.rollback(); raise HTTPException(409,"Safe Launch control code already exists") from exc
    db.refresh(row); return serialize_safe_launch(row)

@router.patch("/projects/{project_code}/build-launch-intelligence/safe-launch/{control_id}")
def update_safe_launch_control(project_code: str, control_id: str, req: SafeLaunchControlUpdateRequest, identity: Identity = Depends(get_identity), db: Session = Depends(get_db)):
    _assurance_admin(identity)
    project, visible_doc_ids, visible_parts, _ = _launch_project_context(db, project_code, identity)
    row=db.get(SafeLaunchControl,control_id)
    if not row or row.project_code!=project.code or (row.part_number and row.part_number.upper() not in visible_parts): raise HTTPException(404,"Safe Launch control not found")
    values=req.model_dump(exclude_unset=True)
    if "evidence_document_ids" in values: values["evidence_document_ids"]=_validate_quality_evidence(db,project,visible_doc_ids,values["evidence_document_ids"])
    for k,v in values.items(): setattr(row,k,v)
    candidate=serialize_safe_launch(row)
    if row.status=="exited" and candidate["exit_gaps"]: db.rollback(); raise HTTPException(400,"Safe Launch exit criteria are not satisfied")
    db.commit(); db.refresh(row); log_event(db,identity.user,"SAFE_LAUNCH_UPDATED","project",project.code,{"control_id":row.id,"status":row.status})
    return serialize_safe_launch(row)

@router.get("/projects/{project_code}/series-intelligence")
def get_series_intelligence(project_code: str, manufacturing_area: str | None = None, identity: Identity = Depends(get_identity), db: Session = Depends(get_db)):
    project, visible_doc_ids, visible_parts, allowed_areas = _launch_project_context(db, project_code, identity, manufacturing_area)
    return series_quality_workspace(db, project.code, visible_doc_ids, visible_parts, manufacturing_area, allowed_areas)

@router.post("/projects/{project_code}/series-intelligence/ask")
def ask_series_intelligence(project_code: str, req: SeriesIntelligenceAskRequest, identity: Identity = Depends(get_identity), db: Session = Depends(get_db)):
    project, visible_doc_ids, visible_parts, allowed_areas = _launch_project_context(db, project_code, identity, req.manufacturing_area)
    ws=series_quality_workspace(db, project.code, visible_doc_ids, visible_parts, req.manufacturing_area, allowed_areas)
    return series_intelligence_answer(ws, req.query)

@router.post("/projects/{project_code}/series-intelligence/observations")
def create_series_observation(project_code: str, req: SeriesQualityObservationCreateRequest, identity: Identity = Depends(get_identity), db: Session = Depends(get_db)):
    _assurance_admin(identity)
    project, visible_doc_ids, visible_parts, _ = _launch_project_context(db, project_code, identity, req.manufacturing_area)
    _validate_quality_area(db,project,identity,req.manufacturing_area)
    pn=_validate_quality_part(req.part_number,visible_parts)
    if req.variant_id: _get_variant(db,project,req.variant_id,identity,visible_doc_ids)
    if req.line_id:
        line=db.get(ManufacturingLine,req.line_id)
        if not line or line.project_code!=project.code: raise HTTPException(404,"Manufacturing line not found")
    if req.station_id:
        station=db.get(ProcessStation,req.station_id)
        if not station: raise HTTPException(404,"Station not found")
    if req.operation_id:
        _validate_process_operation_ref(db,project,identity,visible_parts,req.operation_id,req.manufacturing_area)
    evidence=_validate_quality_evidence(db,project,visible_doc_ids,req.evidence_document_ids)
    row=SeriesQualityObservation(project_code=project.code,manufacturing_area=req.manufacturing_area,plant=req.plant,line_id=req.line_id,station_id=req.station_id,operation_id=req.operation_id,shift_code=req.shift_code,variant_id=req.variant_id,part_number=pn,revision=req.revision,supplier_code=req.supplier_code,supplier_lot=req.supplier_lot,defect_code=req.defect_code,characteristic=req.characteristic,produced_quantity=req.produced_quantity,inspected_quantity=req.inspected_quantity,defect_quantity=req.defect_quantity,detected_in_process_quantity=req.detected_in_process_quantity,escaped_quantity=req.escaped_quantity,scrap_cost=req.scrap_cost,rework_cost=req.rework_cost,containment_cost=req.containment_cost,warranty_cost_estimate=req.warranty_cost_estimate,currency=req.currency.upper(),observed_at=_parse_iso_datetime(req.observed_at) or datetime.now().astimezone(),period_key=req.period_key,source_system=req.source_system,evidence_document_ids=evidence,metadata_json=req.metadata,created_by=identity.user)
    db.add(row); db.commit(); db.refresh(row)
    log_event(db,identity.user,"SERIES_QUALITY_OBSERVATION_IMPORTED","project",project.code,{"id":row.id,"part_number":pn,"defects":row.defect_quantity,"area":row.manufacturing_area})
    return serialize_series_observation(row)

@router.post("/projects/{project_code}/series-intelligence/capability")
def create_process_capability(project_code: str, req: ProcessCapabilityCreateRequest, identity: Identity = Depends(get_identity), db: Session = Depends(get_db)):
    _assurance_admin(identity)
    project, visible_doc_ids, visible_parts, _ = _launch_project_context(db, project_code, identity, req.manufacturing_area)
    _validate_quality_area(db,project,identity,req.manufacturing_area)
    pn=_validate_quality_part(req.part_number,visible_parts)
    if req.operation_id: _validate_process_operation_ref(db,project,identity,visible_parts,req.operation_id,req.manufacturing_area)
    if req.asset_id:
        asset=db.get(ProcessAsset,req.asset_id)
        if not asset: raise HTTPException(404,"Process asset not found")
        if req.operation_id and asset.operation_id!=req.operation_id: raise HTTPException(400,"Asset belongs to another operation")
    evidence=_validate_quality_evidence(db,project,visible_doc_ids,req.evidence_document_ids)
    row=ProcessCapabilityRecord(project_code=project.code,manufacturing_area=req.manufacturing_area,plant=req.plant,line_id=req.line_id,station_id=req.station_id,operation_id=req.operation_id,asset_id=req.asset_id,part_number=pn,supplier_code=req.supplier_code,characteristic=req.characteristic,unit=req.unit,sample_size=req.sample_size,mean_value=req.mean_value,sigma_value=req.sigma_value,lower_spec_limit=req.lower_spec_limit,upper_spec_limit=req.upper_spec_limit,cp=req.cp,cpk=req.cpk,pp=req.pp,ppk=req.ppk,measured_at=_parse_iso_datetime(req.measured_at) or datetime.now().astimezone(),source_system=req.source_system,evidence_document_ids=evidence,metadata_json=req.metadata,created_by=identity.user)
    db.add(row); db.commit(); db.refresh(row)
    log_event(db,identity.user,"PROCESS_CAPABILITY_IMPORTED","project",project.code,{"id":row.id,"characteristic":row.characteristic,"cpk":row.cpk})
    return serialize_capability(row)

@router.post("/projects/{project_code}/series-intelligence/suspect-population")
def build_suspect_population(project_code: str, req: SuspectPopulationRequest, identity: Identity = Depends(get_identity), db: Session = Depends(get_db)):
    project, visible_doc_ids, visible_parts, allowed_areas = _launch_project_context(db, project_code, identity, req.manufacturing_area)
    if req.part_number and req.part_number.upper() not in {x.upper() for x in visible_parts if x}: raise HTTPException(404,"Part not found")
    criteria=req.model_dump(exclude={"manufacturing_area","max_results"})
    criteria["part_number"]=(req.part_number.upper() if req.part_number else None)
    criteria["built_from"]=_parse_iso_datetime(req.built_from) if req.built_from else None
    criteria["built_to"]=_parse_iso_datetime(req.built_to) if req.built_to else None
    return suspect_population(db,project.code,visible_doc_ids,visible_parts,allowed_areas,criteria,req.manufacturing_area,req.max_results)

@router.post("/projects/{project_code}/series-intelligence/containments")
def create_series_containment(project_code: str, req: SeriesContainmentCreateRequest, identity: Identity = Depends(get_identity), db: Session = Depends(get_db)):
    _assurance_admin(identity)
    project, visible_doc_ids, visible_parts, _ = _launch_project_context(db, project_code, identity, req.manufacturing_area)
    _validate_quality_area(db,project,identity,req.manufacturing_area)
    pn=_validate_quality_part(req.part_number,visible_parts)
    if req.linked_8d_id:
        eight=db.get(Problem8D,req.linked_8d_id)
        if not eight or eight.project_code!=project.code or not set(eight.evidence_document_ids or []).issubset(visible_doc_ids): raise HTTPException(404,"8D not found")
    evidence=_validate_quality_evidence(db,project,visible_doc_ids,req.evidence_document_ids)
    row=SeriesContainmentCase(project_code=project.code,manufacturing_area=req.manufacturing_area,code=req.code.upper(),title=req.title,part_number=pn,defect_code=req.defect_code,supplier_code=req.supplier_code,supplier_lot=req.supplier_lot,status=req.status,suspect_criteria_json=req.suspect_criteria,suspect_vehicle_identifiers=list(dict.fromkeys(req.suspect_vehicle_identifiers)),inspected_quantity=req.inspected_quantity,defect_quantity=req.defect_quantity,actions_json=req.actions,linked_8d_id=req.linked_8d_id,evidence_document_ids=evidence,notes=req.notes,metadata_json=req.metadata,created_by=identity.user)
    db.add(row)
    try: db.commit()
    except Exception as exc: db.rollback(); raise HTTPException(409,"Containment code already exists") from exc
    db.refresh(row); log_event(db,identity.user,"SERIES_CONTAINMENT_CREATED","project",project.code,{"id":row.id,"code":row.code,"status":row.status})
    return serialize_containment(row)

@router.patch("/projects/{project_code}/series-intelligence/containments/{containment_id}")
def update_series_containment(project_code: str, containment_id: str, req: SeriesContainmentUpdateRequest, identity: Identity = Depends(get_identity), db: Session = Depends(get_db)):
    _assurance_admin(identity)
    project, visible_doc_ids, visible_parts, allowed_areas = _launch_project_context(db, project_code, identity)
    row=db.get(SeriesContainmentCase,containment_id)
    if not row or row.project_code!=project.code or (row.manufacturing_area and row.manufacturing_area not in allowed_areas) or (row.part_number and row.part_number not in visible_parts) or not set(row.evidence_document_ids or []).issubset(visible_doc_ids): raise HTTPException(404,"Containment not found")
    values=req.model_dump(exclude_unset=True)
    if "evidence_document_ids" in values: values["evidence_document_ids"]=_validate_quality_evidence(db,project,visible_doc_ids,values["evidence_document_ids"])
    if "actions" in values: values["actions_json"]=values.pop("actions")
    if "suspect_vehicle_identifiers" in values: values["suspect_vehicle_identifiers"]=list(dict.fromkeys(values["suspect_vehicle_identifiers"] or []))
    if values.get("status")=="closed" and row.status!="closed": values["closed_at"]=datetime.now().astimezone()
    for k,v in values.items(): setattr(row,k,v)
    db.commit(); db.refresh(row); log_event(db,identity.user,"SERIES_CONTAINMENT_UPDATED","project",project.code,{"id":row.id,"fields":sorted(values),"status":row.status})
    return serialize_containment(row)



@router.patch("/projects/{project_code}/process/stations/{station_id}")
def update_process_station(project_code: str, station_id: str, req: ProcessStationUpdateRequest, identity: Identity = Depends(get_identity), db: Session = Depends(get_db)):
    project = _get_visible_project(db, project_code, identity)
    station, line = _process_station_context(db, project, identity, station_id)
    values = req.model_dump(exclude_unset=True)
    expected_version = values.pop("expected_version", None)
    require_expected_version(station, expected_version, "process_station")
    with UnitOfWork(db) as uow:
        for key, value in values.items():
            setattr(station, key, value)
        add_audit_event(db, identity.user, "PROCESS_STATION_UPDATED", "project", project.code, {"station_id": station.id, "line": line.code, "fields": sorted(values), "previous_version": station.row_version})
        uow.commit()
    db.refresh(station)
    return serialize_station(station)


def _wi_hierarchy(db: Session, project: Project, identity: Identity, visible_parts: set[str], manufacturing_area: str, line_id: str | None, station_id: str | None, operation_id: str | None):
    line = station = operation = None
    if operation_id:
        operation, station, line = _process_operation_context(db, project, identity, visible_parts, operation_id)
        if station_id and station.id != station_id:
            raise HTTPException(400, "Operation belongs to another station")
        if line_id and line.id != line_id:
            raise HTTPException(400, "Operation belongs to another line")
    elif station_id:
        station, line = _process_station_context(db, project, identity, station_id)
        if line_id and line.id != line_id:
            raise HTTPException(400, "Station belongs to another line")
    elif line_id:
        line = _process_line_context(db, project, identity, line_id)
    if line and line.manufacturing_area != manufacturing_area:
        raise HTTPException(400, "Line/station/operation belongs to another manufacturing area")
    return line, station, operation


@router.get("/projects/{project_code}/work-instructions")
def get_work_instruction_workspace(project_code: str, manufacturing_area: str, request: Request, response: Response, identity: Identity = Depends(get_identity), db: Session = Depends(get_db)):
    from app.services.read_models import acl_fingerprint, cache_key, etag_for_payload, get_wi_coverage_read_model, pending_read_model_invalidation, redis_cache_get, redis_cache_set
    project, visible_doc_ids, _ = _quality_project_context(db, project_code, identity, manufacturing_area)
    cfg=get_settings(); pending=pending_read_model_invalidation(db); identity_key=acl_fingerprint(visible_doc_ids, identity.groups)
    key=cache_key("wi_workspace",identity_key,project.code,manufacturing_area)
    payload=None if pending else redis_cache_get(key,surface="wi_workspace")
    cache_state="redis_hit" if payload is not None else ("bypass_pending_invalidation" if pending else "miss")
    if payload is None:
        payload=work_instruction_workspace(db,project.code,manufacturing_area,visible_doc_ids)
        payload["read_model"] = get_wi_coverage_read_model(db, project.code, manufacturing_area)
        if not pending: redis_cache_set(key,payload,ttl=cfg.read_model_cache_ttl_seconds,surface="wi_workspace")
    etag=etag_for_payload(payload); headers={"ETag":etag,"Cache-Control":"private, no-cache","X-MGC-Cache":cache_state}
    if request.headers.get("if-none-match") == etag: return Response(status_code=304,headers=headers)
    response.headers.update(headers)
    return payload


@router.post("/projects/{project_code}/work-instructions")
def create_work_instruction(project_code: str, req: WorkInstructionCreateRequest, identity: Identity = Depends(get_identity), db: Session = Depends(get_db)):
    project, visible_doc_ids, visible_parts = _quality_project_context(db, project_code, identity, req.manufacturing_area)
    _validate_quality_area(db, project, identity, req.manufacturing_area)
    line, station, operation = _wi_hierarchy(db, project, identity, visible_parts, req.manufacturing_area, req.line_id, req.station_id, req.operation_id)
    source_document_id = None
    if req.source_document_id:
        source_document_id = _validate_quality_evidence(db, project, visible_doc_ids, [req.source_document_id])[0]
    evidence = _validate_quality_evidence(db, project, visible_doc_ids, req.evidence_document_ids)
    code = req.code.upper(); revision = req.revision.upper()
    if db.scalar(select(WorkInstruction).where(WorkInstruction.project_code == project.code, WorkInstruction.code == code, WorkInstruction.revision == revision)):
        raise HTTPException(409, "Work instruction code/revision already exists")
    source_language = detect_instruction_language(req.original_text or "") if req.source_language == "auto" else req.source_language
    if source_language == "auto": source_language = "ru"
    row = WorkInstruction(
        project_code=project.code, manufacturing_area=req.manufacturing_area, line_id=line.id if line else req.line_id,
        station_id=station.id if station else req.station_id, operation_id=operation.id if operation else req.operation_id,
        code=code, title=req.title.strip(), revision=revision, instruction_type=req.instruction_type,
        source_type="imported" if source_document_id else "authored", source_language=source_language,
        source_factory=req.source_factory, source_document_id=source_document_id, original_text=req.original_text,
        translation_status="not_required" if source_language == "ru" else "pending",
        steps_json=[x.model_dump() for x in req.steps], safety_points_json=req.safety_points, quality_points_json=req.quality_points,
        tools_json=req.tools, ppe_json=req.ppe, required_skill=req.required_skill, operator_role=req.operator_role,
        cycle_time_sec=req.cycle_time_sec, owner=req.owner or identity.user, created_by=identity.user,
        evidence_document_ids=list(dict.fromkeys(([source_document_id] if source_document_id else []) + evidence)), metadata_json=req.metadata,
    )
    with UnitOfWork(db) as uow:
        db.add(row); db.flush()
        add_audit_event(db, identity.user, "WORK_INSTRUCTION_CREATED", "work_instruction", row.id, {"project": project.code, "area": row.manufacturing_area, "station_id": row.station_id, "code": row.code, "revision": row.revision, "row_version": row.row_version})
        uow.commit()
    db.refresh(row)
    return serialize_work_instruction(row, visible_doc_ids)


@router.post("/projects/{project_code}/work-instructions/import-document")
def import_work_instruction(project_code: str, req: WorkInstructionImportRequest, identity: Identity = Depends(get_identity), db: Session = Depends(get_db)):
    project, visible_doc_ids, visible_parts = _quality_project_context(db, project_code, identity, req.manufacturing_area)
    _validate_quality_area(db, project, identity, req.manufacturing_area)
    line, station, operation = _wi_hierarchy(db, project, identity, visible_parts, req.manufacturing_area, req.line_id, req.station_id, req.operation_id)
    document_id = _validate_quality_evidence(db, project, visible_doc_ids, [req.document_id])[0]
    doc = db.get(Document, document_id)
    code = req.code.upper(); revision = req.revision.upper()
    if db.scalar(select(WorkInstruction).where(WorkInstruction.project_code == project.code, WorkInstruction.code == code, WorkInstruction.revision == revision)):
        raise HTTPException(409, "Work instruction code/revision already exists")
    try:
        text, parse_meta, steps = import_work_instruction_document(db, doc)
    except Exception as exc:
        raise HTTPException(422, f"Instruction document cannot be parsed locally: {type(exc).__name__}") from exc
    source_language = detect_instruction_language(text) if req.source_language == "auto" else req.source_language
    row = WorkInstruction(
        project_code=project.code, manufacturing_area=req.manufacturing_area, line_id=line.id if line else req.line_id,
        station_id=station.id if station else req.station_id, operation_id=operation.id if operation else req.operation_id,
        code=code, title=req.title.strip(), revision=revision, instruction_type=req.instruction_type, source_type="partner_document",
        source_language=source_language, source_factory=req.source_factory, source_document_id=doc.id, original_text=text,
        translation_status="not_required" if source_language == "ru" else "pending", steps_json=steps,
        owner=req.owner or identity.user, created_by=identity.user, evidence_document_ids=[doc.id],
        metadata_json={"import_parser": parse_meta, "source_filename": doc.filename},
    )
    with UnitOfWork(db) as uow:
        db.add(row); db.flush()
        add_audit_event(db, identity.user, "WORK_INSTRUCTION_IMPORTED", "work_instruction", row.id, {"document_id": doc.id, "source_language": source_language, "area": row.manufacturing_area, "row_version": row.row_version})
        uow.commit()
    db.refresh(row)
    return serialize_work_instruction(row, visible_doc_ids)


@router.patch("/projects/{project_code}/work-instructions/{instruction_id}")
def update_work_instruction(project_code: str, instruction_id: str, req: WorkInstructionUpdateRequest, identity: Identity = Depends(get_identity), db: Session = Depends(get_db), idempotency_key: str | None = Header(default=None, alias="Idempotency-Key")):
    project, visible_doc_ids, visible_parts = _quality_project_context(db, project_code, identity)
    row = db.get(WorkInstruction, instruction_id)
    if not row or row.project_code != project.code:
        raise HTTPException(404)
    _validate_quality_area(db, project, identity, row.manufacturing_area)
    if row.source_document_id and row.source_document_id not in visible_doc_ids:
        raise HTTPException(404)
    request_payload = req.model_dump(mode="json", exclude_unset=True)
    route_key = f"PATCH:work_instruction:{instruction_id}"
    try:
        replay = idempotency_lookup(db, user=identity.user, route_key=route_key, key=idempotency_key, request_payload=request_payload)
    except ValueError as exc:
        raise HTTPException(409, str(exc))
    if replay is not None:
        return replay
    values = req.model_dump(exclude_unset=True)
    expected_version = values.pop("expected_version", None)
    require_expected_version(row, expected_version, "work_instruction")
    previous_version = row.row_version
    if row.status == "approved":
        non_status_changes = set(values) - {"status"}
        requested_status = values.get("status", "approved")
        if requested_status == "approved" and not non_status_changes:
            raise HTTPException(409, "Work instruction revision is already approved; duplicate approval is blocked")
        if non_status_changes or requested_status not in {"approved", "obsolete"}:
            raise HTTPException(409, "Approved work instruction is immutable; create a new revision or obsolete the approved revision")
    source_content_changed = any(k in values for k in ("original_text", "steps", "source_language"))
    if any(k in values for k in ("line_id", "station_id", "operation_id")):
        line_id = values.get("line_id", row.line_id); station_id = values.get("station_id", row.station_id); operation_id = values.get("operation_id", row.operation_id)
        line, station, operation = _wi_hierarchy(db, project, identity, visible_parts, row.manufacturing_area, line_id, station_id, operation_id)
        values["line_id"] = line.id if line else line_id; values["station_id"] = station.id if station else station_id; values["operation_id"] = operation.id if operation else operation_id
    if "status" in values and values["status"] == "approved":
        if not _is_admin(identity):
            raise HTTPException(403, "Engineering Admin approval required")
        if not get_settings().allow_legacy_direct_wi_approval:
            raise HTTPException(409, "Direct work-instruction approval is disabled; use the controlled approval workflow")
        if resolve_governance_policy(db, "work_instruction", row.project_code, row.manufacturing_area):
            raise HTTPException(409, "Configured approval policy is active; submit this work instruction through the controlled approval workflow")
        if row.source_language not in {"ru", "auto"}:
            if row.translation_status != "reviewed" or not translation_is_current(row):
                raise HTTPException(409, "Current reviewed Russian translation is required before approval")
        candidate_steps = values.get("steps", row.steps_json or [])
        if not row.station_id and not values.get("station_id"):
            raise HTTPException(409, "Approved work instruction must be linked to a station")
        if not candidate_steps:
            raise HTTPException(409, "Approved work instruction must contain explicit steps")
        row.approved_by = identity.user
    mapping = {"steps": "steps_json", "safety_points":"safety_points_json", "quality_points":"quality_points_json", "tools":"tools_json", "ppe":"ppe_json", "metadata":"metadata_json"}
    for key, value in values.items():
        target = mapping.get(key, key)
        if key == "steps" and value is not None:
            value = [x.model_dump() if hasattr(x, "model_dump") else x for x in value]
        setattr(row, target, value)
    if source_content_changed:
        if row.source_language in {"ru", "auto"}:
            row.translation_status = "not_required"
        elif row.translation_status in {"draft", "reviewed", "rejected", "stale"} and not translation_is_current(row):
            row.translation_status = "stale"
            row.metadata_json = {
                **(row.metadata_json or {}),
                "translation_stale": True,
                "translation_stale_reason": "source_content_changed",
            }
    with UnitOfWork(db) as uow:
        add_audit_event(db, identity.user, "WORK_INSTRUCTION_UPDATED", "work_instruction", row.id, {"fields": sorted(values), "status": row.status, "previous_version": previous_version})
        db.flush()
        response_payload = serialize_work_instruction(row, visible_doc_ids)
        store_idempotency(db, user=identity.user, route_key=route_key, key=idempotency_key, request_payload=request_payload, response=response_payload, entity_type="work_instruction", entity_id=row.id)
        record_revision_snapshot(db, row, "work_instruction", user=identity.user, reason="updated")
        uow.commit()
    db.refresh(row)
    return response_payload


@router.post("/projects/{project_code}/work-instructions/{instruction_id}/revisions")
def create_work_instruction_revision(project_code: str, instruction_id: str, req: WorkInstructionRevisionCreateRequest, idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"), identity: Identity = Depends(get_identity), db: Session = Depends(get_db)):
    project, visible_doc_ids, _ = _quality_project_context(db, project_code, identity)
    source = db.get(WorkInstruction, instruction_id)
    if not source or source.project_code != project.code:
        raise HTTPException(404)
    _validate_quality_area(db, project, identity, source.manufacturing_area)
    if source.source_document_id and source.source_document_id not in visible_doc_ids:
        raise HTTPException(404)
    require_expected_version(source, req.expected_version, "work_instruction")
    if source.status not in {"approved", "obsolete"}:
        raise HTTPException(409, "Create a controlled revision from an approved or obsolete work instruction")
    new_revision = req.new_revision.strip().upper()
    if db.scalar(select(WorkInstruction).where(WorkInstruction.project_code == project.code, WorkInstruction.code == source.code, WorkInstruction.revision == new_revision)):
        raise HTTPException(409, "Work instruction revision already exists")
    payload = req.model_dump(mode="json")
    route_key = f"POST:work_instruction_revision:{instruction_id}"
    try:
        replay = idempotency_lookup(db, user=identity.user, route_key=route_key, key=idempotency_key, request_payload=payload)
    except ValueError as exc:
        raise HTTPException(409, str(exc))
    if replay is not None:
        return replay
    with UnitOfWork(db) as uow:
        row = clone_work_instruction_revision(db, source, new_revision=new_revision, user=identity.user, reason=req.reason.strip())
        add_audit_event(db, identity.user, "WORK_INSTRUCTION_REVISION_CREATED", "work_instruction", row.id, {"source_id": source.id, "from_revision": source.revision, "to_revision": row.revision, "reason": req.reason})
        db.flush()
        response_payload = serialize_work_instruction(row, visible_doc_ids)
        store_idempotency(db, user=identity.user, route_key=route_key, key=idempotency_key, request_payload=payload, response=response_payload, entity_type="work_instruction", entity_id=row.id)
        uow.commit()
    return response_payload


@router.get("/projects/{project_code}/work-instructions/{instruction_id}/diff")
def diff_work_instruction_revisions(project_code: str, instruction_id: str, other_id: str, identity: Identity = Depends(get_identity), db: Session = Depends(get_db)):
    project, visible_doc_ids, _ = _quality_project_context(db, project_code, identity)
    left, right = db.get(WorkInstruction, instruction_id), db.get(WorkInstruction, other_id)
    if not left or not right or left.project_code != project.code or right.project_code != project.code or left.code != right.code:
        raise HTTPException(404)
    for row in (left, right):
        _validate_quality_area(db, project, identity, row.manufacturing_area)
        if row.source_document_id and row.source_document_id not in visible_doc_ids:
            raise HTTPException(404)
    return work_instruction_visual_diff(left, right)


@router.post("/projects/{project_code}/work-instructions/{instruction_id}/translate")
async def translate_work_instruction_to_russian(project_code: str, instruction_id: str, req: EngineeringTranslationRequest, identity: Identity = Depends(get_identity), db: Session = Depends(get_db)):
    if req.target_language != "ru":
        raise HTTPException(400, "Work instructions are operationally normalized to Russian; use BOM translation for other view languages")
    project, visible_doc_ids, _ = _quality_project_context(db, project_code, identity)
    row = db.get(WorkInstruction, instruction_id)
    if not row or row.project_code != project.code:
        raise HTTPException(404)
    _validate_quality_area(db, project, identity, row.manufacturing_area)
    if row.source_document_id and row.source_document_id not in visible_doc_ids:
        raise HTTPException(404)
    require_expected_version(row, req.expected_version, "work_instruction")
    previous_version = row.row_version
    result = await translate_work_instruction(db, row, user=identity.user, force=req.force, commit=False)
    with UnitOfWork(db) as uow:
        add_audit_event(db, identity.user, "WORK_INSTRUCTION_TRANSLATED", "work_instruction", row.id, {"status": result.get("status"), "target_language": "ru", "previous_version": previous_version})
        uow.commit()
    db.refresh(row)
    return {"translation": {k:v for k,v in result.items() if k != "instruction"}, "instruction": serialize_work_instruction(row, visible_doc_ids)}


@router.post("/projects/{project_code}/work-instructions/{instruction_id}/translation-review")
def review_work_instruction_translation(project_code: str, instruction_id: str, req: TranslationReviewRequest, identity: Identity = Depends(get_identity), db: Session = Depends(get_db)):
    if not _is_admin(identity):
        raise HTTPException(403, "Engineering Admin translation review required")
    project, visible_doc_ids, _ = _quality_project_context(db, project_code, identity)
    row = db.get(WorkInstruction, instruction_id)
    if not row or row.project_code != project.code:
        raise HTTPException(404)
    _validate_quality_area(db, project, identity, row.manufacturing_area)
    require_expected_version(row, req.expected_version, "work_instruction")
    if row.translation_status not in {"draft", "reviewed", "rejected"}:
        raise HTTPException(409, "No current translated draft is available for review")
    if not translation_is_current(row):
        row.translation_status = "stale"
        row.metadata_json = {**(row.metadata_json or {}), "translation_stale": True, "translation_stale_reason": "source_content_changed"}
        db.commit()
        raise HTTPException(409, "Translation is stale because the source instruction changed; translate again before review")
    previous_version = row.row_version
    row.translation_status = "reviewed" if req.decision == "approve" else "rejected"
    row.metadata_json = {**(row.metadata_json or {}), "translation_review": {"decision": req.decision, "reviewer": identity.user, "notes": req.notes}}
    with UnitOfWork(db) as uow:
        add_audit_event(db, identity.user, "WORK_INSTRUCTION_TRANSLATION_REVIEW", "work_instruction", row.id, {"decision": req.decision, "previous_version": previous_version})
        uow.commit()
    db.refresh(row)
    return serialize_work_instruction(row, visible_doc_ids)


@router.post("/projects/{project_code}/work-instructions/ask")
async def ask_work_instruction_knowledge(project_code: str, req: WorkInstructionAskRequest, identity: Identity = Depends(get_identity), db: Session = Depends(get_db)):
    project, visible_doc_ids, visible_parts = _quality_project_context(db, project_code, identity, req.manufacturing_area)
    _validate_quality_area(db, project, identity, req.manufacturing_area)
    if req.station_id:
        _process_station_context(db, project, identity, req.station_id)
    if req.operation_id:
        _process_operation_context(db, project, identity, visible_parts, req.operation_id)
    return await ask_work_instructions(db, project_code=project.code, manufacturing_area=req.manufacturing_area, visible_document_ids=visible_doc_ids,
                                       query=req.query, station_id=req.station_id, operation_id=req.operation_id, limit=req.limit)


@router.post("/projects/{project_code}/layouts")
def create_manufacturing_layout(project_code: str, req: ManufacturingLayoutCreateRequest, identity: Identity = Depends(get_identity), db: Session = Depends(get_db)):
    project, visible_doc_ids, _ = _quality_project_context(db, project_code, identity, req.manufacturing_area)
    _validate_quality_area(db, project, identity, req.manufacturing_area)
    line = _process_line_context(db, project, identity, req.line_id) if req.line_id else None
    if line and line.manufacturing_area != req.manufacturing_area:
        raise HTTPException(400, "Line belongs to another manufacturing area")
    source_document_id = None
    if req.source_document_id:
        source_document_id = _validate_quality_evidence(db, project, visible_doc_ids, [req.source_document_id])[0]
    code = req.code.upper(); revision = req.revision.upper()
    if db.scalar(select(ManufacturingLayout).where(ManufacturingLayout.project_code == project.code, ManufacturingLayout.code == code, ManufacturingLayout.revision == revision)):
        raise HTTPException(409, "Layout code/revision already exists")
    row = ManufacturingLayout(project_code=project.code, manufacturing_area=req.manufacturing_area, line_id=req.line_id,
                              code=code, title=req.title.strip(), revision=revision, source_document_id=source_document_id,
                              owner=req.owner or identity.user, created_by=identity.user, metadata_json=req.metadata)
    with UnitOfWork(db) as uow:
        db.add(row); db.flush()
        add_audit_event(db, identity.user, "MANUFACTURING_LAYOUT_CREATED", "layout", row.id, {"project": project.code, "area": row.manufacturing_area, "source_document_id": source_document_id, "row_version": row.row_version})
        uow.commit()
    db.refresh(row)
    return serialize_manufacturing_layout(row, visible_doc_ids, [])


@router.post("/projects/{project_code}/layouts/{layout_id}/revisions")
def create_layout_revision(project_code: str, layout_id: str, req: ManufacturingLayoutRevisionCreateRequest, idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"), identity: Identity = Depends(get_identity), db: Session = Depends(get_db)):
    project, visible_doc_ids, _ = _quality_project_context(db, project_code, identity)
    source = db.get(ManufacturingLayout, layout_id)
    if not source or source.project_code != project.code:
        raise HTTPException(404)
    _validate_quality_area(db, project, identity, source.manufacturing_area)
    if source.source_document_id and source.source_document_id not in visible_doc_ids:
        raise HTTPException(404)
    require_expected_version(source, req.expected_version, "manufacturing_layout")
    new_revision = req.new_revision.strip().upper()
    if db.scalar(select(ManufacturingLayout).where(ManufacturingLayout.project_code == project.code, ManufacturingLayout.code == source.code, ManufacturingLayout.revision == new_revision)):
        raise HTTPException(409, "Layout revision already exists")
    payload = req.model_dump(mode="json")
    route_key = f"POST:layout_revision:{layout_id}"
    try:
        replay = idempotency_lookup(db, user=identity.user, route_key=route_key, key=idempotency_key, request_payload=payload)
    except ValueError as exc:
        raise HTTPException(409, str(exc))
    if replay is not None:
        return replay
    with UnitOfWork(db) as uow:
        row, placements = clone_manufacturing_layout_revision(db, source, new_revision=new_revision, user=identity.user, reason=req.reason.strip())
        add_audit_event(db, identity.user, "MANUFACTURING_LAYOUT_REVISION_CREATED", "layout", row.id, {"source_id": source.id, "from_revision": source.revision, "to_revision": row.revision, "reason": req.reason})
        db.flush()
        response_payload = serialize_manufacturing_layout(row, visible_doc_ids, placements)
        store_idempotency(db, user=identity.user, route_key=route_key, key=idempotency_key, request_payload=payload, response=response_payload, entity_type="manufacturing_layout", entity_id=row.id)
        uow.commit()
    return response_payload


@router.get("/projects/{project_code}/layouts/{layout_id}/diff")
def diff_layout_revisions(project_code: str, layout_id: str, other_id: str, identity: Identity = Depends(get_identity), db: Session = Depends(get_db)):
    project, visible_doc_ids, _ = _quality_project_context(db, project_code, identity)
    left, right = db.get(ManufacturingLayout, layout_id), db.get(ManufacturingLayout, other_id)
    if not left or not right or left.project_code != project.code or right.project_code != project.code or left.code != right.code:
        raise HTTPException(404)
    for row in (left, right):
        _validate_quality_area(db, project, identity, row.manufacturing_area)
        if row.source_document_id and row.source_document_id not in visible_doc_ids:
            raise HTTPException(404)
    return manufacturing_layout_visual_diff(db, left, right)


@router.post("/projects/{project_code}/layouts/{layout_id}/stations")
def place_station_on_layout(project_code: str, layout_id: str, req: StationLayoutPlacementRequest, identity: Identity = Depends(get_identity), db: Session = Depends(get_db)):
    project, visible_doc_ids, _ = _quality_project_context(db, project_code, identity)
    layout = db.get(ManufacturingLayout, layout_id)
    if not layout or layout.project_code != project.code:
        raise HTTPException(404)
    _validate_quality_area(db, project, identity, layout.manufacturing_area)
    require_expected_version(layout, req.expected_layout_version, "manufacturing_layout")
    previous_layout_version = layout.row_version
    station, line = _process_station_context(db, project, identity, req.station_id)
    if line.manufacturing_area != layout.manufacturing_area:
        raise HTTPException(400, "Station belongs to another manufacturing area")
    if layout.line_id and line.id != layout.line_id:
        raise HTTPException(400, "Station belongs to another line")
    row = db.scalar(select(StationLayoutPlacement).where(StationLayoutPlacement.layout_id == layout.id, StationLayoutPlacement.station_id == station.id))
    if not row:
        row = StationLayoutPlacement(layout_id=layout.id, station_id=station.id); db.add(row)
    row.x_pct=req.x_pct; row.y_pct=req.y_pct; row.width_pct=req.width_pct; row.height_pct=req.height_pct; row.rotation_deg=req.rotation_deg; row.label_override=req.label_override; row.metadata_json=req.metadata
    layout.metadata_json = {**(layout.metadata_json or {}), "placement_revision": int((layout.metadata_json or {}).get("placement_revision", 0)) + 1}
    with UnitOfWork(db) as uow:
        add_audit_event(db, identity.user, "STATION_LAYOUT_PLACED", "layout", layout.id, {"station_id": station.id, "x_pct": row.x_pct, "y_pct": row.y_pct, "previous_version": previous_layout_version})
        uow.commit()
    db.refresh(layout); db.refresh(row)
    placements = db.scalars(select(StationLayoutPlacement).where(StationLayoutPlacement.layout_id == layout.id)).all()
    return serialize_manufacturing_layout(layout, visible_doc_ids, placements)
