"""Supplier Field HTTP handlers — v6.2.2.

Extracted from the former 3k-line route monolith. Public paths are unchanged.
"""
from fastapi import APIRouter
from app.api import context_shared as _shared

# Preserve the mature shared handler namespace without duplicating service imports.
globals().update({k: v for k, v in vars(_shared).items() if not k.startswith("__")})
from app.api.lazy_service import lazy_service

cost_economics_workspace = lazy_service("app.services.cost_economics", "cost_economics_workspace")
create_cost_evidence_pack = lazy_service("app.services.cost_economics", "create_cost_evidence_pack")
create_localization_evidence_pack = lazy_service("app.services.supplier_localization", "create_localization_evidence_pack")
field_intelligence_answer = lazy_service("app.services.field_reliability_product_lifecycle", "field_intelligence_answer")
field_reliability_workspace = lazy_service("app.services.field_reliability_product_lifecycle", "field_reliability_workspace")
log_event = lazy_service("app.services.audit", "log_event")
serialize_baseline = lazy_service("app.services.cost_economics", "serialize_baseline")
serialize_dfmea = lazy_service("app.services.field_reliability_product_lifecycle", "serialize_dfmea")
serialize_exposure = lazy_service("app.services.field_reliability_product_lifecycle", "serialize_exposure")
serialize_field_claim_v58 = lazy_service("app.services.field_reliability_product_lifecycle", "serialize_field_claim_v58")
serialize_incoming_quality = lazy_service("app.services.supplier_localization", "serialize_incoming_quality")
serialize_line = lazy_service("app.services.cost_economics", "serialize_line")
serialize_localization_item = lazy_service("app.services.supplier_localization", "serialize_localization_item")
serialize_quote = lazy_service("app.services.cost_economics", "serialize_quote")
serialize_service_action = lazy_service("app.services.field_reliability_product_lifecycle", "serialize_service_action")
supplier_localization_workspace = lazy_service("app.services.supplier_localization", "supplier_localization_workspace")
vin_field_trace = lazy_service("app.services.field_reliability_product_lifecycle", "vin_field_trace")

router = APIRouter(tags=["context:supplier_field"])

@router.get("/projects/{project_code}/supplier-localization")
def get_supplier_localization(project_code: str, manufacturing_area: str | None = None, identity: Identity = Depends(get_identity), db: Session = Depends(get_db)):
    project, visible_doc_ids, visible_parts, allowed_areas = _localization_context(db, project_code, identity, manufacturing_area)
    return supplier_localization_workspace(db, project.code, visible_doc_ids, visible_parts, manufacturing_area, allowed_areas)

@router.post("/projects/{project_code}/localization/items")
def create_localization_item(project_code: str, req: LocalizationItemCreateRequest, identity: Identity = Depends(get_identity), db: Session = Depends(get_db)):
    project, visible_doc_ids, visible_parts, _ = _localization_context(db, project_code, identity)
    _validate_quality_area(db, project, identity, req.manufacturing_area)
    part_number = _validate_quality_part(req.part_number, visible_parts)
    evidence = _validate_quality_evidence(db, project, visible_doc_ids, req.evidence_document_ids)
    supplier_code = req.supplier_code.strip().upper()
    existing = db.scalar(select(LocalizationItem).where(LocalizationItem.project_code == project.code, LocalizationItem.part_number == part_number, LocalizationItem.supplier_code == supplier_code))
    if existing:
        raise HTTPException(409, "Localization item already exists for this supplier/part")
    row = LocalizationItem(project_code=project.code, manufacturing_area=req.manufacturing_area, part_number=part_number, revision=req.revision.upper() if req.revision else None,
        supplier_code=supplier_code, supplier_name=req.supplier_name.strip(), source_country=req.source_country, local_plant=req.local_plant, status=req.status,
        localization_percent=req.localization_percent, target_localization_percent=req.target_localization_percent, technical_package_status=req.technical_package_status,
        rfq_status=req.rfq_status, nomination_status=req.nomination_status, tooling_status=req.tooling_status, capacity_status=req.capacity_status, owner=req.owner or identity.user,
        planned_sop_at=_parse_iso_datetime(req.planned_sop_at), evidence_document_ids=evidence, notes=req.notes, created_by=identity.user)
    db.add(row); db.commit(); db.refresh(row)
    log_event(db, identity.user, "LOCALIZATION_ITEM_CREATED", "project", project.code, {"id": row.id, "part_number": row.part_number, "supplier_code": row.supplier_code})
    return serialize_localization_item(row, visible_doc_ids)

