"""Shared HTTP handler dependencies and ACL helpers.

This module is intentionally route-free. Bounded-context handler modules import this
namespace so security/visibility rules stay centralized while route ownership is split.
"""
import hashlib

import mimetypes

import shutil

from datetime import datetime

from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, Response

from fastapi.responses import FileResponse

from sqlalchemy import func, select

from sqlalchemy.orm import Session

from app.core.config import get_settings

from app.core.security import Identity, get_identity, is_engineering_admin

from app.db.models import APQPDeliverable, AuditEvent, BOMItem, ChangeRequest, ComputeJob, ControlPlanItem, DesignReview, Document, EngineeringRequirement, EvidencePack, LaunchReadinessItem, LaunchTrial, ManufacturingLine, Part, PartRevision, PFMEAItem, PPAPSubmission, Problem8D, ProcessAsset, ProcessDefect, ProcessOperation, ProcessParameter, ProcessStation, Project, ProjectArea, ProjectMilestone, RequirementVerification, ReviewApproval, ReviewStatus, SpecialCharacteristic, ValidationIssue, LocalizationItem, IncomingQualityRecord, CostBaseline, CostLine, SupplierQuotation, ArchitectureNode, InterfaceDefinition, InterfaceVerification, VehicleVariant, ConfigurationApplicability, ReleaseBaseline, EngineeringLesson, EngineeringDecisionRecord, ProductionFeedback, ChangeEffectivenessReview, EngineeringDeviation, EngineeringRisk, ProgramDependency, ManufacturingBOMItem, ConfigurationEffectivity, ChangeCutIn, AsBuiltConfiguration, PartSupersession, VehicleBuild, BuildGenealogyItem, BuildDefectLink, SafeLaunchControl, SeriesQualityObservation, ProcessCapabilityRecord, SeriesContainmentCase, FieldQualityClaim, DesignFMEAItem, FieldReliabilityExposure, FieldServiceAction, EngineeringWorkflowCase

from app.db.models import EngineeringTranslationMemory, WorkInstruction, ManufacturingLayout, StationLayoutPlacement
from app.schemas.api import (BOMTranslationRequest, ProcessStationUpdateRequest, WorkInstructionCreateRequest,
    WorkInstructionImportRequest, WorkInstructionUpdateRequest, EngineeringTranslationRequest, TranslationReviewRequest,
    WorkInstructionAskRequest, ManufacturingLayoutCreateRequest, StationLayoutPlacementRequest)

from app.db.session import get_db

