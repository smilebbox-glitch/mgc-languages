"""Platform Operations HTTP handlers — v6.2.2.

Extracted from the former 3k-line route monolith. Public paths are unchanged.
"""
from fastapi import APIRouter
from datetime import datetime, timezone
from app.api import context_shared as _shared

# Preserve the mature shared handler namespace without duplicating service imports.
globals().update({k: v for k, v in vars(_shared).items() if not k.startswith("__")})
from app.services.manufacturing_areas import AREA_CATALOG

from app.db.models import EngineeringApprovalPolicy, EngineeringApprovalCase, EngineeringApprovalRecord, EngineeringIdentityPolicy, EngineeringIdentityDelegation, EngineeringHandoverTarget, EngineeringRetentionPolicy, EngineeringLegalHold, EngineeringPurgeRequest
from app.schemas.api import ApprovalPolicyCreateRequest, ApprovalDecisionRequest, IdentityPolicyCreateRequest, IdentityDelegationCreateRequest, HandoverTargetCreateRequest, RetentionPolicyCreateRequest, LegalHoldCreateRequest, LegalHoldReleaseRequest, LifecycleArchiveRequest, PurgeRequestCreateRequest
from app.services.approval_governance import submit_case, decide_case, serialize_case, governance_dashboard
from app.services.identity_policy import KNOWN_ACTIONS, DELEGATABLE_ACTIONS, apply_governance_rls_context, enforce_identity_policy
from app.core.security import identity_snapshot
from app.services.work_instructions import translation_is_current
from app.services.engineering_handover import create_target as create_handover_target, serialize_target as serialize_handover_target, handover_dashboard

from app.services.data_lifecycle import (
    SUPPORTED_ENTITY_TYPES, archive_entity, authorize_purge, create_policy as create_retention_policy,
    create_purge_request, evidence_lineage, execute_purge, lifecycle_dashboard, place_hold,
    release_hold, storage_usage,
)
from app.api.lazy_service import lazy_service

apply_audit_retention = lazy_service("app.services.enterprise_security", "apply_audit_retention")
audit_retention_preview = lazy_service("app.services.enterprise_security", "audit_retention_preview")
build_audit_export = lazy_service("app.services.enterprise_security", "build_audit_export")
can_view_job = lazy_service("app.services.compute_manager", "can_view_job")
infer_area_codes_from_groups = lazy_service("app.services.manufacturing_areas", "infer_area_codes_from_groups")
log_event = lazy_service("app.services.audit", "log_event")
security_posture = lazy_service("app.services.enterprise_security", "security_posture")
valid_area = lazy_service("app.services.manufacturing_areas", "valid_area")

router = APIRouter(tags=["context:platform_operations"])

from app.services.background_jobs import (JobRecoveryNotAllowed, dispatch_job as dispatch_compute_job, list_recovery_events, prepare_orphan_recovery, request_cancellation, retry_dead_letter, serialize_job as serialize_compute_job, workload_snapshot)

@router.get("/me")
def me(identity: Identity = Depends(get_identity)):
    return {
        "user": identity.user,
        "groups": [g for g in identity.groups if g != "all"],
        "is_engineer": True,
        "is_admin": is_engineering_admin(identity),
        "access_policy": "engineer_only",
        "identity_assurance": {"auth_mode": identity.auth_mode, "subject": identity.subject or identity.user, "acr": identity.acr, "client_id": identity.client_id, "is_service_account": identity.is_service_account},
        "manufacturing_areas": [{k:v for k,v in a.items() if k in {"code","name","short_name","icon"}} for a in AREA_CATALOG],
        "suggested_manufacturing_areas": infer_area_codes_from_groups(identity.groups),
    }

@router.get("/stats")
def stats(manufacturing_area: str | None = None, identity: Identity = Depends(get_identity), db: Session = Depends(get_db)):
    if not valid_area(manufacturing_area): raise HTTPException(400, "Unknown manufacturing area")
    docs = _visible_docs_for_area(db, identity, manufacturing_area)
    visible_parts = {d.part_number for d in docs if d.part_number}
    visible_doc_ids = {d.id for d in docs}
    issue_rows = db.scalars(select(ValidationIssue)).all()
    visible_issues = [i for i in issue_rows if not i.document_ids or bool(set(i.document_ids) & visible_doc_ids)]
    change_rows = db.scalars(select(ChangeRequest)).all()
    visible_changes = [c for c in change_rows if not c.part_number or c.part_number in visible_parts]
    return {
        "documents": len(docs), "ready_documents": sum(d.status.value == "ready" for d in docs),
        "cad_models": sum(d.doc_type == "cad" for d in docs), "parts": len(visible_parts),
        "open_issues": sum((i.status.value if hasattr(i.status, "value") else i.status) == "open" for i in visible_issues),
        "active_changes": sum(c.status not in {"implemented", "rejected", "cancelled"} for c in visible_changes),
        "indexed_chunks": sum(d.indexed_chunks or 0 for d in docs),
    }

@router.get("/audit")
def audit(limit: int = 100, identity: Identity = Depends(get_identity), db: Session = Depends(get_db)):
    if not _is_admin(identity): raise HTTPException(403, "Admin group required")
    rows = db.scalars(select(AuditEvent).order_by(AuditEvent.created_at.desc()).limit(min(limit, 500))).all()
    return [{"id": e.id, "user": e.user, "action": e.action, "entity_type": e.entity_type, "entity_id": e.entity_id, "details": e.details, "created_at": e.created_at.isoformat()} for e in rows]