@router.patch("/projects/{project_code}/localization/items/{item_id}")
def update_localization_item(project_code: str, item_id: str, req: LocalizationItemUpdateRequest, identity: Identity = Depends(get_identity), db: Session = Depends(get_db)):
    project, visible_doc_ids, visible_parts, _ = _localization_context(db, project_code, identity)
    row = _get_visible_localization_item(db, project, item_id, visible_parts, identity)
    values = req.model_dump(exclude_unset=True)
    if "manufacturing_area" in values: _validate_quality_area(db, project, identity, values["manufacturing_area"])
    if "planned_sop_at" in values: values["planned_sop_at"] = _parse_iso_datetime(values["planned_sop_at"])
    if "evidence_document_ids" in values: values["evidence_document_ids"] = _validate_quality_evidence(db, project, visible_doc_ids, values["evidence_document_ids"])
    if values.get("revision"): values["revision"] = values["revision"].upper()
    for key, value in values.items(): setattr(row, key, value)
    db.commit(); db.refresh(row)
    log_event(db, identity.user, "LOCALIZATION_ITEM_UPDATED", "project", project.code, {"id": row.id, "fields": sorted(values)})
    return serialize_localization_item(row, visible_doc_ids)

@router.post("/projects/{project_code}/localization/incoming-quality")
def create_incoming_quality(project_code: str, req: IncomingQualityCreateRequest, identity: Identity = Depends(get_identity), db: Session = Depends(get_db)):
    project, visible_doc_ids, visible_parts, _ = _localization_context(db, project_code, identity)
    _validate_quality_area(db, project, identity, req.manufacturing_area)
    part_number = _validate_quality_part(req.part_number, visible_parts)
    evidence = _validate_quality_evidence(db, project, visible_doc_ids, req.evidence_document_ids)
    linked_8d_id = _validate_supplier_8d(db, project, visible_parts, req.linked_8d_id)
    code = req.code.strip().upper()
    if db.scalar(select(IncomingQualityRecord).where(IncomingQualityRecord.project_code == project.code, IncomingQualityRecord.code == code)):
        raise HTTPException(409, "Incoming quality code already exists")
    if req.rejected_quantity > req.inspected_quantity or req.defect_quantity > req.inspected_quantity:
        raise HTTPException(400, "Rejected/defect quantity cannot exceed inspected quantity")
    row = IncomingQualityRecord(project_code=project.code, manufacturing_area=req.manufacturing_area, code=code, supplier_code=req.supplier_code.strip().upper(), supplier_name=req.supplier_name,
        part_number=part_number, revision=req.revision.upper() if req.revision else None, lot_reference=req.lot_reference, inspection_type=req.inspection_type,
        inspected_quantity=req.inspected_quantity, rejected_quantity=req.rejected_quantity, defect_quantity=req.defect_quantity, defect_code=req.defect_code, severity=req.severity, status=req.status,
        acceptance_limit_pct=req.acceptance_limit_pct, linked_8d_id=linked_8d_id, evidence_document_ids=evidence, occurred_at=_parse_iso_datetime(req.occurred_at) or datetime.now().astimezone(), notes=req.notes, created_by=identity.user)
    db.add(row); db.commit(); db.refresh(row)
    log_event(db, identity.user, "INCOMING_QUALITY_CREATED", "project", project.code, {"id": row.id, "code": row.code, "part_number": row.part_number, "supplier_code": row.supplier_code})
    return serialize_incoming_quality(row, visible_doc_ids)