from app.schemas.api import APQPDeliverableCreateRequest, APQPDeliverableUpdateRequest, AgentRequest, ApprovalRequest, AskRequest, AskResponse, ChangeSimulationRequest, DigitalThreadAskRequest, ChangeCompleteRequest, ChangeCreateRequest, ChangeDecisionRequest, ChangeImplementationRequest, ControlPlanItemCreateRequest, ControlPlanItemUpdateRequest, DesignReviewRequest, DocumentActivityNoteRequest, EngineeringRequirementCreateRequest, EngineeringRequirementUpdateRequest, EvidencePackRequest, ImpactRequest, IssueUpdate, LaunchReadinessItemCreateRequest, LaunchReadinessItemUpdateRequest, LaunchTrialCreateRequest, LaunchTrialUpdateRequest, ManufacturingLineCreateRequest, MilestoneCreateRequest, MilestoneUpdateRequest, PFMEAItemCreateRequest, PFMEAItemUpdateRequest, PPAPCreateRequest, PPAPUpdateRequest, Problem8DCreateRequest, Problem8DUpdateRequest, ProcessAssetCreateRequest, ProcessDefectCreateRequest, ProcessDefectUpdateRequest, ProcessOperationCreateRequest, ProcessParameterCreateRequest, ProcessStationCreateRequest, ProjectAreaUpdateRequest, ProjectCreateRequest, ProjectUpdateRequest, DocumentAreaUpdateRequest, RequirementVerificationCreateRequest, RequirementVerificationUpdateRequest, LocalizationItemCreateRequest, LocalizationItemUpdateRequest, IncomingQualityCreateRequest, IncomingQualityUpdateRequest, CostBaselineCreateRequest, CostBaselineUpdateRequest, CostLineCreateRequest, CostLineUpdateRequest, SupplierQuotationCreateRequest, SupplierQuotationUpdateRequest, ArchitectureNodeCreateRequest, ArchitectureNodeUpdateRequest, InterfaceCreateRequest, InterfaceUpdateRequest, InterfaceVerificationCreateRequest, InterfaceVerificationUpdateRequest, VehicleVariantCreateRequest, VehicleVariantUpdateRequest, ConfigurationApplicabilityCreateRequest, ConfigurationApplicabilityUpdateRequest, ReleaseBaselineCreateRequest, KnowledgeMemoryAskRequest, KnowledgeLessonPromoteRequest, KnowledgeLessonUpdateRequest, EngineeringDecisionCreateRequest, EngineeringDecisionUpdateRequest, ProductionFeedbackCreateRequest, ChangeEffectivenessCreateRequest, EngineeringDeviationCreateRequest, EngineeringDeviationUpdateRequest, EngineeringRiskCreateRequest, EngineeringRiskUpdateRequest, ProgramDependencyCreateRequest, ProgramDependencyUpdateRequest, ProgramSlipSimulationRequest, ManufacturingBOMItemCreateRequest, ConfigurationEffectivityCreateRequest, ChangeCutInCreateRequest, AsBuiltConfigurationCreateRequest, PartSupersessionCreateRequest, ConfigurationAssuranceAskRequest, VehicleBuildCreateRequest, BuildGenealogyCreateRequest, BuildDefectLinkCreateRequest, SafeLaunchControlCreateRequest, SafeLaunchControlUpdateRequest, SeriesQualityObservationCreateRequest, ProcessCapabilityCreateRequest, SuspectPopulationRequest, SeriesContainmentCreateRequest, SeriesContainmentUpdateRequest, FieldQualityClaimCreateRequest, SeriesIntelligenceAskRequest, FieldReliabilityExposureCreateRequest, DesignFMEAItemCreateRequest, FieldServiceActionCreateRequest, FieldServiceActionUpdateRequest, FieldReliabilityAskRequest, EngineeringWorkflowCreateRequest, EngineeringWorkflowUpdateRequest, EngineeringOSAskRequest, SearchHit, SearchRequest, SpecialCharacteristicCreateRequest, SpecialCharacteristicUpdateRequest











































def _allowed(doc: Document, identity: Identity) -> bool:
    return bool(set(doc.acl_groups or ["all"]) & set(identity.groups + ["all"]))

def _is_admin(identity: Identity) -> bool:
    return is_engineering_admin(identity)

def _visible_docs(db: Session, identity: Identity) -> list[Document]:
    return [d for d in db.scalars(select(Document)).all() if _allowed(d, identity)]

def _visible_docs_for_area(db: Session, identity: Identity, manufacturing_area: str | None) -> list[Document]:
    docs = _visible_docs(db, identity)
    if not manufacturing_area:
        return docs
    explicit_parts = {d.part_number for d in docs if d.manufacturing_area == manufacturing_area and d.part_number}
    return [d for d in docs if d.manufacturing_area == manufacturing_area or (not d.manufacturing_area and (not d.part_number or d.part_number in explicit_parts or d.doc_type == "bom"))]

def _merge_visible_metadata(docs: list[Document]) -> dict:
    out: dict = {}
    conflicts: dict[str, list] = {}
    for d in docs:
        for key, value in (d.extracted_metadata or {}).items():
            if key.startswith("_") or value in (None, "", [], {}):
                continue
            if key not in out:
                out[key] = value
            elif out[key] != value:
                conflicts.setdefault(key, [out[key]])
                if value not in conflicts[key]:
                    conflicts[key].append(value)
    for key, values in conflicts.items():
        out[key] = {"conflict": values}
    return out

def _visible_ids(db: Session, identity: Identity) -> set[str]:
    return {d.id for d in _visible_docs(db, identity)}

