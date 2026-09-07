"""Configuration Change HTTP handlers — v6.2.2.

Extracted from the former 3k-line route monolith. Public paths are unchanged.
"""
from fastapi import APIRouter
from app.api import context_shared as _shared

# Preserve the mature shared handler namespace without duplicating service imports.
globals().update({k: v for k, v in vars(_shared).items() if not k.startswith("__")})
from app.api.lazy_service import lazy_service
from app.db.unit_of_work import require_expected_version
from app.db.models import EngineeringReleasePackage, EngineeringHandoverJob, WorkInstruction, ManufacturingLayout, Document
from app.schemas.api import ReleasePackageCreateRequest, HandoverJobCreateRequest, HandoverAuthorizationRequest
from app.services.approval_governance import create_release_package, serialize_package, submit_package, release_package as release_engineering_package, release_manifest, decide_case, serialize_case
from app.services.identity_policy import apply_governance_rls_context, enforce_identity_policy
from app.services.engineering_handover import create_job as create_handover_job, authorize_job as authorize_handover_job, execute_job as execute_handover_job, reconcile_job as reconcile_handover_job, serialize_job as serialize_handover_job
from app.core.security import identity_snapshot

closed_loop_workspace = lazy_service("app.services.closed_loop_engineering", "closed_loop_workspace")
compare_bom_versions = lazy_service("app.services.release_baseline", "compare_bom_versions")
compare_digital_thread_baselines = lazy_service("app.services.change_intelligence", "compare_digital_thread_baselines")
complete_change = lazy_service("app.services.engineering_change", "complete_change")
configuration_assurance_answer = lazy_service("app.services.configuration_release_assurance", "configuration_assurance_answer")
configuration_impact = lazy_service("app.services.configuration_management", "configuration_impact")
configuration_release_assurance_workspace = lazy_service("app.services.configuration_release_assurance", "configuration_release_assurance_workspace")
configuration_workspace = lazy_service("app.services.configuration_management", "configuration_workspace")
create_change = lazy_service("app.services.engineering_change", "create_change")
create_release_baseline = lazy_service("app.services.release_baseline", "create_release_baseline")
decide_change = lazy_service("app.services.engineering_change", "decide_change")
defect_root_cause_explorer = lazy_service("app.services.closed_loop_engineering", "defect_root_cause_explorer")
list_bom_versions = lazy_service("app.services.release_baseline", "list_bom_versions")
log_document_activity = lazy_service("app.services.audit", "log_document_activity")
log_event = lazy_service("app.services.audit", "log_event")
release_package = lazy_service("app.services.configuration_release_assurance", "release_package")
release_workspace = lazy_service("app.services.release_baseline", "release_workspace")
risk_based_validation_plan = lazy_service("app.services.closed_loop_engineering", "risk_based_validation_plan")
run_change_impact = lazy_service("app.services.engineering_change", "run_change_impact")
serialize_applicability = lazy_service("app.services.configuration_management", "serialize_applicability")
serialize_as_built = lazy_service("app.services.configuration_release_assurance", "serialize_as_built")
serialize_change = lazy_service("app.services.engineering_change", "serialize_change")
serialize_cutin = lazy_service("app.services.configuration_release_assurance", "serialize_cutin")
serialize_decision = lazy_service("app.services.closed_loop_engineering", "serialize_decision")
serialize_deviation = lazy_service("app.services.closed_loop_engineering", "serialize_deviation")
serialize_effectiveness = lazy_service("app.services.closed_loop_engineering", "serialize_effectiveness")
serialize_effectivity = lazy_service("app.services.configuration_release_assurance", "serialize_effectivity")
serialize_feedback = lazy_service("app.services.closed_loop_engineering", "serialize_feedback")
serialize_mbom = lazy_service("app.services.configuration_release_assurance", "serialize_mbom")
serialize_release_baseline = lazy_service("app.services.release_baseline", "serialize_release_baseline")
serialize_risk = lazy_service("app.services.closed_loop_engineering", "serialize_risk")
serialize_supersession = lazy_service("app.services.configuration_release_assurance", "serialize_supersession")
serialize_variant = lazy_service("app.services.configuration_management", "serialize_variant")
start_implementation = lazy_service("app.services.engineering_change", "start_implementation")
submit_for_approval = lazy_service("app.services.engineering_change", "submit_for_approval")
valid_area = lazy_service("app.services.manufacturing_areas", "valid_area")
translate_bom = lazy_service("app.services.engineering_translation", "translate_bom")
from app.core.vehicle_applicability import merge_vehicle_profile, PROFILE_KEYS


router = APIRouter(tags=["context:configuration_change"])

@router.get("/changes")
def list_changes(manufacturing_area: str | None = None, identity: Identity = Depends(get_identity), db: Session = Depends(get_db)):
    if not valid_area(manufacturing_area): raise HTTPException(400, "Unknown manufacturing area")
    visible_parts = {d.part_number for d in _visible_docs_for_area(db, identity, manufacturing_area) if d.part_number}
    rows = db.scalars(select(ChangeRequest).order_by(ChangeRequest.updated_at.desc())).all()
    rows = [x for x in rows if not x.part_number or x.part_number in visible_parts]
    return [serialize_change(db, x) for x in rows]

@router.post("/changes")
def create_engineering_change(req: ChangeCreateRequest, identity: Identity = Depends(get_identity), db: Session = Depends(get_db)):
    try:
        change = create_change(
            db, title=req.title, description=req.description, reason=req.reason,
            part_number=req.part_number, from_revision=req.from_revision, to_revision=req.to_revision,
            priority=req.priority, user=identity.user, allowed_document_ids=_visible_ids(db, identity),
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc))
    log_event(db, identity.user, "ECR_CREATED", "change", change.id, {"code": change.code, "part_number": change.part_number})
    target_docs = [d for d in _visible_docs(db, identity) if d.part_number == change.part_number and d.revision in {change.from_revision, change.to_revision}]
    for doc in target_docs:
        log_document_activity(db, doc.id, identity.user, "ECR_CREATED", f"Создан запрос изменения {change.code}", {"change_id": change.id, "from_revision": change.from_revision, "to_revision": change.to_revision})
    return serialize_change(db, change, include_history=True)

@router.get("/changes/{change_id}")
def get_engineering_change(change_id: str, identity: Identity = Depends(get_identity), db: Session = Depends(get_db)):
    return _serialize_change_with_configuration(db, _get_visible_change(db, change_id, identity), identity, include_history=True)

@router.get("/changes/{change_id}/diff")
def get_engineering_change_diff(change_id: str, identity: Identity = Depends(get_identity), db: Session = Depends(get_db)):
    change = _get_visible_change(db, change_id, identity)
    visible = _visible_docs(db, identity)
    candidates = [d for d in visible if d.part_number == change.part_number and d.revision in {change.from_revision, change.to_revision} and str(getattr(d, "doc_type", "")).lower() == "bom"]
    left = [d for d in candidates if d.revision == change.from_revision]
    right = [d for d in candidates if d.revision == change.to_revision]
    base = {
        "change_id": change.id, "code": change.code, "eco_code": change.eco_code,
        "part_number": change.part_number, "from_revision": change.from_revision, "to_revision": change.to_revision,
        "change_fields": {
            "title": change.title, "reason": change.reason, "risk_level": change.risk_level,
            "status": change.status, "affected_parts": change.affected_parts or [],
        },
        "human_review_required": True, "auto_merge": False,
    }
    if len(left) == 1 and len(right) == 1:
        try:
            base["bom_diff"] = compare_bom_versions(db, change.metadata_json.get("project_code") if isinstance(change.metadata_json, dict) and change.metadata_json.get("project_code") else (left[0].project_code or right[0].project_code), _visible_ids(db, identity), left[0].id, right[0].id, change.part_number)
            base["bom_diff_status"] = "ready"
        except (ValueError, LookupError) as exc:
            base["bom_diff_status"] = "unavailable"; base["reason"] = str(exc)
    else:
        base["bom_diff_status"] = "candidate_selection_required"
        base["from_candidates"] = [{"id": d.id, "filename": d.filename, "revision": d.revision} for d in left]
        base["to_candidates"] = [{"id": d.id, "filename": d.filename, "revision": d.revision} for d in right]
    return base