@router.patch("/projects/{project_code}/localization/incoming-quality/{record_id}")
def update_incoming_quality(project_code: str, record_id: str, req: IncomingQualityUpdateRequest, identity: Identity = Depends(get_identity), db: Session = Depends(get_db)):
    project, visible_doc_ids, visible_parts, _ = _localization_context(db, project_code, identity)
    row = db.get(IncomingQualityRecord, record_id)
    if not row or row.project_code != project.code or row.part_number not in visible_parts:
        raise HTTPException(404, "Incoming quality record not found")
    _validate_quality_area(db, project, identity, row.manufacturing_area)
    values = req.model_dump(exclude_unset=True)
    if "linked_8d_id" in values: values["linked_8d_id"] = _validate_supplier_8d(db, project, visible_parts, values["linked_8d_id"])
    if "evidence_document_ids" in values: values["evidence_document_ids"] = _validate_quality_evidence(db, project, visible_doc_ids, values["evidence_document_ids"])
    inspected = values.get("inspected_quantity", row.inspected_quantity or 0); rejected = values.get("rejected_quantity", row.rejected_quantity or 0); defects = values.get("defect_quantity", row.defect_quantity or 0)
    if rejected > inspected or defects > inspected: raise HTTPException(400, "Rejected/defect quantity cannot exceed inspected quantity")
    for key, value in values.items(): setattr(row, key, value)
    db.commit(); db.refresh(row)
    log_event(db, identity.user, "INCOMING_QUALITY_UPDATED", "project", project.code, {"id": row.id, "fields": sorted(values), "status": row.status})
    return serialize_incoming_quality(row, visible_doc_ids)

@router.post("/projects/{project_code}/localization/items/{item_id}/evidence-pack")
def create_supplier_evidence_pack(project_code: str, item_id: str, identity: Identity = Depends(get_identity), db: Session = Depends(get_db)):
    project, visible_doc_ids, visible_parts, allowed_areas = _localization_context(db, project_code, identity)
    row = _get_visible_localization_item(db, project, item_id, visible_parts, identity)
    workspace = supplier_localization_workspace(db, project.code, visible_doc_ids, visible_parts, row.manufacturing_area, allowed_areas)
    pack = create_localization_evidence_pack(db, project.code, row, identity.user, visible_doc_ids, workspace)
    log_event(db, identity.user, "LOCALIZATION_EVIDENCE_PACK_CREATED", "project", project.code, {"item_id": row.id, "evidence_pack_id": pack.id})
    return {"id": pack.id, "pack_type": pack.pack_type, "part_number": pack.part_number, "revision": pack.revision, "project_code": pack.project_code, "status": pack.status, "manifest": pack.manifest}

@router.get("/projects/{project_code}/cost-economics")
def get_cost_economics(project_code: str, manufacturing_area: str | None = None, identity: Identity = Depends(get_identity), db: Session = Depends(get_db)):
    project, visible_doc_ids, visible_parts, allowed_areas = _cost_context(db, project_code, identity, manufacturing_area)
    return cost_economics_workspace(db, project.code, visible_doc_ids, visible_parts, manufacturing_area, allowed_areas)

@router.post("/projects/{project_code}/cost/baselines")
def create_cost_baseline(project_code: str, req: CostBaselineCreateRequest, identity: Identity = Depends(get_identity), db: Session = Depends(get_db)):
    project, visible_doc_ids, visible_parts, _ = _cost_context(db, project_code, identity)
    _validate_quality_area(db, project, identity, req.manufacturing_area)
    evidence = _validate_quality_evidence(db, project, visible_doc_ids, req.evidence_document_ids)
    code = req.code.strip().upper()
    if db.scalar(select(CostBaseline).where(CostBaseline.project_code == project.code, CostBaseline.code == code)):
        raise HTTPException(409, "Cost baseline code already exists")
    ref = None
    if req.reference_baseline_id:
        ref = _get_visible_cost_baseline(db, project, req.reference_baseline_id, identity)
    change_id = _validate_cost_change(db, visible_parts, req.linked_change_id)
    if req.baseline_type == "change" and not change_id:
        raise HTTPException(400, "Change cost scenario requires linked_change_id")
    row = CostBaseline(project_code=project.code, manufacturing_area=req.manufacturing_area, code=code, name=req.name.strip(), baseline_type=req.baseline_type,
        status=req.status, currency=req.currency.upper(), annual_volume=req.annual_volume, target_vehicle_cost=req.target_vehicle_cost,
        reference_baseline_id=ref.id if ref else None, linked_change_id=change_id, effective_at=_parse_iso_datetime(req.effective_at), evidence_document_ids=evidence,
        notes=req.notes, created_by=identity.user)
    db.add(row); db.commit(); db.refresh(row)
    log_event(db, identity.user, "COST_BASELINE_CREATED", "project", project.code, {"id": row.id, "code": row.code, "type": row.baseline_type})
    return serialize_baseline(row, visible_doc_ids)