def serialize_doc(doc: Document) -> dict:
    return {
        "id": doc.id, "filename": doc.filename, "mime_type": doc.mime_type, "extension": doc.extension,
        "size_bytes": doc.size_bytes, "sha256": doc.sha256, "status": doc.status.value, "error": doc.error,
        "part_number": doc.part_number, "revision": doc.revision, "doc_type": doc.doc_type,
        "project_code": doc.project_code, "manufacturing_area": doc.manufacturing_area, "acl_groups": doc.acl_groups, "metadata": doc.extracted_metadata,
        "indexed_chunks": doc.indexed_chunks, "has_preview": bool(doc.preview_path), "source_path": doc.source_path,
        "created_at": doc.created_at.isoformat(), "updated_at": doc.updated_at.isoformat(),
    }

def _get_visible_change(db: Session, change_id: str, identity: Identity) -> ChangeRequest:
    change = db.get(ChangeRequest, change_id)
    if not change:
        raise HTTPException(404)
    visible_docs = _visible_docs(db, identity)
    if change.part_number and not any(d.part_number == change.part_number for d in visible_docs):
        raise HTTPException(404)
    return change

def _serialize_change_with_configuration(db: Session, change: ChangeRequest, identity: Identity, include_history: bool = False) -> dict:
    from app.services.configuration_management import configuration_impact
    from app.services.engineering_change import serialize_change
    payload=serialize_change(db,change,include_history=include_history)
    if change.part_number:
        part=db.scalar(select(Part).where(Part.part_number==change.part_number))
        if part and part.project_code:
            try:
                project, visible_doc_ids, visible_parts, allowed_areas=_launch_project_context(db,part.project_code,identity,None)
                if change.part_number in visible_parts:
                    payload["configuration_impact"]=configuration_impact(db,project.code,change.part_number,visible_doc_ids,visible_parts,None,allowed_areas)
            except HTTPException:
                pass
    return payload

def _parse_iso_datetime(value: str | None):
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise HTTPException(400, f"Invalid ISO datetime: {value}") from exc

def _get_visible_project(db: Session, code: str, identity: Identity) -> Project:
    from app.services.project_workspace import project_allowed
    project = db.scalar(select(Project).where(Project.code == code.upper()))
    if not project or not project_allowed(project, identity.groups):
        raise HTTPException(404, "Project not found")
    return project

def _quality_project_context(db: Session, project_code: str, identity: Identity, manufacturing_area: str | None = None):
    from app.services.manufacturing_areas import area_allowed, ensure_project_areas, valid_area
    project = _get_visible_project(db, project_code, identity)
    ensure_project_areas(db, project)
    if manufacturing_area:
        if not valid_area(manufacturing_area):
            raise HTTPException(400, "Unknown manufacturing area")
        area = db.scalar(select(ProjectArea).where(ProjectArea.project_code == project.code, ProjectArea.code == manufacturing_area))
        if not area or not area_allowed(area, identity.groups):
            raise HTTPException(404, "Manufacturing area not found")
    visible_docs = [d for d in _visible_docs(db, identity) if d.project_code == project.code]
    visible_doc_ids = {d.id for d in visible_docs}
    visible_parts = {d.part_number for d in visible_docs if d.part_number}
    return project, visible_doc_ids, visible_parts

def _validate_quality_area(db: Session, project: Project, identity: Identity, area_code: str | None) -> None:
    from app.services.manufacturing_areas import area_allowed, valid_area
    if not area_code:
        return
    if not valid_area(area_code):
        raise HTTPException(400, "Unknown manufacturing area")
    area = db.scalar(select(ProjectArea).where(ProjectArea.project_code == project.code, ProjectArea.code == area_code))
    if not area or not area_allowed(area, identity.groups):
        raise HTTPException(403, "No access to manufacturing area")

def _validate_quality_part(part_number: str | None, visible_parts: set[str]) -> str | None:
    if not part_number:
        return None
    pn = part_number.upper()
    if pn not in visible_parts:
        raise HTTPException(404, "Part not found in visible project evidence")
    return pn