@router.post("/changes/{change_id}/impact")
def analyze_engineering_change(change_id: str, identity: Identity = Depends(get_identity), db: Session = Depends(get_db)):
    change = _get_visible_change(db, change_id, identity)
    try:
        run_change_impact(db, change, identity.user, _visible_ids(db, identity))
    except ValueError as exc:
        raise HTTPException(400, str(exc))
    log_event(db, identity.user, "ECR_IMPACT", "change", change.id, {"risk_level": change.risk_level})
    for document_id in change.affected_document_ids or []:
        if document_id in _visible_ids(db, identity):
            log_document_activity(db, document_id, identity.user, "ECR_IMPACT", f"Документ затронут изменением {change.code}", {"change_id": change.id, "risk_level": change.risk_level})
    return _serialize_change_with_configuration(db, change, identity, include_history=True)

@router.post("/changes/{change_id}/submit")
def submit_engineering_change(change_id: str, identity: Identity = Depends(get_identity), db: Session = Depends(get_db)):
    change = _get_visible_change(db, change_id, identity)
    if identity.user != change.created_by and not _is_admin(identity):
        raise HTTPException(403, "Only the author or engineering admin can submit the change")
    try:
        submit_for_approval(db, change, identity.user)
    except ValueError as exc:
        raise HTTPException(400, str(exc))
    return _serialize_change_with_configuration(db, change, identity, include_history=True)

@router.post("/changes/{change_id}/decision")
def decide_engineering_change(change_id: str, req: ChangeDecisionRequest, identity: Identity = Depends(get_identity), db: Session = Depends(get_db)):
    change = _get_visible_change(db, change_id, identity)
    require_expected_version(change, req.expected_version, "change_request")
    try:
        decide_change(db, change, stage=req.stage, decision=req.decision, comment=req.comment, user=identity.user, is_admin=_is_admin(identity), allowed_document_ids=_visible_ids(db, identity))
    except PermissionError as exc:
        raise HTTPException(403, str(exc))
    except ValueError as exc:
        raise HTTPException(400, str(exc))
    log_event(db, identity.user, "CHANGE_DECISION", "change", change.id, {"stage": req.stage, "decision": req.decision, "eco_code": change.eco_code})
    if change.eco_code:
        for document_id in change.affected_document_ids or []:
            if document_id in _visible_ids(db, identity):
                log_document_activity(db, document_id, identity.user, "ECO_RELEASED", f"Выпущено изменение {change.eco_code}", {"change_id": change.id, "ecr_code": change.code})
    return _serialize_change_with_configuration(db, change, identity, include_history=True)

@router.post("/changes/{change_id}/implementation")
def start_engineering_change_implementation(change_id: str, req: ChangeImplementationRequest, identity: Identity = Depends(get_identity), db: Session = Depends(get_db)):
    change = _get_visible_change(db, change_id, identity)
    require_expected_version(change, req.expected_version, "change_request")
    try:
        start_implementation(db, change, implementation_plan=req.implementation_plan, verification_plan=req.verification_plan, user=identity.user)
    except ValueError as exc:
        raise HTTPException(400, str(exc))
    return _serialize_change_with_configuration(db, change, identity, include_history=True)

@router.post("/changes/{change_id}/complete")
def complete_engineering_change(change_id: str, req: ChangeCompleteRequest, identity: Identity = Depends(get_identity), db: Session = Depends(get_db)):
    change = _get_visible_change(db, change_id, identity)
    if identity.user != change.owner and not _is_admin(identity):
        raise HTTPException(403, "Only the implementation owner or engineering admin can complete the change")
    require_expected_version(change, req.expected_version, "change_request")
    try:
        complete_change(db, change, verification_result=req.verification_result, user=identity.user)
    except ValueError as exc:
        raise HTTPException(400, str(exc))
    log_event(db, identity.user, "ECO_IMPLEMENTED", "change", change.id, {"eco_code": change.eco_code})
    for document_id in change.affected_document_ids or []:
        if document_id in _visible_ids(db, identity):
            log_document_activity(db, document_id, identity.user, "ECO_IMPLEMENTED", f"Изменение {change.eco_code or change.code} внедрено", {"change_id": change.id, "verification_result": req.verification_result})
    return _serialize_change_with_configuration(db, change, identity, include_history=True)

@router.get("/projects/{project_code}/configurations")
def get_configurations(project_code: str, manufacturing_area: str | None = None, identity: Identity = Depends(get_identity), db: Session = Depends(get_db)):
    project, visible_doc_ids, visible_parts, allowed_areas=_configuration_context(db,project_code,identity,manufacturing_area)
    return configuration_workspace(db,project.code,visible_doc_ids,visible_parts,manufacturing_area,allowed_areas)

@router.get("/projects/{project_code}/configurations/impact")
def get_configuration_impact(project_code: str, part_number: str, manufacturing_area: str | None = None, identity: Identity = Depends(get_identity), db: Session = Depends(get_db)):
    project, visible_doc_ids, visible_parts, allowed_areas=_configuration_context(db,project_code,identity,manufacturing_area)
    pn=part_number.strip().upper()
    if pn not in visible_parts: raise HTTPException(404,"Part not found")
    return configuration_impact(db,project.code,pn,visible_doc_ids,visible_parts,manufacturing_area,allowed_areas)

@router.post("/projects/{project_code}/configurations/variants")
def create_vehicle_variant(project_code: str, req: VehicleVariantCreateRequest, identity: Identity = Depends(get_identity), db: Session = Depends(get_db)):
    project, visible_doc_ids, _, _=_configuration_context(db,project_code,identity)
    _validate_quality_area(db,project,identity,req.manufacturing_area)
    evidence=_validate_quality_evidence(db,project,visible_doc_ids,req.evidence_document_ids)
    code=req.code.upper()
    if db.scalar(select(VehicleVariant).where(VehicleVariant.project_code==project.code,VehicleVariant.code==code)): raise HTTPException(409,"Vehicle variant code already exists")
    profile_values={k:getattr(req,k) for k in PROFILE_KEYS}
    attributes=merge_vehicle_profile(req.attributes,profile_values)
    row=VehicleVariant(project_code=project.code,manufacturing_area=req.manufacturing_area,code=code,name=req.name.strip(),status=req.status,model_year=req.model_year,market=req.market,body_style=req.body_style,engine=req.engine,transmission=req.transmission,trim=req.trim,supplier_strategy=req.supplier_strategy,attributes_json=attributes,evidence_document_ids=evidence,notes=req.notes,created_by=identity.user)
    db.add(row);db.commit();db.refresh(row)
    log_event(db,identity.user,"VEHICLE_VARIANT_CREATED","project",project.code,{"id":row.id,"code":row.code})
    return serialize_variant(row,visible_doc_ids)

@router.patch("/projects/{project_code}/configurations/variants/{variant_id}")
def update_vehicle_variant(project_code: str, variant_id: str, req: VehicleVariantUpdateRequest, identity: Identity = Depends(get_identity), db: Session = Depends(get_db)):
    project, visible_doc_ids, _, _=_configuration_context(db,project_code,identity)
    row=_get_variant(db,project,variant_id,identity,visible_doc_ids)
    values=req.model_dump(exclude_unset=True)
    if 'manufacturing_area' in values: _validate_quality_area(db,project,identity,values['manufacturing_area'])
    if 'evidence_document_ids' in values: values['evidence_document_ids']=_validate_quality_evidence(db,project,visible_doc_ids,values['evidence_document_ids'])
    explicit_profile={k:values.pop(k) for k in list(values) if k in PROFILE_KEYS}
    if 'attributes' in values:
        base_attributes=values.pop('attributes')
    else:
        base_attributes=row.attributes_json or {}
    if explicit_profile:
        values['attributes_json']=merge_vehicle_profile(base_attributes,explicit_profile,partial=True)
    elif base_attributes is not row.attributes_json:
        values['attributes_json']=base_attributes
    for k,v in values.items(): setattr(row,k,v)
    db.commit();db.refresh(row)
    log_event(db,identity.user,"VEHICLE_VARIANT_UPDATED","project",project.code,{"id":row.id,"fields":sorted(values)})
    return serialize_variant(row,visible_doc_ids)