@router.get("/security/posture")
def enterprise_security_posture(identity: Identity = Depends(get_identity)):
    if not _is_admin(identity): raise HTTPException(403, "Admin group required")
    return security_posture()

@router.get("/security/audit/export")
def enterprise_audit_export(limit: int = 5000, identity: Identity = Depends(get_identity), db: Session = Depends(get_db)):
    if not _is_admin(identity): raise HTTPException(403, "Admin group required")
    payload, manifest = build_audit_export(db, limit=limit)
    log_event(db, identity.user, "AUDIT_EXPORT", "audit", details={"row_count": manifest["row_count"], "sha256": manifest["sha256"]})
    return Response(
        content=payload,
        media_type="application/x-ndjson",
        headers={
            "X-MGC-Audit-SHA256": manifest["sha256"],
            "X-MGC-Audit-Chain-Head": manifest["chain_head"],
            "X-MGC-Audit-Row-Count": str(manifest["row_count"]),
        },
    )

@router.get("/security/audit/retention")
def enterprise_audit_retention_preview(identity: Identity = Depends(get_identity), db: Session = Depends(get_db)):
    if not _is_admin(identity): raise HTTPException(403, "Admin group required")
    return audit_retention_preview(db)

@router.post("/security/audit/retention")
def enterprise_audit_retention_apply(confirm: str, identity: Identity = Depends(get_identity), db: Session = Depends(get_db)):
    if not _is_admin(identity): raise HTTPException(403, "Admin group required")
    try:
        return apply_audit_retention(db, confirm=confirm, actor=identity.user)
    except ValueError as exc:
        raise HTTPException(400, str(exc))

@router.get("/compute/tasks/{job_id}")
def compute_task_status(job_id: str, identity: Identity = Depends(get_identity), db: Session = Depends(get_db)):
    job = db.get(ComputeJob, job_id)
    admin = _is_admin(identity)
    if not job or not can_view_job(job.user, identity.user, admin):
        raise HTTPException(404)
    return serialize_compute_job(job, include_result=True, admin=admin)

@router.get("/compute/tasks")
def list_compute_tasks(limit: int = 50, identity: Identity = Depends(get_identity), db: Session = Depends(get_db)):
    q = select(ComputeJob).order_by(ComputeJob.created_at.desc()).limit(min(max(limit, 1), 200))
    if not _is_admin(identity):
        q = q.where(ComputeJob.user == identity.user)
    rows = db.scalars(q).all()
    return [serialize_compute_job(x, include_result=False, admin=_is_admin(identity)) for x in rows]

@router.post("/compute/tasks/{job_id}/cancel")
def cancel_compute_task(job_id: str, identity: Identity = Depends(get_identity), db: Session = Depends(get_db)):
    job = db.get(ComputeJob, job_id)
    admin = _is_admin(identity)
    if not job or not can_view_job(job.user, identity.user, admin):
        raise HTTPException(404)
    request_cancellation(db, job)
    if get_settings().job_cancel_revoke_enabled and job.celery_task_id:
        try:
            from app.workers.celery_app import celery
            celery.control.revoke(job.celery_task_id, terminate=False)
        except Exception:
            pass
    log_event(db, identity.user, "COMPUTE_JOB_CANCEL_REQUESTED", "compute_job", job.id, {"kind": job.kind, "state": job.status})
    return serialize_compute_job(job, admin=admin)

@router.get("/operations/workload")
def operations_workload(identity: Identity = Depends(get_identity), db: Session = Depends(get_db)):
    if not _is_admin(identity): raise HTTPException(403, "Admin group required")
    return workload_snapshot(db)

@router.post("/operations/workload/{job_id}/retry")
def operations_retry_job(job_id: str, identity: Identity = Depends(get_identity), db: Session = Depends(get_db)):
    if not _is_admin(identity): raise HTTPException(403, "Admin group required")
    job = db.get(ComputeJob, job_id)
    if not job: raise HTTPException(404, "Compute job not found")
    try:
        retry_dead_letter(db, job)
        task = dispatch_compute_job(job)
        job.celery_task_id = task.id
        db.commit()
    except ValueError as exc:
        raise HTTPException(409, str(exc))
    log_event(db, identity.user, "COMPUTE_JOB_RETRIED", "compute_job", job.id, {"kind": job.kind, "resource_class": job.resource_class})
    return serialize_compute_job(job, admin=True)


@router.post("/operations/workload/{job_id}/recover")
def operations_recover_orphaned_job(job_id: str, confirm: str, identity: Identity = Depends(get_identity), db: Session = Depends(get_db)):
    if not _is_admin(identity): raise HTTPException(403, "Admin group required")
    job = db.get(ComputeJob, job_id)
    if not job: raise HTTPException(404, "Compute job not found")
    try:
        prepare_orphan_recovery(db, job, actor=identity.user, confirm=confirm)
        task = dispatch_compute_job(job, reason="manual_orphan_recovery")
        job.celery_task_id = task.id
        db.commit()
    except JobRecoveryNotAllowed as exc:
        raise HTTPException(409, str(exc))
    except ValueError as exc:
        raise HTTPException(409, str(exc))
    except Exception as exc:
        job.status = "orphaned"
        job.error = f"Manual recovery dispatch failed: {type(exc).__name__}: {exc}"[:1000]
        job.progress_message = "Ручное восстановление не доставлено; проверьте broker/worker"
        db.commit()
        raise HTTPException(503, "Recovery dispatch unavailable")
    log_event(db, identity.user, "COMPUTE_JOB_ORPHAN_RECOVERED", "compute_job", job.id, {"kind": job.kind, "resource_class": job.resource_class, "dispatch_generation": job.dispatch_generation})
    return serialize_compute_job(job, admin=True)