def _validate_quality_evidence(db: Session, project: Project, visible_doc_ids: set[str], ids: list[str] | None) -> list[str]:
    values = list(dict.fromkeys(ids or []))
    for document_id in values:
        doc = db.get(Document, document_id)
        if not doc or doc.id not in visible_doc_ids or doc.project_code != project.code:
            raise HTTPException(404, "Evidence document not found")
    return values

def _validate_characteristic_refs(db: Session, project_code: str, ids: list[str] | None, visible_parts: set[str]) -> list[str]:
    values = list(dict.fromkeys(ids or []))
    for item_id in values:
        ch = db.get(SpecialCharacteristic, item_id)
        if not ch or ch.project_code != project_code or (ch.part_number and ch.part_number not in visible_parts):
            raise HTTPException(404, "Special characteristic not found")
    return values

def _validate_process_operation_ref(db: Session, project: Project, identity: Identity, visible_parts: set[str], operation_id: str | None, requested_area: str | None = None) -> str | None:
    if not operation_id:
        return None
    op = db.get(ProcessOperation, operation_id)
    if not op or (op.part_number and op.part_number not in visible_parts):
        raise HTTPException(404, "Process operation not found")
    station = db.get(ProcessStation, op.station_id)
    line = db.get(ManufacturingLine, station.line_id) if station else None
    if not station or not line or line.project_code != project.code:
        raise HTTPException(404, "Process operation not found")
    _validate_quality_area(db, project, identity, line.manufacturing_area)
    if requested_area and line.manufacturing_area != requested_area:
        raise HTTPException(400, "Process operation belongs to another manufacturing area")
    return op.id

def _process_line_context(db: Session, project: Project, identity: Identity, line_id: str) -> ManufacturingLine:
    line = db.get(ManufacturingLine, line_id)
    if not line or line.project_code != project.code:
        raise HTTPException(404, "Manufacturing line not found")
    _validate_quality_area(db, project, identity, line.manufacturing_area)
    return line

def _process_station_context(db: Session, project: Project, identity: Identity, station_id: str) -> tuple[ProcessStation, ManufacturingLine]:
    station = db.get(ProcessStation, station_id)
    if not station:
        raise HTTPException(404, "Process station not found")
    line = _process_line_context(db, project, identity, station.line_id)
    return station, line

def _process_operation_context(db: Session, project: Project, identity: Identity, visible_parts: set[str], operation_id: str) -> tuple[ProcessOperation, ProcessStation, ManufacturingLine]:
    op = db.get(ProcessOperation, operation_id)
    if not op or (op.part_number and op.part_number not in visible_parts):
        raise HTTPException(404, "Process operation not found")
    station, line = _process_station_context(db, project, identity, op.station_id)
    return op, station, line

def _launch_project_context(db: Session, project_code: str, identity: Identity, manufacturing_area: str | None = None):
    from app.services.manufacturing_areas import ensure_project_areas, visible_project_areas
    project = _get_visible_project(db, project_code, identity)
    ensure_project_areas(db, project)
    visible_areas = visible_project_areas(db, project, identity.groups)
    allowed_areas = {a.code for a in visible_areas}
    if manufacturing_area:
        if manufacturing_area not in allowed_areas:
            raise HTTPException(404, "Manufacturing area not found")
    docs = [d for d in _visible_docs(db, identity) if d.project_code == project.code and (not d.manufacturing_area or d.manufacturing_area in allowed_areas)]
    if manufacturing_area:
        explicit_parts = {d.part_number for d in docs if d.manufacturing_area == manufacturing_area and d.part_number}
        docs = [d for d in docs if d.manufacturing_area == manufacturing_area or (not d.manufacturing_area and (not d.part_number or d.part_number in explicit_parts or d.doc_type == "bom"))]
    return project, {d.id for d in docs}, {d.part_number for d in docs if d.part_number}, allowed_areas