@router.post("/projects/{project_code}/configurations/applicability")
def create_configuration_applicability(project_code: str, req: ConfigurationApplicabilityCreateRequest, identity: Identity = Depends(get_identity), db: Session = Depends(get_db)):
    project, visible_doc_ids, visible_parts, _=_configuration_context(db,project_code,identity)
    variant=_get_variant(db,project,req.variant_id,identity,visible_doc_ids)
    _validate_quality_area(db,project,identity,req.manufacturing_area)
    key=_configuration_entity_key(db,project,req,identity,visible_doc_ids,visible_parts)
    evidence=_validate_quality_evidence(db,project,visible_doc_ids,req.evidence_document_ids)
    existing=db.scalar(select(ConfigurationApplicability).where(ConfigurationApplicability.project_code==project.code,ConfigurationApplicability.variant_id==variant.id,ConfigurationApplicability.entity_type==req.entity_type,ConfigurationApplicability.entity_key==key))
    if existing: raise HTTPException(409,"Applicability already exists")
    row=ConfigurationApplicability(project_code=project.code,variant_id=variant.id,manufacturing_area=req.manufacturing_area,entity_type=req.entity_type,entity_key=key,applicability=req.applicability,source=req.source,effectivity_from=req.effectivity_from,effectivity_to=req.effectivity_to,evidence_document_ids=evidence,notes=req.notes,created_by=identity.user)
    db.add(row);db.commit();db.refresh(row)
    log_event(db,identity.user,"CONFIGURATION_APPLICABILITY_CREATED","project",project.code,{"id":row.id,"variant":variant.code,"entity_type":row.entity_type,"entity_key":row.entity_key,"applicability":row.applicability})
    return serialize_applicability(row,variant,visible_doc_ids)

@router.patch("/projects/{project_code}/configurations/applicability/{applicability_id}")
def update_configuration_applicability(project_code: str, applicability_id: str, req: ConfigurationApplicabilityUpdateRequest, identity: Identity = Depends(get_identity), db: Session = Depends(get_db)):
    project, visible_doc_ids, _, _=_configuration_context(db,project_code,identity)
    row=db.get(ConfigurationApplicability,applicability_id)
    if not row or row.project_code!=project.code: raise HTTPException(404,"Applicability not found")
    _get_variant(db,project,row.variant_id,identity,visible_doc_ids)
    _validate_quality_area(db,project,identity,row.manufacturing_area)
    if row.evidence_document_ids and not set(row.evidence_document_ids).issubset(visible_doc_ids): raise HTTPException(404,"Applicability not found")
    values=req.model_dump(exclude_unset=True)
    if 'manufacturing_area' in values: _validate_quality_area(db,project,identity,values['manufacturing_area'])
    if 'evidence_document_ids' in values: values['evidence_document_ids']=_validate_quality_evidence(db,project,visible_doc_ids,values['evidence_document_ids'])
    for k,v in values.items(): setattr(row,k,v)
    db.commit();db.refresh(row)
    return serialize_applicability(row,db.get(VehicleVariant,row.variant_id),visible_doc_ids)

@router.get("/projects/{project_code}/closed-loop")
def project_closed_loop(project_code: str, manufacturing_area: str | None = None, identity: Identity = Depends(get_identity), db: Session = Depends(get_db)):
    project, visible_doc_ids, visible_parts, allowed_areas=_closed_loop_context(db,project_code,identity,manufacturing_area)
    return closed_loop_workspace(db,project.code,visible_doc_ids,visible_parts,manufacturing_area,allowed_areas)

@router.post("/projects/{project_code}/closed-loop/decisions")
def create_engineering_decision(project_code: str, req: EngineeringDecisionCreateRequest, identity: Identity = Depends(get_identity), db: Session = Depends(get_db)):
    project, visible_doc_ids, visible_parts, allowed_areas=_closed_loop_context(db,project_code,identity,req.manufacturing_area)
    _visible_evidence_or_400(req.evidence_document_ids,visible_doc_ids)
    pn=req.part_number.strip().upper() if req.part_number else None
    if pn and pn not in visible_parts: raise HTTPException(404,"Part not found")
    change=_visible_change_or_404(db,req.change_id,visible_doc_ids,visible_parts)
    code=req.code.strip().upper()
    if db.scalar(select(EngineeringDecisionRecord).where(EngineeringDecisionRecord.project_code==project.code,EngineeringDecisionRecord.code==code)): raise HTTPException(409,"Decision code already exists")
    row=EngineeringDecisionRecord(project_code=project.code,manufacturing_area=req.manufacturing_area,code=code,title=req.title.strip(),part_number=pn,change_id=change.id if change else None,problem_statement=req.problem_statement.strip(),alternatives_json=req.alternatives,chosen_option=req.chosen_option.strip(),rationale=req.rationale.strip(),expected_result=req.expected_result,accepted_risk=req.accepted_risk,owner=req.owner or identity.user,evidence_document_ids=req.evidence_document_ids,metadata_json=req.metadata,created_by=identity.user)
    db.add(row);db.commit();db.refresh(row)
    log_event(db,identity.user,"ENGINEERING_DECISION_CREATED","project",project.code,{"decision_id":row.id,"code":row.code,"part_number":pn,"change_id":row.change_id})
    return serialize_decision(row)

@router.patch("/projects/{project_code}/closed-loop/decisions/{decision_id}")
def update_engineering_decision(project_code: str, decision_id: str, req: EngineeringDecisionUpdateRequest, identity: Identity = Depends(get_identity), db: Session = Depends(get_db)):
    project, visible_doc_ids, visible_parts, _=_closed_loop_context(db,project_code,identity,None)
    row=db.get(EngineeringDecisionRecord,decision_id)
    if not row or row.project_code!=project.code or (row.part_number and row.part_number not in visible_parts) or not set(row.evidence_document_ids or []).issubset(visible_doc_ids): raise HTTPException(404,"Engineering decision not found")
    if req.status in {"approved","verified","closed"} and not _is_admin(identity): raise HTTPException(403,"Engineering admin required for controlled decision status")
    values=req.model_dump(exclude_unset=True)
    if "evidence_document_ids" in values:
        _visible_evidence_or_400(values["evidence_document_ids"] or [],visible_doc_ids); row.evidence_document_ids=values.pop("evidence_document_ids") or []
    for k,v in values.items(): setattr(row,k,v)
    if req.status=="approved": row.approved_by=identity.user; row.approved_at=datetime.now().astimezone()
    db.commit();db.refresh(row)
    log_event(db,identity.user,"ENGINEERING_DECISION_UPDATED","project",project.code,{"decision_id":row.id,"status":row.status,"effectiveness_status":row.effectiveness_status})
    return serialize_decision(row)

@router.post("/projects/{project_code}/closed-loop/production-feedback")
def create_production_feedback(project_code: str, req: ProductionFeedbackCreateRequest, identity: Identity = Depends(get_identity), db: Session = Depends(get_db)):
    project, visible_doc_ids, visible_parts, _=_closed_loop_context(db,project_code,identity,req.manufacturing_area)
    _visible_evidence_or_400(req.evidence_document_ids,visible_doc_ids)
    pn=req.part_number.strip().upper() if req.part_number else None
    if pn and pn not in visible_parts: raise HTTPException(404,"Part not found")
    change=_visible_change_or_404(db,req.change_id,visible_doc_ids,visible_parts)
    decision=db.get(EngineeringDecisionRecord,req.decision_id) if req.decision_id else None
    if req.decision_id and (not decision or decision.project_code!=project.code or not set(decision.evidence_document_ids or []).issubset(visible_doc_ids)): raise HTTPException(404,"Engineering decision not found")
    code=req.code.strip().upper()
    if db.scalar(select(ProductionFeedback).where(ProductionFeedback.project_code==project.code,ProductionFeedback.code==code)): raise HTTPException(409,"Feedback code already exists")
    row=ProductionFeedback(project_code=project.code,manufacturing_area=req.manufacturing_area,code=code,change_id=change.id if change else None,decision_id=decision.id if decision else None,part_number=pn,supplier_code=req.supplier_code,observation_from=_parse_iso_datetime(req.observation_from),observation_to=_parse_iso_datetime(req.observation_to),built_quantity=req.built_quantity,defect_quantity=req.defect_quantity,before_defect_rate_pct=req.before_defect_rate_pct,planned_cost_delta=req.planned_cost_delta,actual_cost_delta=req.actual_cost_delta,planned_mass_delta_kg=req.planned_mass_delta_kg,actual_mass_delta_kg=req.actual_mass_delta_kg,planned_cycle_time_delta_sec=req.planned_cycle_time_delta_sec,actual_cycle_time_delta_sec=req.actual_cycle_time_delta_sec,currency=req.currency.upper() if req.currency else None,status=req.status,metrics_json=req.metrics,evidence_document_ids=req.evidence_document_ids,notes=req.notes,created_by=identity.user)
    db.add(row);db.commit();db.refresh(row)
    log_event(db,identity.user,"PRODUCTION_FEEDBACK_RECORDED","project",project.code,{"feedback_id":row.id,"change_id":row.change_id,"part_number":pn,"built_quantity":row.built_quantity,"defect_quantity":row.defect_quantity})
    return serialize_feedback(row)