@router.patch("/projects/{project_code}/cost/baselines/{baseline_id}")
def update_cost_baseline(project_code: str, baseline_id: str, req: CostBaselineUpdateRequest, identity: Identity = Depends(get_identity), db: Session = Depends(get_db)):
    project, visible_doc_ids, visible_parts, _ = _cost_context(db, project_code, identity)
    row = _get_visible_cost_baseline(db, project, baseline_id, identity)
    values = req.model_dump(exclude_unset=True)
    if "manufacturing_area" in values: _validate_quality_area(db, project, identity, values["manufacturing_area"])
    if "evidence_document_ids" in values: values["evidence_document_ids"] = _validate_quality_evidence(db, project, visible_doc_ids, values["evidence_document_ids"])
    if "effective_at" in values: values["effective_at"] = _parse_iso_datetime(values["effective_at"])
    if "currency" in values and values["currency"]: values["currency"] = values["currency"].upper()
    if "reference_baseline_id" in values and values["reference_baseline_id"]:
        values["reference_baseline_id"] = _get_visible_cost_baseline(db, project, values["reference_baseline_id"], identity).id
    if "linked_change_id" in values: values["linked_change_id"] = _validate_cost_change(db, visible_parts, values["linked_change_id"])
    next_type = values.get("baseline_type", row.baseline_type)
    next_change = values.get("linked_change_id", row.linked_change_id)
    if next_type == "change" and not next_change:
        raise HTTPException(400, "Change cost scenario requires linked_change_id")
    for key, value in values.items(): setattr(row, key, value)
    db.commit(); db.refresh(row)
    log_event(db, identity.user, "COST_BASELINE_UPDATED", "project", project.code, {"id": row.id, "fields": sorted(values)})
    return serialize_baseline(row, visible_doc_ids)

@router.post("/projects/{project_code}/cost/lines")
def create_cost_line(project_code: str, req: CostLineCreateRequest, identity: Identity = Depends(get_identity), db: Session = Depends(get_db)):
    project, visible_doc_ids, visible_parts, _ = _cost_context(db, project_code, identity)
    base = _get_visible_cost_baseline(db, project, req.baseline_id, identity)
    _validate_quality_area(db, project, identity, req.manufacturing_area)
    part_number = _validate_quality_part(req.part_number, visible_parts)
    evidence = _validate_quality_evidence(db, project, visible_doc_ids, req.evidence_document_ids)
    supplier_code = req.supplier_code.strip().upper() if req.supplier_code else None
    existing = db.scalar(select(CostLine).where(CostLine.baseline_id == base.id, CostLine.part_number == part_number, CostLine.supplier_code == supplier_code))
    if existing: raise HTTPException(409, "Cost line already exists for this baseline/part/supplier")
    if req.calculation_mode == "quote" and req.supplier_unit_price is None:
        raise HTTPException(400, "Quote calculation mode requires supplier_unit_price")
    row = CostLine(project_code=project.code, baseline_id=base.id, manufacturing_area=req.manufacturing_area or base.manufacturing_area, part_number=part_number,
        revision=req.revision.upper() if req.revision else None, supplier_code=supplier_code, supplier_name=req.supplier_name, quantity_per_vehicle=req.quantity_per_vehicle,
        calculation_mode=req.calculation_mode, mass_kg=req.mass_kg, material_name=req.material_name, material_price_per_kg=req.material_price_per_kg, scrap_rate_pct=req.scrap_rate_pct,
        conversion_cost=req.conversion_cost, logistics_cost=req.logistics_cost, packaging_cost=req.packaging_cost, overhead_cost=req.overhead_cost, supplier_unit_price=req.supplier_unit_price,
        other_unit_cost=req.other_unit_cost, tooling_cost=req.tooling_cost, tooling_amortization_volume=req.tooling_amortization_volume, target_unit_cost=req.target_unit_cost,
        evidence_document_ids=evidence, notes=req.notes)
    db.add(row); db.commit(); db.refresh(row)
    log_event(db, identity.user, "COST_LINE_CREATED", "project", project.code, {"id": row.id, "baseline_id": base.id, "part_number": part_number})
    return serialize_line(row, visible_doc_ids)