def _validate_launch_line(db: Session, project: Project, identity: Identity, line_id: str | None, manufacturing_area: str | None = None) -> str | None:
    if not line_id:
        return None
    line = _process_line_context(db, project, identity, line_id)
    if manufacturing_area and line.manufacturing_area != manufacturing_area:
        raise HTTPException(400, "Launch item line belongs to another manufacturing area")
    return line.id

def _requirement_context(db: Session, project_code: str, identity: Identity, manufacturing_area: str | None = None):
    return _launch_project_context(db, project_code, identity, manufacturing_area)

def _get_visible_requirement(db: Session, project: Project, requirement_id: str, visible_doc_ids: set[str], visible_parts: set[str], identity: Identity) -> EngineeringRequirement:
    row = db.get(EngineeringRequirement, requirement_id)
    if not row or row.project_code != project.code:
        raise HTTPException(404, "Requirement not found")
    if row.manufacturing_area:
        _validate_quality_area(db, project, identity, row.manufacturing_area)
    if row.source_document_id and row.source_document_id not in visible_doc_ids:
        raise HTTPException(404, "Requirement not found")
    if row.part_numbers and not (set(row.part_numbers) & visible_parts):
        raise HTTPException(404, "Requirement not found")
    return row

def _validate_requirement_parts(part_numbers: list[str], visible_parts: set[str]) -> list[str]:
    normalized = sorted({x.strip().upper() for x in (part_numbers or []) if x and x.strip()})
    missing = [x for x in normalized if x not in visible_parts]
    if missing:
        raise HTTPException(404, f"Part not found in visible project evidence: {missing[0]}")
    return normalized

def _validate_requirement_changes(db: Session, ids: list[str], visible_parts: set[str]) -> list[str]:
    out=[]
    for cid in ids or []:
        row=db.get(ChangeRequest,cid)
        if not row or row.part_number not in visible_parts:
            raise HTTPException(404, "Linked change not found")
        out.append(row.id)
    return sorted(set(out))

def _validate_verification_links(db: Session, project: Project, visible_parts: set[str], launch_trial_id: str | None, design_review_id: str | None, linked_change_id: str | None):
    launch=None; review=None; change=None
    if launch_trial_id:
        launch=db.get(LaunchTrial,launch_trial_id)
        if not launch or launch.project_code!=project.code or (launch.part_number and launch.part_number not in visible_parts):
            raise HTTPException(404,"Launch trial not found")
    if design_review_id:
        review=db.get(DesignReview,design_review_id)
        if not review or review.part_number not in visible_parts:
            raise HTTPException(404,"Design Review not found")
    if linked_change_id:
        change=db.get(ChangeRequest,linked_change_id)
        if not change or change.part_number not in visible_parts:
            raise HTTPException(404,"Linked change not found")
    return launch,review,change

def _verification_has_proof(status: str, evidence: list[str], launch, review) -> bool:
    if status != "passed":
        return True
    review_status = getattr(review.status,"value",review.status) if review else None
    return bool(evidence or (launch and launch.status=="passed") or (review and review_status=="approved"))

def _localization_context(db: Session, project_code: str, identity: Identity, manufacturing_area: str | None = None):
    return _launch_project_context(db, project_code, identity, manufacturing_area)

def _get_visible_localization_item(db: Session, project: Project, item_id: str, visible_parts: set[str], identity: Identity) -> LocalizationItem:
    row = db.get(LocalizationItem, item_id)
    if not row or row.project_code != project.code or row.part_number not in visible_parts:
        raise HTTPException(404, "Localization item not found")
    _validate_quality_area(db, project, identity, row.manufacturing_area)
    return row

def _validate_supplier_8d(db: Session, project: Project, visible_parts: set[str], problem_id: str | None):
    if not problem_id:
        return None
    row = db.get(Problem8D, problem_id)
    if not row or row.project_code != project.code or (row.part_number and row.part_number not in visible_parts):
        raise HTTPException(404, "8D not found")
    return row.id

def _cost_context(db: Session, project_code: str, identity: Identity, manufacturing_area: str | None = None):
    return _launch_project_context(db, project_code, identity, manufacturing_area)