@router.post("/projects/{project_code}/closed-loop/effectiveness")
def create_change_effectiveness(project_code: str, req: ChangeEffectivenessCreateRequest, identity: Identity = Depends(get_identity), db: Session = Depends(get_db)):
    project, visible_doc_ids, visible_parts, _=_closed_loop_context(db,project_code,identity,req.manufacturing_area)
    _visible_evidence_or_400(req.evidence_document_ids,visible_doc_ids)
    change=_visible_change_or_404(db,req.change_id,visible_doc_ids,visible_parts)
    if req.status in {"effective","ineffective"} and not _is_admin(identity): raise HTTPException(403,"Engineering admin required to confirm final change effectiveness")
    decision=db.get(EngineeringDecisionRecord,req.decision_id) if req.decision_id else None
    feedback=db.get(ProductionFeedback,req.feedback_id) if req.feedback_id else None
    if req.decision_id and (not decision or decision.project_code!=project.code): raise HTTPException(404,"Engineering decision not found")
    if req.feedback_id and (not feedback or feedback.project_code!=project.code or not set(feedback.evidence_document_ids or []).issubset(visible_doc_ids)): raise HTTPException(404,"Production feedback not found")
    code=req.code.strip().upper()
    if db.scalar(select(ChangeEffectivenessReview).where(ChangeEffectivenessReview.project_code==project.code,ChangeEffectivenessReview.code==code)): raise HTTPException(409,"Effectiveness review code already exists")
    row=ChangeEffectivenessReview(project_code=project.code,manufacturing_area=req.manufacturing_area,code=code,change_id=change.id,decision_id=decision.id if decision else None,feedback_id=feedback.id if feedback else None,target_description=req.target_description,baseline_value=req.baseline_value,target_value=req.target_value,observed_value=req.observed_value,unit=req.unit,population=req.population,status=req.status,conclusion=req.conclusion,evidence_document_ids=req.evidence_document_ids,reviewed_by=identity.user if req.status in {"effective","ineffective","inconclusive"} else None,reviewed_at=datetime.now().astimezone() if req.status in {"effective","ineffective","inconclusive"} else None,metadata_json=req.metadata,created_by=identity.user)
    db.add(row)
    if decision and req.status in {"effective","ineffective","inconclusive"}:
        decision.effectiveness_status=req.status; decision.effectiveness_summary=req.conclusion or req.target_description
    db.commit();db.refresh(row)
    log_event(db,identity.user,"CHANGE_EFFECTIVENESS_REVIEWED","project",project.code,{"review_id":row.id,"change_id":row.change_id,"status":row.status})
    return serialize_effectiveness(row)

@router.post("/projects/{project_code}/closed-loop/deviations")
def create_engineering_deviation(project_code: str, req: EngineeringDeviationCreateRequest, identity: Identity = Depends(get_identity), db: Session = Depends(get_db)):
    project, visible_doc_ids, visible_parts, _=_closed_loop_context(db,project_code,identity,req.manufacturing_area)
    _visible_evidence_or_400(req.evidence_document_ids,visible_doc_ids)
    pn=req.part_number.strip().upper()
    if pn not in visible_parts: raise HTTPException(404,"Part not found")
    code=req.code.strip().upper()
    if db.scalar(select(EngineeringDeviation).where(EngineeringDeviation.project_code==project.code,EngineeringDeviation.code==code)): raise HTTPException(409,"Deviation code already exists")
    row=EngineeringDeviation(project_code=project.code,manufacturing_area=req.manufacturing_area,code=code,part_number=pn,released_revision=req.released_revision,requested_revision=req.requested_revision,reason=req.reason,quantity_limit=req.quantity_limit,valid_from=_parse_iso_datetime(req.valid_from),valid_until=_parse_iso_datetime(req.valid_until),affected_variant_ids=req.affected_variant_ids,risks_json=req.risks,evidence_document_ids=req.evidence_document_ids,notes=req.notes,created_by=identity.user)
    db.add(row);db.commit();db.refresh(row)
    log_event(db,identity.user,"ENGINEERING_DEVIATION_CREATED","project",project.code,{"deviation_id":row.id,"code":row.code,"part_number":pn})
    return serialize_deviation(row)

@router.patch("/projects/{project_code}/closed-loop/deviations/{deviation_id}")
def update_engineering_deviation(project_code: str, deviation_id: str, req: EngineeringDeviationUpdateRequest, identity: Identity = Depends(get_identity), db: Session = Depends(get_db)):
    project, visible_doc_ids, visible_parts, _=_closed_loop_context(db,project_code,identity,None)
    row=db.get(EngineeringDeviation,deviation_id)
    if not row or row.project_code!=project.code or row.part_number not in visible_parts or not set(row.evidence_document_ids or []).issubset(visible_doc_ids): raise HTTPException(404,"Engineering deviation not found")
    if req.status in {"approved","active","closed"} and not _is_admin(identity): raise HTTPException(403,"Engineering admin required for controlled deviation status")
    values=req.model_dump(exclude_unset=True)
    if "evidence_document_ids" in values:
        _visible_evidence_or_400(values["evidence_document_ids"] or [],visible_doc_ids); row.evidence_document_ids=values.pop("evidence_document_ids") or []
    if "approvals" in values: row.approvals_json=values.pop("approvals") or []
    if "risks" in values: row.risks_json=values.pop("risks") or []
    for k,v in values.items(): setattr(row,k,v)
    if req.status=="approved": row.approved_by=identity.user; row.approved_at=datetime.now().astimezone()
    db.commit();db.refresh(row)
    log_event(db,identity.user,"ENGINEERING_DEVIATION_UPDATED","project",project.code,{"deviation_id":row.id,"status":row.status})
    return serialize_deviation(row)

@router.post("/projects/{project_code}/closed-loop/risks")
def create_engineering_risk(project_code: str, req: EngineeringRiskCreateRequest, identity: Identity = Depends(get_identity), db: Session = Depends(get_db)):
    project, visible_doc_ids, visible_parts, _=_closed_loop_context(db,project_code,identity,req.manufacturing_area)
    _visible_evidence_or_400(req.evidence_document_ids,visible_doc_ids)
    pn=req.part_number.strip().upper() if req.part_number else None
    if pn and pn not in visible_parts: raise HTTPException(404,"Part not found")
    change=_visible_change_or_404(db,req.change_id,visible_doc_ids,visible_parts)
    code=req.code.strip().upper()
    if db.scalar(select(EngineeringRisk).where(EngineeringRisk.project_code==project.code,EngineeringRisk.code==code)): raise HTTPException(409,"Risk code already exists")
    row=EngineeringRisk(project_code=project.code,manufacturing_area=req.manufacturing_area,code=code,title=req.title,description=req.description,part_number=pn,change_id=change.id if change else None,supplier_code=req.supplier_code,probability=req.probability,severity=req.severity,detectability=req.detectability,owner=req.owner or identity.user,mitigations_json=req.mitigations,evidence_document_ids=req.evidence_document_ids,notes=req.notes,created_by=identity.user)
    db.add(row);db.commit();db.refresh(row)
    log_event(db,identity.user,"ENGINEERING_RISK_CREATED","project",project.code,{"risk_id":row.id,"code":row.code,"part_number":pn})
    return serialize_risk(row)