@router.get("/operations/workload/recovery-events")
def operations_workload_recovery_events(job_id: str | None = None, limit: int = 100, identity: Identity = Depends(get_identity), db: Session = Depends(get_db)):
    if not _is_admin(identity): raise HTTPException(403, "Admin group required")
    return {"items": list_recovery_events(db, job_id=job_id, limit=limit)}



# --- v6.3.5 Engineering Approval Governance ---
def _approval_entity_context(db: Session, project_code: str, entity_type: str, entity_id: str, identity: Identity):
    project = _get_visible_project(db, project_code, identity)
    if entity_type == "work_instruction":
        row = db.get(WorkInstruction, entity_id)
        if not row or row.project_code != project.code: raise HTTPException(404, "Work instruction not found")
        _validate_quality_area(db, project, identity, row.manufacturing_area)
        return row, row.manufacturing_area
    if entity_type == "manufacturing_layout":
        row = db.get(ManufacturingLayout, entity_id)
        if not row or row.project_code != project.code: raise HTTPException(404, "Layout not found")
        _validate_quality_area(db, project, identity, row.manufacturing_area)
        return row, row.manufacturing_area
    if entity_type == "engineering_change":
        row = _get_visible_change(db, entity_id, identity)
        meta = row.metadata_json or {}; area = meta.get("manufacturing_area")
        if area: _validate_quality_area(db, project, identity, area)
        return row, area
    if entity_type == "release_package":
        from app.db.models import EngineeringReleasePackage
        row=db.get(EngineeringReleasePackage,entity_id)
        if not row or row.project_code != project.code: raise HTTPException(404,"Release package not found")
        if row.manufacturing_area: _validate_quality_area(db,project,identity,row.manufacturing_area)
        return row,row.manufacturing_area
    raise HTTPException(400, "Unsupported approval entity type")

@router.get("/approval-policies")
def approval_policies(entity_type: str | None = None, identity: Identity = Depends(get_identity), db: Session = Depends(get_db)):
    if not _is_admin(identity): raise HTTPException(403, "Engineering Admin required")
    q = select(EngineeringApprovalPolicy).order_by(EngineeringApprovalPolicy.created_at.desc())
    rows = db.scalars(q).all()
    if entity_type: rows = [x for x in rows if x.entity_type == entity_type]
    return [{"id":x.id,"project_code":x.project_code,"manufacturing_area":x.manufacturing_area,"entity_type":x.entity_type,"name":x.name,"stages":x.stages_json or [],"maker_checker_required":x.maker_checker_required,"distinct_approvers_required":x.distinct_approvers_required,"active":x.active,"created_by":x.created_by,"created_at":x.created_at.isoformat()} for x in rows]

@router.post("/approval-policies")
def create_approval_policy(req: ApprovalPolicyCreateRequest, identity: Identity = Depends(get_identity), db: Session = Depends(get_db)):
    if not _is_admin(identity): raise HTTPException(403, "Engineering Admin required")
    apply_governance_rls_context(db, identity)
    try: enforce_identity_policy(db, identity, action="approval_policy_admin", project_code=req.project_code, manufacturing_area=req.manufacturing_area, entity_type=req.entity_type)
    except PermissionError as exc: raise HTTPException(403, str(exc))
    if req.project_code: _get_visible_project(db, req.project_code, identity)
    if req.project_code and req.manufacturing_area:
        _validate_quality_area(db, _get_visible_project(db, req.project_code, identity), identity, req.manufacturing_area)
    keys=[x.key for x in req.stages]
    if len(keys) != len(set(keys)): raise HTTPException(400, "Approval stage keys must be unique")
    if any(x.required_role == "group" and not x.required_groups for x in req.stages): raise HTTPException(400, "Group approval stage requires at least one required group")
    # one active policy per exact scope/entity; old policy remains as historical evidence.
    rows = db.scalars(select(EngineeringApprovalPolicy).where(EngineeringApprovalPolicy.entity_type==req.entity_type, EngineeringApprovalPolicy.active==True)).all()
    for old in rows:
        if old.project_code == req.project_code and old.manufacturing_area == req.manufacturing_area: old.active = False
    row = EngineeringApprovalPolicy(project_code=req.project_code, manufacturing_area=req.manufacturing_area, entity_type=req.entity_type, name=req.name.strip(), stages_json=[x.model_dump() for x in req.stages], maker_checker_required=req.maker_checker_required, distinct_approvers_required=req.distinct_approvers_required, active=True, created_by=identity.user)
    db.add(row); db.commit(); db.refresh(row)
    log_event(db, identity.user, "APPROVAL_POLICY_CREATED", "approval_policy", row.id, {"entity_type":row.entity_type,"project_code":row.project_code,"manufacturing_area":row.manufacturing_area})
    return {"id":row.id,"active":row.active,"entity_type":row.entity_type,"stages":row.stages_json}