def _get_visible_cost_baseline(db: Session, project: Project, baseline_id: str, identity: Identity) -> CostBaseline:
    row = db.get(CostBaseline, baseline_id)
    if not row or row.project_code != project.code:
        raise HTTPException(404, "Cost baseline not found")
    _validate_quality_area(db, project, identity, row.manufacturing_area)
    return row

def _validate_cost_change(db: Session, visible_parts: set[str], change_id: str | None):
    if not change_id:
        return None
    row = db.get(ChangeRequest, change_id)
    if not row or (row.part_number and row.part_number not in visible_parts):
        raise HTTPException(404, "Engineering change not found")
    return row.id

def _architecture_context(db: Session, project_code: str, identity: Identity, manufacturing_area: str | None = None):
    return _launch_project_context(db, project_code, identity, manufacturing_area)

def _get_arch_node(db: Session, project: Project, node_id: str, identity: Identity, visible_parts: set[str]) -> ArchitectureNode:
    row = db.get(ArchitectureNode, node_id)
    if not row or row.project_code != project.code:
        raise HTTPException(404, "Architecture node not found")
    _validate_quality_area(db, project, identity, row.manufacturing_area)
    if row.part_number and row.part_number not in visible_parts:
        raise HTTPException(404, "Architecture node not found")
    visible_ids=_visible_ids(db, identity)
    if row.evidence_document_ids and not set(row.evidence_document_ids).issubset(visible_ids):
        raise HTTPException(404, "Architecture node not found")
    return row

def _arch_evidence(db: Session, project: Project, visible_doc_ids: set[str], ids: list[str] | None) -> list[str]:
    return _validate_quality_evidence(db, project, visible_doc_ids, ids)

def _arch_requirements(db: Session, project: Project, ids: list[str] | None, visible_doc_ids: set[str], visible_parts: set[str], identity: Identity) -> list[str]:
    out=[]
    for rid in ids or []:
        row=_get_visible_requirement(db,project,rid,visible_doc_ids,visible_parts,identity)
        out.append(row.id)
    return sorted(set(out))

def _arch_changes(db: Session, ids: list[str] | None, visible_parts: set[str]) -> list[str]:
    return _validate_requirement_changes(db, ids or [], visible_parts)

def _get_interface(db: Session, project: Project, interface_id: str, identity: Identity, visible_parts: set[str]) -> InterfaceDefinition:
    row=db.get(InterfaceDefinition,interface_id)
    if not row or row.project_code!=project.code:
        raise HTTPException(404,"Interface not found")
    _validate_quality_area(db,project,identity,row.manufacturing_area)
    _get_arch_node(db,project,row.source_node_id,identity,visible_parts)
    _get_arch_node(db,project,row.target_node_id,identity,visible_parts)
    visible_ids=_visible_ids(db, identity)
    if row.evidence_document_ids and not set(row.evidence_document_ids).issubset(visible_ids):
        raise HTTPException(404, "Interface not found")
    return row

def _validate_linked_req_verification(db: Session, project: Project, verification_id: str | None, visible_doc_ids: set[str], visible_parts: set[str], identity: Identity):
    if not verification_id: return None
    row=db.get(RequirementVerification,verification_id)
    if not row or row.project_code!=project.code: raise HTTPException(404,"Requirement verification not found")
    req=_get_visible_requirement(db,project,row.requirement_id,visible_doc_ids,visible_parts,identity)
    return row

def _configuration_context(db: Session, project_code: str, identity: Identity, manufacturing_area: str | None = None):
    return _launch_project_context(db, project_code, identity, manufacturing_area)

def _get_variant(db: Session, project: Project, variant_id: str, identity: Identity, visible_doc_ids: set[str]) -> VehicleVariant:
    row=db.get(VehicleVariant,variant_id)
    if not row or row.project_code!=project.code: raise HTTPException(404,"Vehicle variant not found")
    _validate_quality_area(db,project,identity,row.manufacturing_area)
    if row.evidence_document_ids and not set(row.evidence_document_ids).issubset(visible_doc_ids): raise HTTPException(404,"Vehicle variant not found")
    return row