@router.patch("/projects/{project_code}/closed-loop/risks/{risk_id}")
def update_engineering_risk(project_code: str, risk_id: str, req: EngineeringRiskUpdateRequest, identity: Identity = Depends(get_identity), db: Session = Depends(get_db)):
    project, visible_doc_ids, visible_parts, _=_closed_loop_context(db,project_code,identity,None)
    row=db.get(EngineeringRisk,risk_id)
    if not row or row.project_code!=project.code or (row.part_number and row.part_number not in visible_parts) or not set(row.evidence_document_ids or []).issubset(visible_doc_ids): raise HTTPException(404,"Engineering risk not found")
    if req.status in {"accepted","closed"} and not _is_admin(identity): raise HTTPException(403,"Engineering admin required to accept/close engineering risk")
    values=req.model_dump(exclude_unset=True)
    if "evidence_document_ids" in values:
        _visible_evidence_or_400(values["evidence_document_ids"] or [],visible_doc_ids); row.evidence_document_ids=values.pop("evidence_document_ids") or []
    if "mitigations" in values: row.mitigations_json=values.pop("mitigations") or []
    for k,v in values.items(): setattr(row,k,v)
    db.commit();db.refresh(row)
    log_event(db,identity.user,"ENGINEERING_RISK_UPDATED","project",project.code,{"risk_id":row.id,"status":row.status})
    return serialize_risk(row)

@router.post("/projects/{project_code}/closed-loop/validation-plan")
def closed_loop_validation_plan(project_code: str, req: ChangeSimulationRequest, manufacturing_area: str | None = None, identity: Identity = Depends(get_identity), db: Session = Depends(get_db)):
    project, _, visible_parts, _=_closed_loop_context(db,project_code,identity,manufacturing_area)
    if req.part_number.strip().upper() not in visible_parts: raise HTTPException(404,"Part not found")
    return risk_based_validation_plan(req.model_dump()) | {"part_number":req.part_number.strip().upper()}

@router.get("/projects/{project_code}/closed-loop/defects/{defect_id}/root-cause")
def closed_loop_root_cause(project_code: str, defect_id: str, manufacturing_area: str | None = None, identity: Identity = Depends(get_identity), db: Session = Depends(get_db)):
    project, visible_doc_ids, visible_parts, allowed_areas=_closed_loop_context(db,project_code,identity,manufacturing_area)
    try: return defect_root_cause_explorer(db,project.code,visible_doc_ids,visible_parts,manufacturing_area,allowed_areas,defect_id)
    except LookupError as exc: raise HTTPException(404,str(exc)) from exc

@router.get("/projects/{project_code}/configuration-assurance")
def get_configuration_assurance(project_code: str, variant_id: str | None = None, vehicle_identifier: str | None = None, manufacturing_area: str | None = None, identity: Identity = Depends(get_identity), db: Session = Depends(get_db)):
    project, visible_doc_ids, visible_parts, allowed_areas = _assurance_context(db, project_code, identity, manufacturing_area)
    try:
        return configuration_release_assurance_workspace(db, project, visible_doc_ids, visible_parts, manufacturing_area, allowed_areas, variant_id, vehicle_identifier)
    except LookupError as exc:
        raise HTTPException(404, str(exc)) from exc

@router.post("/projects/{project_code}/configuration-assurance/ask")
def ask_configuration_assurance(project_code: str, req: ConfigurationAssuranceAskRequest, identity: Identity = Depends(get_identity), db: Session = Depends(get_db)):
    project, visible_doc_ids, visible_parts, allowed_areas = _assurance_context(db, project_code, identity, req.manufacturing_area)
    try:
        ws=configuration_release_assurance_workspace(db,project,visible_doc_ids,visible_parts,req.manufacturing_area,allowed_areas,req.variant_id,req.vehicle_identifier)
    except LookupError as exc:
        raise HTTPException(404,str(exc)) from exc
    return configuration_assurance_answer(ws,req.query)

@router.get("/projects/{project_code}/configuration-assurance/release-package")
def get_configuration_release_package(project_code: str, variant_id: str | None = None, manufacturing_area: str | None = None, identity: Identity = Depends(get_identity), db: Session = Depends(get_db)):
    project, visible_doc_ids, visible_parts, allowed_areas = _assurance_context(db, project_code, identity, manufacturing_area)
    variant = _get_variant(db, project, variant_id, identity, visible_doc_ids) if variant_id else None
    ws = configuration_release_assurance_workspace(db, project, visible_doc_ids, visible_parts, manufacturing_area, allowed_areas, variant_id, None)
    return release_package(db, project, visible_doc_ids, visible_parts, allowed_areas, variant, manufacturing_area, ws["buildability"])

@router.post("/projects/{project_code}/configuration-assurance/mbom")
def create_mbom_item(project_code: str, req: ManufacturingBOMItemCreateRequest, identity: Identity = Depends(get_identity), db: Session = Depends(get_db)):
    _assurance_admin(identity)
    project, visible_doc_ids, visible_parts, _ = _assurance_context(db, project_code, identity, req.manufacturing_area)
    _validate_quality_area(db, project, identity, req.manufacturing_area)
    parent=req.parent_part_number.strip().upper(); child=req.child_part_number.strip().upper()
    if parent not in visible_parts or child not in visible_parts: raise HTTPException(404,"Part not found")
    if req.variant_id: _get_variant(db,project,req.variant_id,identity,visible_doc_ids)
    evidence=_validate_quality_evidence(db,project,visible_doc_ids,req.evidence_document_ids)
    if req.source_document_id and req.source_document_id not in visible_doc_ids: raise HTTPException(404,"Document not found")
    row=ManufacturingBOMItem(project_code=project.code,manufacturing_area=req.manufacturing_area,variant_id=req.variant_id,parent_part_number=parent,parent_revision=req.parent_revision,child_part_number=child,child_revision=req.child_revision,quantity=req.quantity,unit=req.unit,position=req.position,operation_code=req.operation_code,supplier_code=req.supplier_code,source_system=req.source_system,source_document_id=req.source_document_id,evidence_document_ids=evidence,metadata_json=req.metadata,created_by=identity.user)
    db.add(row)
    try: db.commit()
    except Exception as exc: db.rollback(); raise HTTPException(409,"MBOM item already exists in this scope") from exc
    db.refresh(row); log_event(db,identity.user,"MBOM_ITEM_CREATED","project",project.code,{"id":row.id,"child_part_number":child,"variant_id":req.variant_id})
    return serialize_mbom(row)

@router.post("/projects/{project_code}/configuration-assurance/effectivity")
def create_effectivity(project_code: str, req: ConfigurationEffectivityCreateRequest, identity: Identity = Depends(get_identity), db: Session = Depends(get_db)):
    _assurance_admin(identity)
    project, visible_doc_ids, visible_parts, _ = _assurance_context(db, project_code, identity, req.manufacturing_area)
    _validate_quality_area(db,project,identity,req.manufacturing_area)
    pn=req.part_number.strip().upper()
    if pn not in visible_parts: raise HTTPException(404,"Part not found")
    if req.variant_id: _get_variant(db,project,req.variant_id,identity,visible_doc_ids)
    evidence=_validate_quality_evidence(db,project,visible_doc_ids,req.evidence_document_ids)
    if req.serial_from is not None and req.serial_to is not None and req.serial_from>req.serial_to: raise HTTPException(400,"serial_from must be <= serial_to")
    row=ConfigurationEffectivity(project_code=project.code,manufacturing_area=req.manufacturing_area,variant_id=req.variant_id,part_number=pn,revision=req.revision,plant=req.plant,market=req.market,supplier_code=req.supplier_code,vin_from=req.vin_from,vin_to=req.vin_to,serial_from=req.serial_from,serial_to=req.serial_to,effective_from=_parse_iso_datetime(req.effective_from),effective_to=_parse_iso_datetime(req.effective_to),status=req.status,source=req.source,evidence_document_ids=evidence,notes=req.notes,metadata_json=req.metadata,created_by=identity.user)
    db.add(row)
    try: db.commit()
    except Exception as exc: db.rollback(); raise HTTPException(409,"Effectivity rule already exists in this scope") from exc
    db.refresh(row); log_event(db,identity.user,"CONFIGURATION_EFFECTIVITY_CREATED","project",project.code,{"id":row.id,"part_number":pn,"revision":row.revision})
    return serialize_effectivity(row)