@router.post("/projects/{project_code}/approvals/{entity_type}/{entity_id}/submit")
def submit_engineering_approval(project_code: str, entity_type: str, entity_id: str, identity: Identity = Depends(get_identity), db: Session = Depends(get_db)):
    row, area = _approval_entity_context(db, project_code, entity_type, entity_id, identity)
    if entity_type == "work_instruction":
        if row.status not in {"draft","in_review"}: raise HTTPException(409, "Work instruction must be draft/in_review before approval submission")
        if not row.station_id: raise HTTPException(409, "Work instruction must be linked to a station before approval")
        if not (row.steps_json or []): raise HTTPException(409, "Work instruction must contain explicit steps before approval")
        if row.source_language not in {"ru","auto"} and (row.translation_status != "reviewed" or not translation_is_current(row)):
            raise HTTPException(409, "Current reviewed Russian translation is required before approval")
    if entity_type == "manufacturing_layout":
        if row.status not in {"draft","in_review"}: raise HTTPException(409, "Layout must be draft/in_review before approval submission")
        placements=db.scalars(select(StationLayoutPlacement).where(StationLayoutPlacement.layout_id==row.id)).all()
        if not placements: raise HTTPException(409, "Layout must contain at least one station placement before approval")
    if entity_type in {"work_instruction","manufacturing_layout"}:
        row.status="in_review"; db.flush()
    apply_governance_rls_context(db, identity)
    try:
        enforce_identity_policy(db, identity, action="approval_submit", project_code=project_code, manufacturing_area=area, entity_type=entity_type)
        case = submit_case(db, entity_type=entity_type, entity_id=entity_id, project_code=project_code, manufacturing_area=area, submitted_by=identity.user, submitted_identity=identity_snapshot(identity))
    except PermissionError as exc:
        db.rollback(); raise HTTPException(403, str(exc))
    except (ValueError, LookupError) as exc:
        db.rollback(); raise HTTPException(409, str(exc))
    log_event(db, identity.user, "ENGINEERING_APPROVAL_SUBMITTED", entity_type, entity_id, {"case_id":case.id,"cycle_no":case.cycle_no,"snapshot_sha256":case.snapshot_sha256})
    return serialize_case(db, case)

@router.get("/approvals/{case_id}")
def get_engineering_approval(case_id: str, identity: Identity = Depends(get_identity), db: Session = Depends(get_db)):
    case=db.get(EngineeringApprovalCase,case_id)
    if not case: raise HTTPException(404, "Approval case not found")
    if case.project_code: _approval_entity_context(db, case.project_code, case.entity_type, case.entity_id, identity)
    return serialize_case(db,case)

@router.post("/approvals/{case_id}/decision")
def decide_engineering_approval(case_id: str, req: ApprovalDecisionRequest, identity: Identity = Depends(get_identity), db: Session = Depends(get_db)):
    case=db.get(EngineeringApprovalCase,case_id)
    if not case: raise HTTPException(404, "Approval case not found")
    if case.project_code: row,_=_approval_entity_context(db,case.project_code,case.entity_type,case.entity_id,identity)
    else: row=None
    records=db.scalars(select(EngineeringApprovalRecord).where(EngineeringApprovalRecord.case_id==case.id).order_by(EngineeringApprovalRecord.stage_order)).all()
    stages=(case.policy_snapshot_json or {}).get("stages") or []
    next_stage=stages[len(records)] if len(records) < len(stages) else {}
    apply_governance_rls_context(db, identity)
    try:
        pd=enforce_identity_policy(db, identity, action="approval_decision", project_code=case.project_code, manufacturing_area=case.manufacturing_area, entity_type=case.entity_type, allow_delegation=bool(next_stage.get("delegation_allowed",False)))
        case=decide_case(db,case,user=identity.user,groups=pd.effective_groups,is_admin=_is_admin(identity),decision=req.decision,comment=req.comment,identity_snapshot_payload=pd.identity,assurance_payload={**pd.assurance,"identity_policy_id":pd.policy_id,"delegation_ids":pd.delegation_ids})
    except PermissionError as exc: raise HTTPException(403,str(exc))
    except ValueError as exc: raise HTTPException(409,str(exc))
    if row is not None and case.status == "approved" and case.entity_type in {"work_instruction","manufacturing_layout"}:
        row.status="approved"
        if case.entity_type == "work_instruction": row.approved_by=identity.user
        db.commit()
    elif row is not None and case.status == "rejected" and case.entity_type in {"work_instruction","manufacturing_layout"}:
        row.status="draft"; db.commit()
    log_event(db, identity.user, "ENGINEERING_APPROVAL_DECISION", case.entity_type, case.entity_id, {"case_id":case.id,"decision":req.decision,"case_status":case.status})
    return serialize_case(db,case)

@router.get("/governance/summary")
def approval_governance_summary(identity: Identity = Depends(get_identity), db: Session = Depends(get_db)):
    if not _is_admin(identity): raise HTTPException(403, "Engineering Admin required")
    return governance_dashboard(db)


# --- v6.3.6 Enterprise Identity & Policy Enforcement ---
@router.get("/identity/policies")
def identity_policies(action: str | None = None, identity: Identity = Depends(get_identity), db: Session = Depends(get_db)):
    if not _is_admin(identity): raise HTTPException(403, "Engineering Admin required")
    apply_governance_rls_context(db, identity)
    rows=db.scalars(select(EngineeringIdentityPolicy).order_by(EngineeringIdentityPolicy.created_at.desc())).all()
    if action: rows=[x for x in rows if x.action==action]
    return [{"id":x.id,"project_code":x.project_code,"manufacturing_area":x.manufacturing_area,"entity_type":x.entity_type,"action":x.action,"name":x.name,"allowed_groups":x.allowed_groups_json or [],"denied_groups":x.denied_groups_json or [],"required_acr_values":x.required_acr_values_json or [],"require_oidc":x.require_oidc,"max_auth_age_seconds":x.max_auth_age_seconds,"allow_service_accounts":x.allow_service_accounts,"delegation_allowed":x.delegation_allowed,"active":x.active,"created_by":x.created_by,"created_at":x.created_at.isoformat()} for x in rows]