def _configuration_entity_key(db: Session, project: Project, req, identity: Identity, visible_doc_ids: set[str], visible_parts: set[str]):
    key=req.entity_key.strip()
    if req.entity_type=='part':
        key=key.upper()
        if key not in visible_parts: raise HTTPException(404,"Part not found")
    elif req.entity_type=='document':
        if key not in visible_doc_ids: raise HTTPException(404,"Document not found")
    elif req.entity_type=='architecture_node':
        _get_arch_node(db,project,key,identity,visible_parts)
    elif req.entity_type=='interface':
        _get_interface(db,project,key,identity,visible_parts)
    elif req.entity_type=='requirement':
        _get_visible_requirement(db,project,key,visible_doc_ids,visible_parts,identity)
    elif req.entity_type=='change':
        ch=db.get(ChangeRequest,key)
        if not ch or (ch.part_number and ch.part_number not in visible_parts): raise HTTPException(404,"Change not found")
    return key

def _knowledge_contexts(db: Session, current_project: Project, identity: Identity, manufacturing_area: str | None, scope: str):
    from app.services.engineering_knowledge_memory import accessible_memory_contexts
    try:
        return accessible_memory_contexts(db,current_project,identity.groups,_visible_docs(db,identity),manufacturing_area,scope)
    except ValueError as exc:
        raise HTTPException(400,str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(404,str(exc)) from exc

def _knowledge_cases(db: Session, project: Project, identity: Identity, manufacturing_area: str | None, scope: str):
    from app.services.engineering_knowledge_memory import collect_project_cases
    cases=[]
    for p, visible_doc_ids, visible_parts, allowed_areas in _knowledge_contexts(db, project, identity, manufacturing_area, scope):
        cases.extend(collect_project_cases(db,p.code,visible_doc_ids,visible_parts,manufacturing_area,allowed_areas,True))
    return cases

def _closed_loop_context(db: Session, project_code: str, identity: Identity, manufacturing_area: str | None = None):
    return _architecture_context(db, project_code, identity, manufacturing_area)

def _visible_evidence_or_400(ids: list[str], visible_doc_ids: set[str]):
    if not set(ids or []).issubset(visible_doc_ids):
        raise HTTPException(400, "Evidence document is unavailable or outside current ACL context")

def _visible_change_or_404(db: Session, change_id: str | None, visible_doc_ids: set[str], visible_parts: set[str]):
    if not change_id:
        return None
    row=db.get(ChangeRequest,change_id)
    if not row or (row.part_number and row.part_number not in visible_parts) or not set(row.affected_document_ids or []).issubset(visible_doc_ids):
        raise HTTPException(404,"Engineering change not found")
    return row

def _program_context(db: Session, project_code: str, identity: Identity, manufacturing_area: str | None = None):
    return _architecture_context(db, project_code, identity, manufacturing_area)

def _program_visible_milestone(db: Session, project_code: str, milestone_id: str, allowed_areas: set[str], manufacturing_area: str | None = None):
    row = db.get(ProjectMilestone, milestone_id)
    if not row or row.project_code != project_code:
        raise HTTPException(404, "Milestone not found")
    if row.manufacturing_area and row.manufacturing_area not in allowed_areas:
        raise HTTPException(404, "Milestone not found")
    if manufacturing_area and row.manufacturing_area not in {None, manufacturing_area}:
        raise HTTPException(404, "Milestone not found")
    return row

def _assurance_context(db: Session, project_code: str, identity: Identity, manufacturing_area: str | None = None):
    return _configuration_context(db, project_code, identity, manufacturing_area)

def _assurance_admin(identity: Identity):
    if not _is_admin(identity):
        raise HTTPException(403, "Engineering admin required for configuration-authority shadow data")

def _validate_field_action_visibility(row: FieldServiceAction, visible_doc_ids: set[str], visible_parts: set[str]) -> bool:
    return (not row.part_number or row.part_number in visible_parts) and set(row.evidence_document_ids or []).issubset(visible_doc_ids)