@router.post("/projects/{project_code}/configuration-assurance/cutins")
def create_change_cutin(project_code: str, req: ChangeCutInCreateRequest, identity: Identity = Depends(get_identity), db: Session = Depends(get_db)):
    _assurance_admin(identity)
    project, visible_doc_ids, visible_parts, _ = _assurance_context(db, project_code, identity, req.manufacturing_area)
    _validate_quality_area(db,project,identity,req.manufacturing_area)
    pn=req.part_number.strip().upper()
    if pn not in visible_parts: raise HTTPException(404,"Part not found")
    for vid in req.variant_ids: _get_variant(db,project,vid,identity,visible_doc_ids)
    if req.change_id:
        ch=db.get(ChangeRequest,req.change_id)
        if not ch or (ch.part_number and ch.part_number.upper()!=pn): raise HTTPException(404,"Change not found")
    if req.line_id:
        line=db.get(ManufacturingLine,req.line_id)
        if not line or line.project_code!=project.code: raise HTTPException(404,"Manufacturing line not found")
    evidence=_validate_quality_evidence(db,project,visible_doc_ids,req.evidence_document_ids)
    row=ChangeCutIn(project_code=project.code,manufacturing_area=req.manufacturing_area,code=req.code.upper(),change_id=req.change_id,part_number=pn,from_revision=req.from_revision,to_revision=req.to_revision,variant_ids=req.variant_ids,plant=req.plant,line_id=req.line_id,cut_in_at=_parse_iso_datetime(req.cut_in_at),vin_from=req.vin_from,old_stock_qty=req.old_stock_qty,new_stock_qty=req.new_stock_qty,old_stock_disposition=req.old_stock_disposition,logistics_confirmed=req.logistics_confirmed,status=req.status,evidence_document_ids=evidence,notes=req.notes,metadata_json=req.metadata,created_by=identity.user)
    db.add(row)
    try: db.commit()
    except Exception as exc: db.rollback(); raise HTTPException(409,"Cut-in code already exists") from exc
    db.refresh(row); log_event(db,identity.user,"CHANGE_CUTIN_CREATED","project",project.code,{"id":row.id,"code":row.code,"part_number":pn})
    return serialize_cutin(row)

@router.post("/projects/{project_code}/configuration-assurance/as-built")
def create_as_built(project_code: str, req: AsBuiltConfigurationCreateRequest, identity: Identity = Depends(get_identity), db: Session = Depends(get_db)):
    _assurance_admin(identity)
    project, visible_doc_ids, visible_parts, _ = _assurance_context(db, project_code, identity, req.manufacturing_area)
    _validate_quality_area(db,project,identity,req.manufacturing_area)
    pn=req.part_number.strip().upper()
    if pn not in visible_parts: raise HTTPException(404,"Part not found")
    if req.variant_id: _get_variant(db,project,req.variant_id,identity,visible_doc_ids)
    if req.deviation_id:
        dev=db.get(EngineeringDeviation,req.deviation_id)
        if not dev or dev.project_code!=project.code or dev.part_number!=pn: raise HTTPException(404,"Deviation not found")
    evidence=_validate_quality_evidence(db,project,visible_doc_ids,req.evidence_document_ids)
    row=AsBuiltConfiguration(project_code=project.code,manufacturing_area=req.manufacturing_area,vehicle_identifier=req.vehicle_identifier,variant_id=req.variant_id,plant=req.plant,built_at=_parse_iso_datetime(req.built_at),part_number=pn,revision=req.revision,supplier_code=req.supplier_code,deviation_id=req.deviation_id,source_system=req.source_system,evidence_document_ids=evidence,metadata_json=req.metadata,created_by=identity.user)
    db.add(row)
    try: db.commit()
    except Exception as exc: db.rollback(); raise HTTPException(409,"As-built vehicle/part record already exists") from exc
    db.refresh(row); log_event(db,identity.user,"AS_BUILT_CONFIGURATION_IMPORTED","project",project.code,{"id":row.id,"vehicle_identifier":row.vehicle_identifier,"part_number":pn})
    return serialize_as_built(row)

@router.post("/projects/{project_code}/configuration-assurance/supersessions")
def create_part_supersession(project_code: str, req: PartSupersessionCreateRequest, identity: Identity = Depends(get_identity), db: Session = Depends(get_db)):
    _assurance_admin(identity)
    project, visible_doc_ids, visible_parts, _ = _assurance_context(db, project_code, identity, req.manufacturing_area)
    _validate_quality_area(db,project,identity,req.manufacturing_area)
    old=req.old_part_number.strip().upper(); new=req.new_part_number.strip().upper()
    if old not in visible_parts or new not in visible_parts: raise HTTPException(404,"Part not found")
    evidence=_validate_quality_evidence(db,project,visible_doc_ids,req.evidence_document_ids)
    row=PartSupersession(project_code=project.code,manufacturing_area=req.manufacturing_area,old_part_number=old,old_revision=req.old_revision,new_part_number=new,new_revision=req.new_revision,interchangeable=req.interchangeable,retrofit_allowed=req.retrofit_allowed,stock_use_allowed=req.stock_use_allowed,status=req.status,evidence_document_ids=evidence,notes=req.notes,metadata_json=req.metadata,created_by=identity.user)
    db.add(row)
    try: db.commit()
    except Exception as exc: db.rollback(); raise HTTPException(409,"Supersession already exists") from exc
    db.refresh(row); log_event(db,identity.user,"PART_SUPERSESSION_CREATED","project",project.code,{"id":row.id,"old":old,"new":new})
    return serialize_supersession(row)

@router.get("/projects/{project_code}/release-baselines")
def get_release_baselines(project_code: str, manufacturing_area: str | None = None, identity: Identity = Depends(get_identity), db: Session = Depends(get_db)):
    project, visible_doc_ids, visible_parts, allowed_areas = _launch_project_context(db, project_code, identity, manufacturing_area)
    return release_workspace(db, project.code, visible_doc_ids, project.root_part_number, manufacturing_area)

@router.post("/projects/{project_code}/release-baselines")
def freeze_release_baseline(project_code: str, req: ReleaseBaselineCreateRequest, identity: Identity = Depends(get_identity), db: Session = Depends(get_db)):
    project, visible_doc_ids, visible_parts, allowed_areas = _launch_project_context(db, project_code, identity, req.manufacturing_area)
    if req.baseline_type in {"release", "sop"} and not _is_admin(identity):
        raise HTTPException(403, "Engineering admin required to freeze Release/SOP baseline")
    if req.variant_id:
        _get_variant(db, project, req.variant_id, identity, visible_doc_ids)
    if db.scalar(select(ReleaseBaseline).where(ReleaseBaseline.project_code==project.code, ReleaseBaseline.code==req.code.upper())):
        raise HTTPException(409, "Baseline code already exists")
    try:
        row=create_release_baseline(db, project, code=req.code, name=req.name, baseline_type=req.baseline_type, created_by=identity.user, visible_document_ids=visible_doc_ids, visible_part_numbers=visible_parts, allowed_area_codes=allowed_areas, variant_id=req.variant_id, manufacturing_area=req.manufacturing_area, root_part_number=req.root_part_number, notes=req.notes)
    except LookupError as exc:
        raise HTTPException(404, str(exc)) from exc
    log_event(db, identity.user, "RELEASE_BASELINE_FROZEN", "project", project.code, {"baseline_id":row.id,"code":row.code,"type":row.baseline_type,"fingerprint":row.fingerprint,"release_candidate":row.release_candidate})
    return serialize_release_baseline(row, visible_doc_ids, True)

@router.get("/projects/{project_code}/release-baselines/comparison")
def compare_release_baseline_api(project_code: str, left_id: str, right_id: str, identity: Identity = Depends(get_identity), db: Session = Depends(get_db)):
    project, visible_doc_ids, _, _ = _launch_project_context(db, project_code, identity)
    left=db.get(ReleaseBaseline,left_id); right=db.get(ReleaseBaseline,right_id)
    if not left or not right or left.project_code!=project.code or right.project_code!=project.code: raise HTTPException(404,"Baseline not found")
    try:
        serialize_release_baseline(left,visible_doc_ids); serialize_release_baseline(right,visible_doc_ids)
    except LookupError:
        raise HTTPException(404,"Baseline not found")
    return compare_digital_thread_baselines(left,right)