@router.post("/identity/policies")
def create_identity_policy(req: IdentityPolicyCreateRequest, identity: Identity = Depends(get_identity), db: Session = Depends(get_db)):
    if not _is_admin(identity): raise HTTPException(403, "Engineering Admin required")
    if req.action not in KNOWN_ACTIONS: raise HTTPException(400, "Unknown controlled identity-policy action")
    apply_governance_rls_context(db, identity)
    try: enforce_identity_policy(db, identity, action="identity_policy_admin", project_code=req.project_code, manufacturing_area=req.manufacturing_area, entity_type=req.entity_type)
    except PermissionError as exc: raise HTTPException(403, str(exc))
    if req.project_code: _get_visible_project(db, req.project_code, identity)
    if set(req.allowed_groups) & set(req.denied_groups): raise HTTPException(400, "A group cannot be both allowed and denied")
    rows=db.scalars(select(EngineeringIdentityPolicy).where(EngineeringIdentityPolicy.action==req.action,EngineeringIdentityPolicy.active==True)).all()
    for old in rows:
        if old.project_code==req.project_code and old.manufacturing_area==req.manufacturing_area and old.entity_type==req.entity_type: old.active=False
    row=EngineeringIdentityPolicy(project_code=req.project_code,manufacturing_area=req.manufacturing_area,entity_type=req.entity_type,action=req.action,name=req.name.strip(),allowed_groups_json=sorted(set(req.allowed_groups)),denied_groups_json=sorted(set(req.denied_groups)),required_acr_values_json=sorted(set(req.required_acr_values)),require_oidc=req.require_oidc,max_auth_age_seconds=req.max_auth_age_seconds,allow_service_accounts=req.allow_service_accounts,delegation_allowed=req.delegation_allowed,active=True,created_by=identity.user)
    db.add(row); db.commit(); db.refresh(row)
    log_event(db, identity.user, "IDENTITY_POLICY_CREATED", "identity_policy", row.id, {"action":row.action,"project_code":row.project_code,"manufacturing_area":row.manufacturing_area})
    return {"id":row.id,"active":row.active,"action":row.action}

@router.get("/identity/delegations")
def identity_delegations(identity: Identity = Depends(get_identity), db: Session = Depends(get_db)):
    apply_governance_rls_context(db, identity)
    q=select(EngineeringIdentityDelegation).order_by(EngineeringIdentityDelegation.created_at.desc())
    rows=db.scalars(q).all()
    if not _is_admin(identity): rows=[x for x in rows if x.delegate==identity.user or x.delegator==identity.user]
    return [{"id":x.id,"delegator":x.delegator,"delegate":x.delegate,"project_code":x.project_code,"manufacturing_area":x.manufacturing_area,"entity_type":x.entity_type,"actions":x.actions_json or [],"delegated_groups":x.delegated_groups_json or [],"valid_from":x.valid_from.isoformat(),"valid_until":x.valid_until.isoformat(),"reason":x.reason,"revoked_at":x.revoked_at.isoformat() if x.revoked_at else None,"created_by":x.created_by} for x in rows]

@router.post("/identity/delegations")
def create_identity_delegation(req: IdentityDelegationCreateRequest, identity: Identity = Depends(get_identity), db: Session = Depends(get_db)):
    if not _is_admin(identity): raise HTTPException(403, "Engineering Admin required")
    apply_governance_rls_context(db, identity)
    try: enforce_identity_policy(db, identity, action="delegation_admin", project_code=req.project_code, manufacturing_area=req.manufacturing_area, entity_type=req.entity_type)
    except PermissionError as exc: raise HTTPException(403, str(exc))
    if req.delegator==req.delegate: raise HTTPException(400, "Delegator and delegate must be different identities")
    if any(a not in DELEGATABLE_ACTIONS for a in req.actions): raise HTTPException(400, "Only explicitly delegatable actions may be delegated")
    if set(req.delegated_groups) & get_settings().engineering_admin_group_set: raise HTTPException(400, "Engineering Admin authority cannot be delegated")
    start=req.valid_from or datetime.now(timezone.utc)
    end=req.valid_until
    if end.tzinfo is None: end=end.replace(tzinfo=timezone.utc)
    if start.tzinfo is None: start=start.replace(tzinfo=timezone.utc)
    if end <= start: raise HTTPException(400, "Delegation valid_until must be after valid_from")
    row=EngineeringIdentityDelegation(delegator=req.delegator,delegate=req.delegate,project_code=req.project_code,manufacturing_area=req.manufacturing_area,entity_type=req.entity_type,actions_json=sorted(set(req.actions)),delegated_groups_json=sorted(set(req.delegated_groups)),valid_from=start,valid_until=end,reason=req.reason.strip(),created_by=identity.user)
    db.add(row); db.commit(); db.refresh(row)
    log_event(db, identity.user, "IDENTITY_DELEGATION_CREATED", "identity_delegation", row.id, {"delegate":row.delegate,"actions":row.actions_json})
    return {"id":row.id,"delegate":row.delegate,"valid_until":row.valid_until.isoformat()}

@router.post("/identity/delegations/{delegation_id}/revoke")
def revoke_identity_delegation(delegation_id: str, identity: Identity = Depends(get_identity), db: Session = Depends(get_db)):
    if not _is_admin(identity): raise HTTPException(403, "Engineering Admin required")
    apply_governance_rls_context(db, identity)
    try: enforce_identity_policy(db, identity, action="delegation_admin")
    except PermissionError as exc: raise HTTPException(403, str(exc))
    row=db.get(EngineeringIdentityDelegation,delegation_id)
    if not row: raise HTTPException(404,"Delegation not found")
    if row.revoked_at: return {"id":row.id,"revoked":True}
    row.revoked_at=datetime.now(timezone.utc); row.revoked_by=identity.user; db.commit()
    log_event(db, identity.user, "IDENTITY_DELEGATION_REVOKED", "identity_delegation", row.id, {"delegate":row.delegate})
    return {"id":row.id,"revoked":True}