@router.patch("/projects/{project_code}/cost/lines/{line_id}")
def update_cost_line(project_code: str, line_id: str, req: CostLineUpdateRequest, identity: Identity = Depends(get_identity), db: Session = Depends(get_db)):
    project, visible_doc_ids, visible_parts, _ = _cost_context(db, project_code, identity)
    row = db.get(CostLine, line_id)
    if not row or row.project_code != project.code or row.part_number not in visible_parts:
        raise HTTPException(404, "Cost line not found")
    _validate_quality_area(db, project, identity, row.manufacturing_area)
    values = req.model_dump(exclude_unset=True)
    if "manufacturing_area" in values: _validate_quality_area(db, project, identity, values["manufacturing_area"])
    if "evidence_document_ids" in values: values["evidence_document_ids"] = _validate_quality_evidence(db, project, visible_doc_ids, values["evidence_document_ids"])
    if "revision" in values and values["revision"]: values["revision"] = values["revision"].upper()
    if "supplier_code" in values and values["supplier_code"]: values["supplier_code"] = values["supplier_code"].strip().upper()
    mode = values.get("calculation_mode", row.calculation_mode)
    quote_price = values.get("supplier_unit_price", row.supplier_unit_price)
    if mode == "quote" and quote_price is None: raise HTTPException(400, "Quote calculation mode requires supplier_unit_price")
    for key, value in values.items(): setattr(row, key, value)
    db.commit(); db.refresh(row)
    log_event(db, identity.user, "COST_LINE_UPDATED", "project", project.code, {"id": row.id, "fields": sorted(values)})
    return serialize_line(row, visible_doc_ids)

@router.post("/projects/{project_code}/cost/quotes")
def create_supplier_quotation(project_code: str, req: SupplierQuotationCreateRequest, identity: Identity = Depends(get_identity), db: Session = Depends(get_db)):
    project, visible_doc_ids, visible_parts, _ = _cost_context(db, project_code, identity)
    _validate_quality_area(db, project, identity, req.manufacturing_area)
    part_number = _validate_quality_part(req.part_number, visible_parts)
    evidence = _validate_quality_evidence(db, project, visible_doc_ids, req.evidence_document_ids)
    code = req.code.strip().upper()
    if db.scalar(select(SupplierQuotation).where(SupplierQuotation.project_code == project.code, SupplierQuotation.code == code)):
        raise HTTPException(409, "Supplier quotation code already exists")
    row = SupplierQuotation(project_code=project.code, manufacturing_area=req.manufacturing_area, code=code, part_number=part_number,
        revision=req.revision.upper() if req.revision else None, supplier_code=req.supplier_code.strip().upper(), supplier_name=req.supplier_name.strip(), currency=req.currency.upper(),
        unit_price=req.unit_price, tooling_cost=req.tooling_cost, annual_volume=req.annual_volume, status=req.status, valid_until=_parse_iso_datetime(req.valid_until),
        evidence_document_ids=evidence, notes=req.notes, created_by=identity.user)
    db.add(row); db.commit(); db.refresh(row)
    log_event(db, identity.user, "SUPPLIER_QUOTATION_CREATED", "project", project.code, {"id": row.id, "code": row.code, "part_number": row.part_number})
    return serialize_quote(row, visible_doc_ids)

@router.patch("/projects/{project_code}/cost/quotes/{quote_id}")
def update_supplier_quotation(project_code: str, quote_id: str, req: SupplierQuotationUpdateRequest, identity: Identity = Depends(get_identity), db: Session = Depends(get_db)):
    project, visible_doc_ids, visible_parts, _ = _cost_context(db, project_code, identity)
    row = db.get(SupplierQuotation, quote_id)
    if not row or row.project_code != project.code or row.part_number not in visible_parts:
        raise HTTPException(404, "Supplier quotation not found")
    _validate_quality_area(db, project, identity, row.manufacturing_area)
    values = req.model_dump(exclude_unset=True)
    if "manufacturing_area" in values: _validate_quality_area(db, project, identity, values["manufacturing_area"])
    if "evidence_document_ids" in values: values["evidence_document_ids"] = _validate_quality_evidence(db, project, visible_doc_ids, values["evidence_document_ids"])
    if "valid_until" in values: values["valid_until"] = _parse_iso_datetime(values["valid_until"])
    if "currency" in values and values["currency"]: values["currency"] = values["currency"].upper()
    if "revision" in values and values["revision"]: values["revision"] = values["revision"].upper()
    for key, value in values.items(): setattr(row, key, value)
    db.commit(); db.refresh(row)
    log_event(db, identity.user, "SUPPLIER_QUOTATION_UPDATED", "project", project.code, {"id": row.id, "fields": sorted(values), "status": row.status})
    return serialize_quote(row, visible_doc_ids)