@router.get("/projects/{project_code}/release-baselines/{baseline_id}")
def get_release_baseline(project_code: str, baseline_id: str, identity: Identity = Depends(get_identity), db: Session = Depends(get_db)):
    project, visible_doc_ids, _, _ = _launch_project_context(db, project_code, identity)
    row=db.get(ReleaseBaseline,baseline_id)
    if not row or row.project_code!=project.code: raise HTTPException(404,"Baseline not found")
    try: return serialize_release_baseline(row,visible_doc_ids,True)
    except LookupError: raise HTTPException(404,"Baseline not found")

@router.get("/projects/{project_code}/bom-versions")
def get_bom_versions(project_code: str, parent_part_number: str | None = None, identity: Identity = Depends(get_identity), db: Session = Depends(get_db)):
    project=_get_visible_project(db,project_code,identity)
    return list_bom_versions(db,project.code,_visible_ids(db,identity),parent_part_number)

@router.get("/projects/{project_code}/bom-compare")
def get_bom_compare(project_code: str, left_document_id: str, right_document_id: str, parent_part_number: str | None = None, identity: Identity = Depends(get_identity), db: Session = Depends(get_db)):
    project=_get_visible_project(db,project_code,identity)
    try:
        result=compare_bom_versions(db,project.code,_visible_ids(db,identity),left_document_id,right_document_id,parent_part_number)
    except LookupError as exc: raise HTTPException(404,str(exc)) from exc
    except ValueError as exc: raise HTTPException(400,str(exc)) from exc
    log_event(db,identity.user,"BOM_VERSION_COMPARE","project",project.code,{"left_document_id":left_document_id,"right_document_id":right_document_id,"parent_part_number":parent_part_number,"summary":result.get("summary")})
    return result



@router.post("/parts/{part_number}/bom/translate")
async def translate_part_bom(part_number: str, req: BOMTranslationRequest, manufacturing_area: str | None = None, identity: Identity = Depends(get_identity), db: Session = Depends(get_db)):
    if manufacturing_area and not valid_area(manufacturing_area):
        raise HTTPException(400, "Unknown manufacturing area")
    pn = part_number.upper()
    part = db.scalar(select(Part).where(Part.part_number == pn))
    if not part:
        raise HTTPException(404)
    docs = [d for d in _visible_docs_for_area(db, identity, manufacturing_area) if d.part_number == pn]
    if not docs:
        raise HTTPException(404)
    visible_doc_ids = {d.id for d in docs}
    rows = [x for x in db.scalars(select(BOMItem).where(BOMItem.parent_part_number == pn)).all() if x.source_document_id in visible_doc_ids]
    out = await translate_bom(db, rows, project_code=part.project_code, manufacturing_area=manufacturing_area,
                              target_language=req.target_language, source_language=req.source_language,
                              user=identity.user, refresh=req.refresh)
    log_event(db, identity.user, "BOM_TRANSLATION_VIEW", "part", pn, {"target_language": req.target_language, "items": len(rows), "source_immutable": True})
    return out


# --- v6.3.5 Controlled Engineering Release Packages ---
def _release_item_visible(db: Session, project: Project, identity: Identity, entity_type: str, entity_id: str, manufacturing_area: str | None):
    if entity_type == "document":
        if entity_id not in _visible_ids(db, identity): raise HTTPException(404, "Document not found")
        row=db.get(Document,entity_id)
    elif entity_type == "engineering_change":
        row=_get_visible_change(db,entity_id,identity)
    elif entity_type == "work_instruction":
        row=db.get(WorkInstruction,entity_id)
        if not row or row.project_code!=project.code: raise HTTPException(404,"Work instruction not found")
        _validate_quality_area(db,project,identity,row.manufacturing_area)
    elif entity_type == "manufacturing_layout":
        row=db.get(ManufacturingLayout,entity_id)
        if not row or row.project_code!=project.code: raise HTTPException(404,"Layout not found")
        _validate_quality_area(db,project,identity,row.manufacturing_area)
    else: raise HTTPException(400,"Unsupported release package entity type")
    if getattr(row,"project_code",project.code) not in (None,project.code): raise HTTPException(404,"Entity not found")
    area=getattr(row,"manufacturing_area",None)
    if manufacturing_area and area not in (None,manufacturing_area): raise HTTPException(409,"Release package item belongs to another manufacturing area")
    return row

@router.get("/projects/{project_code}/release-packages")
def list_release_packages(project_code: str, manufacturing_area: str | None = None, identity: Identity = Depends(get_identity), db: Session = Depends(get_db)):
    project=_get_visible_project(db,project_code,identity)
    if manufacturing_area: _validate_quality_area(db,project,identity,manufacturing_area)
    rows=db.scalars(select(EngineeringReleasePackage).where(EngineeringReleasePackage.project_code==project.code).order_by(EngineeringReleasePackage.created_at.desc())).all()
    if manufacturing_area: rows=[x for x in rows if x.manufacturing_area==manufacturing_area]
    return [serialize_package(db,x) for x in rows]

@router.post("/projects/{project_code}/release-packages")
def create_controlled_release_package(project_code: str, req: ReleasePackageCreateRequest, identity: Identity = Depends(get_identity), db: Session = Depends(get_db)):
    project=_get_visible_project(db,project_code,identity)
    if req.manufacturing_area: _validate_quality_area(db,project,identity,req.manufacturing_area)
    apply_governance_rls_context(db, identity)
    try: enforce_identity_policy(db, identity, action="release_package_create", project_code=project.code, manufacturing_area=req.manufacturing_area, entity_type="release_package")
    except PermissionError as exc: raise HTTPException(403, str(exc))
    if req.source_change_id: _get_visible_change(db,req.source_change_id,identity)
    items=[]
    for x in req.items:
        _release_item_visible(db,project,identity,x.entity_type,x.entity_id,req.manufacturing_area)
        items.append((x.entity_type,x.entity_id))
    try: pkg=create_release_package(db,project_code=project.code,manufacturing_area=req.manufacturing_area,code=req.code.upper(),title=req.title.strip(),source_change_id=req.source_change_id,items=items,metadata=req.metadata,user=identity.user)
    except (ValueError,LookupError) as exc: raise HTTPException(409,str(exc))
    log_event(db,identity.user,"RELEASE_PACKAGE_CREATED","release_package",pkg.id,{"code":pkg.code,"item_count":len(items),"release_sha256":pkg.release_sha256})
    return serialize_package(db,pkg)

@router.get("/projects/{project_code}/release-packages/{package_id}")
def get_controlled_release_package(project_code: str, package_id: str, identity: Identity = Depends(get_identity), db: Session = Depends(get_db)):
    project=_get_visible_project(db,project_code,identity); pkg=db.get(EngineeringReleasePackage,package_id)
    if not pkg or pkg.project_code!=project.code: raise HTTPException(404,"Release package not found")
    if pkg.manufacturing_area: _validate_quality_area(db,project,identity,pkg.manufacturing_area)
    return serialize_package(db,pkg)

@router.get("/projects/{project_code}/release-packages/{package_id}/manifest")
def get_controlled_release_manifest(project_code: str, package_id: str, identity: Identity = Depends(get_identity), db: Session = Depends(get_db)):
    project=_get_visible_project(db,project_code,identity); pkg=db.get(EngineeringReleasePackage,package_id)
    if not pkg or pkg.project_code!=project.code: raise HTTPException(404,"Release package not found")
    if pkg.manufacturing_area: _validate_quality_area(db,project,identity,pkg.manufacturing_area)
    return release_manifest(db,pkg)

@router.post("/projects/{project_code}/release-packages/{package_id}/submit")
def submit_controlled_release_package(project_code: str, package_id: str, identity: Identity = Depends(get_identity), db: Session = Depends(get_db)):
    project=_get_visible_project(db,project_code,identity); pkg=db.get(EngineeringReleasePackage,package_id)
    if not pkg or pkg.project_code!=project.code: raise HTTPException(404,"Release package not found")
    if pkg.manufacturing_area: _validate_quality_area(db,project,identity,pkg.manufacturing_area)
    apply_governance_rls_context(db, identity)
    try:
        enforce_identity_policy(db, identity, action="release_package_submit", project_code=project.code, manufacturing_area=pkg.manufacturing_area, entity_type="release_package")
        pkg,case=submit_package(db,pkg,identity.user,submitted_identity=identity_snapshot(identity))
    except PermissionError as exc: raise HTTPException(403,str(exc))
    except ValueError as exc: raise HTTPException(409,str(exc))
    log_event(db,identity.user,"RELEASE_PACKAGE_SUBMITTED","release_package",pkg.id,{"approval_case_id":case.id,"release_sha256":pkg.release_sha256})
    return serialize_package(db,pkg)