# --- v6.3.7 Controlled handover target administration ---
@router.get("/handover/targets")
def handover_targets(identity: Identity = Depends(get_identity), db: Session = Depends(get_db)):
    if not _is_admin(identity): raise HTTPException(403,"Engineering Admin required")
    rows=db.scalars(select(EngineeringHandoverTarget).order_by(EngineeringHandoverTarget.code)).all()
    return [serialize_handover_target(db,x) for x in rows]

@router.post("/handover/targets")
def create_controlled_handover_target(req: HandoverTargetCreateRequest, identity: Identity = Depends(get_identity), db: Session = Depends(get_db)):
    if not _is_admin(identity): raise HTTPException(403,"Engineering Admin required")
    try:
        pd=enforce_identity_policy(db,identity,action="handover_target_admin")
        row=create_handover_target(db,code=req.code,name=req.name,external_system_id=req.external_system_id,environment=req.environment,allow_write=req.allow_write,idempotency_supported=req.idempotency_supported,receipt_required=req.receipt_required,write_path=req.write_path,reconcile_path_template=req.reconcile_path_template,allowed_projects=req.allowed_project_codes,allowed_areas=req.allowed_manufacturing_areas,metadata=req.metadata,user=identity.user)
    except PermissionError as exc: raise HTTPException(403,str(exc))
    except ValueError as exc: raise HTTPException(409,str(exc))
    log_event(db,identity.user,"HANDOVER_TARGET_CREATED","engineering_handover_target",row.id,{"code":row.code,"allow_write":row.allow_write,"environment":row.environment,"identity_policy_id":pd.policy_id})
    return serialize_handover_target(db,row)

@router.get("/handover/summary")
def controlled_handover_summary(identity: Identity = Depends(get_identity), db: Session = Depends(get_db)):
    if not _is_admin(identity): raise HTTPException(403,"Engineering Admin required")
    return handover_dashboard(db)

# --- v6.3.8 Data Lifecycle, Retention & Compliance Hardening ---
def _serialize_retention(row):
    return {"id":row.id,"name":row.name,"entity_type":row.entity_type,"project_code":row.project_code,"manufacturing_area":row.manufacturing_area,"archive_after_days":row.archive_after_days,"retain_for_days":row.retain_for_days,"immutable_min_days":row.immutable_min_days,"allow_authoritative_purge":row.allow_authoritative_purge,"active":row.active,"created_by":row.created_by,"created_at":row.created_at.isoformat()}

def _serialize_hold(row):
    return {"id":row.id,"hold_code":row.hold_code,"project_code":row.project_code,"manufacturing_area":row.manufacturing_area,"entity_type":row.entity_type,"entity_id":row.entity_id,"reason":row.reason,"active":row.active,"expires_at":row.expires_at.isoformat() if row.expires_at else None,"placed_by":row.placed_by,"placed_at":row.placed_at.isoformat(),"released_by":row.released_by,"released_at":row.released_at.isoformat() if row.released_at else None}

def _serialize_purge(row):
    return {"id":row.id,"entity_type":row.entity_type,"entity_id":row.entity_id,"project_code":row.project_code,"manufacturing_area":row.manufacturing_area,"purge_scope":row.purge_scope,"entity_snapshot_sha256":row.entity_snapshot_sha256,"reason":row.reason,"status":row.status,"created_by":row.created_by,"checker_user":row.checker_user,"authorized_at":row.authorized_at.isoformat() if row.authorized_at else None,"executed_by":row.executed_by,"executed_at":row.executed_at.isoformat() if row.executed_at else None,"result":row.result_json or {},"created_at":row.created_at.isoformat()}

@router.get("/lifecycle/summary")
def data_lifecycle_summary(identity: Identity = Depends(get_identity), db: Session = Depends(get_db)):
    if not _is_admin(identity): raise HTTPException(403,"Engineering Admin required")
    return lifecycle_dashboard(db)

@router.get("/lifecycle/storage-usage")
def data_lifecycle_storage_usage(project_code: str | None = None, manufacturing_area: str | None = None, identity: Identity = Depends(get_identity), db: Session = Depends(get_db)):
    if not _is_admin(identity): raise HTTPException(403,"Engineering Admin required")
    return storage_usage(db,project_code=project_code,manufacturing_area=manufacturing_area)

@router.get("/lifecycle/retention-policies")
def retention_policies(identity: Identity = Depends(get_identity), db: Session = Depends(get_db)):
    if not _is_admin(identity): raise HTTPException(403,"Engineering Admin required")
    return [_serialize_retention(x) for x in db.scalars(select(EngineeringRetentionPolicy).order_by(EngineeringRetentionPolicy.created_at.desc())).all()]