@router.post("/projects/{project_code}/cost/baselines/{baseline_id}/evidence-pack")
def create_cost_pack(project_code: str, baseline_id: str, identity: Identity = Depends(get_identity), db: Session = Depends(get_db)):
    project, visible_doc_ids, visible_parts, allowed_areas = _cost_context(db, project_code, identity)
    base = _get_visible_cost_baseline(db, project, baseline_id, identity)
    workspace = cost_economics_workspace(db, project.code, visible_doc_ids, visible_parts, base.manufacturing_area, allowed_areas)
    pack = create_cost_evidence_pack(db, project.code, base, identity.user, visible_doc_ids, workspace)
    log_event(db, identity.user, "COST_EVIDENCE_PACK_CREATED", "project", project.code, {"baseline_id": base.id, "evidence_pack_id": pack.id})
    return {"id": pack.id, "pack_type": pack.pack_type, "project_code": pack.project_code, "status": pack.status, "manifest": pack.manifest}

@router.post("/projects/{project_code}/series-intelligence/field-claims")
def create_field_quality_claim(project_code: str, req: FieldQualityClaimCreateRequest, identity: Identity = Depends(get_identity), db: Session = Depends(get_db)):
    _assurance_admin(identity)
    project, visible_doc_ids, visible_parts, _ = _launch_project_context(db, project_code, identity, req.manufacturing_area)
    _validate_quality_area(db,project,identity,req.manufacturing_area)
    pn=_validate_quality_part(req.part_number,visible_parts)
    if req.linked_8d_id:
        eight=db.get(Problem8D,req.linked_8d_id)
        if not eight or eight.project_code!=project.code or not set(eight.evidence_document_ids or []).issubset(visible_doc_ids): raise HTTPException(404,"8D not found")
    evidence=_validate_quality_evidence(db,project,visible_doc_ids,req.evidence_document_ids)
    row=FieldQualityClaim(project_code=project.code,manufacturing_area=req.manufacturing_area,claim_reference=req.claim_reference,vehicle_identifier=req.vehicle_identifier,part_number=pn,revision=req.revision,supplier_code=req.supplier_code,failure_mode=req.failure_mode,failure_family=req.failure_family,mileage_km=req.mileage_km,in_service_at=_parse_iso_datetime(req.in_service_at) if req.in_service_at else None,market=req.market,climate_zone=req.climate_zone,dealer_code=req.dealer_code,repair_code=req.repair_code,repair_method=req.repair_method,no_trouble_found=req.no_trouble_found,repeat_repair=req.repeat_repair,part_cost=req.part_cost,labor_cost=req.labor_cost,logistics_cost=req.logistics_cost,dealer_handling_cost=req.dealer_handling_cost,source_system=req.source_system,severity=req.severity,status=req.status,claim_at=_parse_iso_datetime(req.claim_at) or datetime.now().astimezone(),cost_estimate=req.cost_estimate,currency=req.currency.upper(),linked_8d_id=req.linked_8d_id,evidence_document_ids=evidence,metadata_json=req.metadata,created_by=identity.user)
    db.add(row)
    try: db.commit()
    except Exception as exc: db.rollback(); raise HTTPException(409,"Field claim reference already exists") from exc
    db.refresh(row); log_event(db,identity.user,"FIELD_QUALITY_CLAIM_IMPORTED","project",project.code,{"id":row.id,"claim_reference":row.claim_reference,"vehicle_identifier":row.vehicle_identifier})
    return serialize_field_claim_v58(row)