@router.post("/projects/{project_code}/release-packages/{package_id}/release")
def release_controlled_release_package(project_code: str, package_id: str, identity: Identity = Depends(get_identity), db: Session = Depends(get_db)):
    project=_get_visible_project(db,project_code,identity); pkg=db.get(EngineeringReleasePackage,package_id)
    if not pkg or pkg.project_code!=project.code: raise HTTPException(404,"Release package not found")
    if pkg.manufacturing_area: _validate_quality_area(db,project,identity,pkg.manufacturing_area)
    apply_governance_rls_context(db, identity)
    try:
        pd=enforce_identity_policy(db, identity, action="release_package_release", project_code=project.code, manufacturing_area=pkg.manufacturing_area, entity_type="release_package")
        pkg=release_engineering_package(db,pkg,identity.user,_is_admin(identity),released_identity={**pd.identity,"assurance":pd.assurance,"identity_policy_id":pd.policy_id})
    except PermissionError as exc: raise HTTPException(403,str(exc))
    except ValueError as exc: raise HTTPException(409,str(exc))
    log_event(db,identity.user,"RELEASE_PACKAGE_RELEASED","release_package",pkg.id,{"code":pkg.code,"release_sha256":pkg.release_sha256,"production_writeback":False})
    return serialize_package(db,pkg)


# --- v6.3.7 Engineering Release Handover & Integration Safety ---
def _handover_context(db: Session, project_code: str, package_id: str, identity: Identity):
    project=_get_visible_project(db, project_code, identity)
    pkg=db.get(EngineeringReleasePackage,package_id)
    if not pkg or pkg.project_code!=project_code: raise HTTPException(404,"Release package not found")
    if pkg.manufacturing_area: _validate_quality_area(db,project,identity,pkg.manufacturing_area)
    return pkg

@router.get("/projects/{project_code}/release-packages/{package_id}/handover-jobs")
def list_release_handover_jobs(project_code: str, package_id: str, identity: Identity = Depends(get_identity), db: Session = Depends(get_db)):
    _handover_context(db,project_code,package_id,identity)
    rows=db.scalars(select(EngineeringHandoverJob).where(EngineeringHandoverJob.package_id==package_id).order_by(EngineeringHandoverJob.created_at.desc())).all()
    return [serialize_handover_job(db,x) for x in rows]

@router.post("/projects/{project_code}/release-packages/{package_id}/handover-jobs")
def create_release_handover_job(project_code: str, package_id: str, req: HandoverJobCreateRequest, identity: Identity = Depends(get_identity), db: Session = Depends(get_db)):
    pkg=_handover_context(db,project_code,package_id,identity)
    try:
        pd=enforce_identity_policy(db,identity,action="handover_create",project_code=project_code,manufacturing_area=pkg.manufacturing_area,entity_type="release_package")
        job=create_handover_job(db,package_id=package_id,target_code=req.target_code,idempotency_key=req.idempotency_key,mode=req.mode,identity=identity)
    except PermissionError as exc: raise HTTPException(403,str(exc))
    except LookupError as exc: raise HTTPException(404,str(exc))
    except ValueError as exc: raise HTTPException(409,str(exc))
    log_event(db,identity.user,"HANDOVER_JOB_CREATED","engineering_handover_job",job.id,{"package_id":package_id,"target_code":req.target_code,"mode":job.mode,"request_sha256":job.request_sha256,"identity_policy_id":pd.policy_id})
    out=serialize_handover_job(db,job)
    if job.mode=="dry_run": out["dry_run_preview"]=job.payload_json or {}
    return out

@router.get("/handover-jobs/{job_id}")
def get_release_handover_job(job_id: str, identity: Identity = Depends(get_identity), db: Session = Depends(get_db)):
    job=db.get(EngineeringHandoverJob,job_id)
    if not job: raise HTTPException(404,"Handover job not found")
    pkg=db.get(EngineeringReleasePackage,job.package_id)
    if not pkg: raise HTTPException(404,"Handover job not found")
    _handover_context(db,pkg.project_code,pkg.id,identity)
    return serialize_handover_job(db,job)

@router.post("/handover-jobs/{job_id}/authorize")
def authorize_release_handover_job(job_id: str, req: HandoverAuthorizationRequest, identity: Identity = Depends(get_identity), db: Session = Depends(get_db)):
    job=db.get(EngineeringHandoverJob,job_id)
    if not job: raise HTTPException(404,"Handover job not found")
    pkg=db.get(EngineeringReleasePackage,job.package_id)
    if not pkg: raise HTTPException(404,"Release package not found")
    _handover_context(db,pkg.project_code,pkg.id,identity)
    try:
        pd=enforce_identity_policy(db,identity,action="handover_authorize",project_code=pkg.project_code,manufacturing_area=pkg.manufacturing_area,entity_type="release_package")
        job=authorize_handover_job(db,job,identity=identity,identity_policy_id=pd.policy_id,assurance={**pd.assurance,"comment":req.comment})
    except PermissionError as exc: raise HTTPException(403,str(exc))
    except ValueError as exc: raise HTTPException(409,str(exc))
    log_event(db,identity.user,"HANDOVER_JOB_AUTHORIZED","engineering_handover_job",job.id,{"package_id":pkg.id,"checker":identity.user,"identity_policy_id":pd.policy_id})
    return serialize_handover_job(db,job)

@router.post("/handover-jobs/{job_id}/execute")
def execute_release_handover_job(job_id: str, identity: Identity = Depends(get_identity), db: Session = Depends(get_db)):
    job=db.get(EngineeringHandoverJob,job_id)
    if not job: raise HTTPException(404,"Handover job not found")
    pkg=db.get(EngineeringReleasePackage,job.package_id)
    if not pkg: raise HTTPException(404,"Release package not found")
    _handover_context(db,pkg.project_code,pkg.id,identity)
    try:
        pd=enforce_identity_policy(db,identity,action="handover_execute",project_code=pkg.project_code,manufacturing_area=pkg.manufacturing_area,entity_type="release_package")
        job=execute_handover_job(db,job,identity=identity)
    except PermissionError as exc: raise HTTPException(403,str(exc))
    except (ValueError,LookupError) as exc: raise HTTPException(409,str(exc))
    except Exception as exc: raise HTTPException(502,"Controlled handover gateway delivery failed")
    log_event(db,identity.user,"HANDOVER_JOB_EXECUTED","engineering_handover_job",job.id,{"package_id":pkg.id,"receipt_id":job.external_receipt_id,"response_sha256":job.response_sha256,"identity_policy_id":pd.policy_id})
    return serialize_handover_job(db,job)

@router.post("/handover-jobs/{job_id}/reconcile")
def reconcile_release_handover_job(job_id: str, identity: Identity = Depends(get_identity), db: Session = Depends(get_db)):
    job=db.get(EngineeringHandoverJob,job_id)
    if not job: raise HTTPException(404,"Handover job not found")
    pkg=db.get(EngineeringReleasePackage,job.package_id)
    if not pkg: raise HTTPException(404,"Release package not found")
    _handover_context(db,pkg.project_code,pkg.id,identity)
    try:
        pd=enforce_identity_policy(db,identity,action="handover_reconcile",project_code=pkg.project_code,manufacturing_area=pkg.manufacturing_area,entity_type="release_package")
        job=reconcile_handover_job(db,job,identity=identity)
    except PermissionError as exc: raise HTTPException(403,str(exc))
    except (ValueError,LookupError) as exc: raise HTTPException(409,str(exc))
    except Exception: raise HTTPException(502,"Controlled handover reconciliation failed")
    log_event(db,identity.user,"HANDOVER_JOB_RECONCILED","engineering_handover_job",job.id,{"package_id":pkg.id,"receipt_id":job.external_receipt_id,"identity_policy_id":pd.policy_id})
    return serialize_handover_job(db,job)