@router.post("/lifecycle/retention-policies")
def create_engineering_retention_policy(req: RetentionPolicyCreateRequest, identity: Identity = Depends(get_identity), db: Session = Depends(get_db)):
    if not _is_admin(identity): raise HTTPException(403,"Engineering Admin required")
    if req.entity_type not in SUPPORTED_ENTITY_TYPES: raise HTTPException(400,"Unsupported retention entity type")
    try:
        pd=enforce_identity_policy(db,identity,action="retention_policy_admin",project_code=req.project_code,manufacturing_area=req.manufacturing_area,entity_type=req.entity_type)
        row=create_retention_policy(db,name=req.name,entity_type=req.entity_type,project_code=req.project_code,manufacturing_area=req.manufacturing_area,archive_after_days=req.archive_after_days,retain_for_days=req.retain_for_days,immutable_min_days=req.immutable_min_days,allow_authoritative_purge=req.allow_authoritative_purge,created_by=identity.user)
    except PermissionError as exc: raise HTTPException(403,str(exc))
    log_event(db,identity.user,"RETENTION_POLICY_CREATED","retention_policy",row.id,{"entity_type":row.entity_type,"identity_policy_id":pd.policy_id})
    return _serialize_retention(row)

@router.get("/lifecycle/legal-holds")
def legal_holds(identity: Identity = Depends(get_identity), db: Session = Depends(get_db)):
    if not _is_admin(identity): raise HTTPException(403,"Engineering Admin required")
    return [_serialize_hold(x) for x in db.scalars(select(EngineeringLegalHold).order_by(EngineeringLegalHold.placed_at.desc())).all()]

@router.post("/lifecycle/legal-holds")
def create_legal_hold(req: LegalHoldCreateRequest, identity: Identity = Depends(get_identity), db: Session = Depends(get_db)):
    if not _is_admin(identity): raise HTTPException(403,"Engineering Admin required")
    if req.entity_type and req.entity_type not in SUPPORTED_ENTITY_TYPES: raise HTTPException(400,"Unsupported legal hold entity type")
    try:
        pd=enforce_identity_policy(db,identity,action="legal_hold_admin",project_code=req.project_code,manufacturing_area=req.manufacturing_area,entity_type=req.entity_type)
        row=place_hold(db,hold_code=req.hold_code,project_code=req.project_code,manufacturing_area=req.manufacturing_area,entity_type=req.entity_type,entity_id=req.entity_id,reason=req.reason,expires_at=req.expires_at,user=identity.user)
    except PermissionError as exc: raise HTTPException(403,str(exc))
    except ValueError as exc: raise HTTPException(409,str(exc))
    log_event(db,identity.user,"LEGAL_HOLD_PLACED","legal_hold",row.id,{"hold_code":row.hold_code,"identity_policy_id":pd.policy_id})
    return _serialize_hold(row)

@router.post("/lifecycle/legal-holds/{hold_id}/release")
def release_engineering_legal_hold(hold_id: str, req: LegalHoldReleaseRequest, identity: Identity = Depends(get_identity), db: Session = Depends(get_db)):
    if not _is_admin(identity): raise HTTPException(403,"Engineering Admin required")
    row=db.get(EngineeringLegalHold,hold_id)
    if not row: raise HTTPException(404,"Legal hold not found")
    try: enforce_identity_policy(db,identity,action="legal_hold_admin",project_code=row.project_code,manufacturing_area=row.manufacturing_area,entity_type=row.entity_type)
    except PermissionError as exc: raise HTTPException(403,str(exc))
    row=release_hold(db,row,user=identity.user,reason=req.reason); log_event(db,identity.user,"LEGAL_HOLD_RELEASED","legal_hold",row.id,{"reason":req.reason}); return _serialize_hold(row)

@router.post("/lifecycle/{entity_type}/{entity_id}/archive")
def archive_engineering_entity(entity_type: str, entity_id: str, req: LifecycleArchiveRequest, identity: Identity = Depends(get_identity), db: Session = Depends(get_db)):
    if not _is_admin(identity): raise HTTPException(403,"Engineering Admin required")
    try:
        enforce_identity_policy(db,identity,action="lifecycle_archive",entity_type=entity_type)
        state=archive_entity(db,entity_type=entity_type,entity_id=entity_id,identity=identity,reason=req.reason)
    except PermissionError as exc: raise HTTPException(403,str(exc))
    except LookupError as exc: raise HTTPException(404,str(exc))
    except ValueError as exc: raise HTTPException(400,str(exc))
    log_event(db,identity.user,"ENGINEERING_ENTITY_ARCHIVED",entity_type,entity_id,{"reason":req.reason})
    return {"entity_type":state.entity_type,"entity_id":state.entity_id,"state":state.state,"archived_at":state.archived_at.isoformat() if state.archived_at else None}

@router.get("/lifecycle/{entity_type}/{entity_id}/lineage")
def engineering_evidence_lineage(entity_type: str, entity_id: str, identity: Identity = Depends(get_identity), db: Session = Depends(get_db)):
    if not _is_admin(identity): raise HTTPException(403,"Engineering Admin required")
    try: return evidence_lineage(db,entity_type=entity_type,entity_id=entity_id)
    except LookupError as exc: raise HTTPException(404,str(exc))

@router.get("/lifecycle/purge-requests")
def purge_requests(identity: Identity = Depends(get_identity), db: Session = Depends(get_db)):
    if not _is_admin(identity): raise HTTPException(403,"Engineering Admin required")
    return [_serialize_purge(x) for x in db.scalars(select(EngineeringPurgeRequest).order_by(EngineeringPurgeRequest.created_at.desc()).limit(500)).all()]