@router.get("/projects/{project_code}/field-intelligence")
def get_field_reliability_intelligence(project_code: str, manufacturing_area: str | None = None, vehicle_identifier: str | None = None, identity: Identity = Depends(get_identity), db: Session = Depends(get_db)):
    project, visible_doc_ids, visible_parts, allowed_areas = _launch_project_context(db, project_code, identity, manufacturing_area)
    return field_reliability_workspace(db, project.code, visible_doc_ids, visible_parts, manufacturing_area, allowed_areas, vehicle_identifier)

@router.post("/projects/{project_code}/field-intelligence/ask")
def ask_field_reliability_intelligence(project_code: str, req: FieldReliabilityAskRequest, identity: Identity = Depends(get_identity), db: Session = Depends(get_db)):
    project, visible_doc_ids, visible_parts, allowed_areas = _launch_project_context(db, project_code, identity, req.manufacturing_area)
    ws=field_reliability_workspace(db, project.code, visible_doc_ids, visible_parts, req.manufacturing_area, allowed_areas, req.vehicle_identifier)
    return field_intelligence_answer(ws, req.query)

@router.get("/projects/{project_code}/field-intelligence/vin/{vehicle_identifier}")
def get_field_vin_trace(project_code: str, vehicle_identifier: str, identity: Identity = Depends(get_identity), db: Session = Depends(get_db)):
    project, visible_doc_ids, visible_parts, allowed_areas = _launch_project_context(db, project_code, identity)
    return vin_field_trace(db, project.code, vehicle_identifier, visible_doc_ids, visible_parts, allowed_areas)

@router.post("/projects/{project_code}/field-intelligence/exposures")
def create_field_reliability_exposure(project_code: str, req: FieldReliabilityExposureCreateRequest, identity: Identity = Depends(get_identity), db: Session = Depends(get_db)):
    _assurance_admin(identity)
    project, visible_doc_ids, visible_parts, _ = _launch_project_context(db, project_code, identity, req.manufacturing_area)
    _validate_quality_area(db,project,identity,req.manufacturing_area)
    pn=_validate_quality_part(req.part_number,visible_parts)
    evidence=_validate_quality_evidence(db,project,visible_doc_ids,req.evidence_document_ids)
    if req.censored_count>req.population_count: raise HTTPException(400,"censored_count cannot exceed population_count")
    row=FieldReliabilityExposure(project_code=project.code,manufacturing_area=req.manufacturing_area,part_number=pn,revision=req.revision,supplier_code=req.supplier_code,market=req.market,climate_zone=req.climate_zone,population_count=req.population_count,censored_count=req.censored_count,censor_mileage_km=req.censor_mileage_km,total_exposure_km=req.total_exposure_km,as_of_at=_parse_iso_datetime(req.as_of_at) or datetime.now().astimezone(),source_system=req.source_system,evidence_document_ids=evidence,metadata_json=req.metadata,created_by=identity.user)
    db.add(row);db.commit();db.refresh(row);log_event(db,identity.user,"FIELD_RELIABILITY_EXPOSURE_IMPORTED","project",project.code,{"id":row.id,"part_number":pn,"population":row.population_count})
    return serialize_exposure(row)

@router.post("/projects/{project_code}/field-intelligence/dfmea")
def create_design_fmea_item(project_code: str, req: DesignFMEAItemCreateRequest, identity: Identity = Depends(get_identity), db: Session = Depends(get_db)):
    _assurance_admin(identity)
    project, visible_doc_ids, visible_parts, _ = _launch_project_context(db, project_code, identity, req.manufacturing_area)
    _validate_quality_area(db,project,identity,req.manufacturing_area)
    pn=_validate_quality_part(req.part_number,visible_parts)
    evidence=_validate_quality_evidence(db,project,visible_doc_ids,req.evidence_document_ids)
    row=DesignFMEAItem(project_code=project.code,manufacturing_area=req.manufacturing_area,part_number=pn,function=req.function,failure_mode=req.failure_mode,effect=req.effect,cause=req.cause,prevention_control=req.prevention_control,detection_control=req.detection_control,severity=req.severity,occurrence=req.occurrence,detection=req.detection,action_priority=req.action_priority,status=req.status,evidence_document_ids=evidence,metadata_json=req.metadata,created_by=identity.user)
    db.add(row);db.commit();db.refresh(row);log_event(db,identity.user,"DFMEA_ITEM_CREATED","project",project.code,{"id":row.id,"part_number":pn,"failure_mode":row.failure_mode})
    return serialize_dfmea(row)