@router.post("/lifecycle/purge-requests")
def create_engineering_purge_request(req: PurgeRequestCreateRequest, identity: Identity = Depends(get_identity), db: Session = Depends(get_db)):
    if not _is_admin(identity): raise HTTPException(403,"Engineering Admin required")
    try:
        enforce_identity_policy(db,identity,action="purge_create",entity_type=req.entity_type)
        row=create_purge_request(db,entity_type=req.entity_type,entity_id=req.entity_id,purge_scope=req.purge_scope,reason=req.reason,identity=identity)
    except PermissionError as exc: raise HTTPException(403,str(exc))
    except LookupError as exc: raise HTTPException(404,str(exc))
    except ValueError as exc: raise HTTPException(409,str(exc))
    log_event(db,identity.user,"PURGE_REQUEST_CREATED","purge_request",row.id,{"entity_type":row.entity_type,"entity_id":row.entity_id,"scope":row.purge_scope})
    return _serialize_purge(row)

@router.post("/lifecycle/purge-requests/{request_id}/authorize")
def authorize_engineering_purge(request_id: str, identity: Identity = Depends(get_identity), db: Session = Depends(get_db)):
    if not _is_admin(identity): raise HTTPException(403,"Engineering Admin required")
    row=db.get(EngineeringPurgeRequest,request_id)
    if not row: raise HTTPException(404,"Purge request not found")
    try:
        enforce_identity_policy(db,identity,action="purge_authorize",project_code=row.project_code,manufacturing_area=row.manufacturing_area,entity_type=row.entity_type)
        row=authorize_purge(db,row,identity=identity)
    except PermissionError as exc: raise HTTPException(403,str(exc))
    log_event(db,identity.user,"PURGE_REQUEST_AUTHORIZED","purge_request",row.id,{"entity_type":row.entity_type,"entity_id":row.entity_id})
    return _serialize_purge(row)

@router.post("/lifecycle/purge-requests/{request_id}/execute")
def execute_engineering_purge(request_id: str, identity: Identity = Depends(get_identity), db: Session = Depends(get_db)):
    if not _is_admin(identity): raise HTTPException(403,"Engineering Admin required")
    row=db.get(EngineeringPurgeRequest,request_id)
    if not row: raise HTTPException(404,"Purge request not found")
    try:
        enforce_identity_policy(db,identity,action="purge_execute",project_code=row.project_code,manufacturing_area=row.manufacturing_area,entity_type=row.entity_type)
        row=execute_purge(db,row,identity=identity)
    except PermissionError as exc: raise HTTPException(403,str(exc))
    except ValueError as exc: raise HTTPException(409,str(exc))
    except LookupError as exc: raise HTTPException(404,str(exc))
    log_event(db,identity.user,"PURGE_EXECUTED","purge_request",row.id,row.result_json or {})
    return _serialize_purge(row)

# --- v6.3.9 Database Performance & Scale Hardening ---
@router.get("/operations/performance")
def database_performance(identity: Identity = Depends(get_identity)):
    if not _is_admin(identity): raise HTTPException(403, "Engineering Admin required")
    from app.db.session import engine
    from app.services.performance_governance import performance_governance_snapshot, scale_profiles
    payload = performance_governance_snapshot(engine)
    payload["available_scale_profiles"] = scale_profiles()
    return payload


@router.get("/audit/cursor")
def audit_cursor(cursor: str | None = None, limit: int | None = None, identity: Identity = Depends(get_identity), db: Session = Depends(get_db)):
    """Keyset pagination for high-cardinality audit browsing; legacy /audit remains unchanged."""
    if not _is_admin(identity): raise HTTPException(403, "Admin group required")
    from datetime import datetime as _dt
    from sqlalchemy import and_, or_
    from app.services.performance_governance import decode_cursor, encode_cursor
    cfg = get_settings()
    page_limit = max(1, min(int(limit or cfg.cursor_page_default_limit), int(cfg.cursor_page_max_limit)))
    q = select(AuditEvent)
    if cursor:
        try:
            created_raw, row_id = decode_cursor(cursor)
            created_at = _dt.fromisoformat(created_raw)
        except ValueError as exc:
            raise HTTPException(400, str(exc))
        q = q.where(or_(AuditEvent.created_at < created_at, and_(AuditEvent.created_at == created_at, AuditEvent.id < row_id)))
    rows = db.scalars(q.order_by(AuditEvent.created_at.desc(), AuditEvent.id.desc()).limit(page_limit + 1)).all()
    has_more = len(rows) > page_limit
    page = rows[:page_limit]
    next_cursor = encode_cursor(page[-1].created_at, page[-1].id) if has_more and page else None
    return {"items": [{"id": e.id, "user": e.user, "action": e.action, "entity_type": e.entity_type, "entity_id": e.entity_id, "details": e.details, "created_at": e.created_at.isoformat()} for e in page], "next_cursor": next_cursor, "limit": page_limit, "strategy": "keyset"}


# --- v6.3.10 Cache, Read Models & Object 360 Performance ---
@router.get("/operations/read-models")
def engineering_read_models(identity: Identity = Depends(get_identity), db: Session = Depends(get_db)):
    if not _is_admin(identity): raise HTTPException(403, "Engineering Admin required")
    from app.services.read_models import read_model_status
    return read_model_status(db)


@router.post("/operations/read-models/rebuild")
def rebuild_engineering_read_models(project_code: str | None = None, manufacturing_area: str | None = None, identity: Identity = Depends(get_identity), db: Session = Depends(get_db)):
    if not _is_admin(identity): raise HTTPException(403, "Engineering Admin required")
    from app.services.read_models import rebuild_read_models
    result = rebuild_read_models(db, project_code=project_code, manufacturing_area=manufacturing_area)
    log_event(db, identity.user, "READ_MODELS_REBUILT", "platform", "read_models", {"project_code": project_code, "manufacturing_area": manufacturing_area, **result})
    return result