@router.post("/projects/{project_code}/field-intelligence/service-actions")
def create_field_service_action(project_code: str, req: FieldServiceActionCreateRequest, identity: Identity = Depends(get_identity), db: Session = Depends(get_db)):
    _assurance_admin(identity)
    project, visible_doc_ids, visible_parts, _ = _launch_project_context(db, project_code, identity, req.manufacturing_area)
    _validate_quality_area(db,project,identity,req.manufacturing_area)
    pn=_validate_quality_part(req.part_number,visible_parts)
    evidence=_validate_quality_evidence(db,project,visible_doc_ids,req.evidence_document_ids)
    if req.linked_8d_id:
        eight=db.get(Problem8D,req.linked_8d_id)
        if not eight or eight.project_code!=project.code or not set(eight.evidence_document_ids or []).issubset(visible_doc_ids): raise HTTPException(404,"8D not found")
    if req.linked_change_id:
        ch=db.get(ChangeRequest,req.linked_change_id)
        if not ch or ch.project_code!=project.code: raise HTTPException(404,"Change not found")
    row=FieldServiceAction(project_code=project.code,manufacturing_area=req.manufacturing_area,code=req.code.upper(),action_type=req.action_type,title=req.title,status=req.status,part_number=pn,revision=req.revision,supplier_code=req.supplier_code,failure_mode=req.failure_mode,severity=req.severity,safety_relevance=req.safety_relevance,applicability_json=req.applicability,diagnosis=req.diagnosis,repair=req.repair,suspect_vehicle_identifiers=list(dict.fromkeys(req.suspect_vehicle_identifiers)),inspected_quantity=req.inspected_quantity,repaired_quantity=req.repaired_quantity,no_defect_quantity=req.no_defect_quantity,linked_8d_id=req.linked_8d_id,linked_change_id=req.linked_change_id,evidence_document_ids=evidence,notes=req.notes,metadata_json=req.metadata,human_approval_required=True,created_by=identity.user)
    db.add(row)
    try: db.commit()
    except Exception as exc: db.rollback(); raise HTTPException(409,"Field service action code already exists") from exc
    db.refresh(row);log_event(db,identity.user,"FIELD_SERVICE_ACTION_CREATED","project",project.code,{"id":row.id,"code":row.code,"action_type":row.action_type})
    return serialize_service_action(row)

@router.patch("/projects/{project_code}/field-intelligence/service-actions/{action_id}")
def update_field_service_action(project_code: str, action_id: str, req: FieldServiceActionUpdateRequest, identity: Identity = Depends(get_identity), db: Session = Depends(get_db)):
    _assurance_admin(identity)
    project, visible_doc_ids, visible_parts, allowed_areas = _launch_project_context(db, project_code, identity)
    row=db.get(FieldServiceAction,action_id)
    if not row or row.project_code!=project.code or (row.manufacturing_area and row.manufacturing_area not in allowed_areas) or not _validate_field_action_visibility(row,visible_doc_ids,visible_parts): raise HTTPException(404,"Field service action not found")
    values=req.model_dump(exclude_unset=True)
    approve=values.pop("approve",None)
    if "evidence_document_ids" in values: values["evidence_document_ids"]=_validate_quality_evidence(db,project,visible_doc_ids,values["evidence_document_ids"])
    if "applicability" in values: values["applicability_json"]=values.pop("applicability")
    if "suspect_vehicle_identifiers" in values: values["suspect_vehicle_identifiers"]=list(dict.fromkeys(values["suspect_vehicle_identifiers"] or []))
    if approve is True:
        values["approved_by"]=identity.user; values["approved_at"]=datetime.now().astimezone()
    elif approve is False:
        values["approved_by"]=None; values["approved_at"]=None
    for k,v in values.items(): setattr(row,k,v)
    db.commit();db.refresh(row);log_event(db,identity.user,"FIELD_SERVICE_ACTION_UPDATED","project",project.code,{"id":row.id,"fields":sorted(values)})
    return serialize_service_action(row)

