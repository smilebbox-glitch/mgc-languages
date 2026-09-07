from __future__ import annotations

import hashlib, json
from datetime import datetime, timezone
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models import (
    ChangeRequest, Document, EngineeringApprovalCase, EngineeringApprovalPolicy, EngineeringApprovalRecord,
    EngineeringReleasePackage, EngineeringReleasePackageItem, ManufacturingLayout, WorkInstruction,
    EngineeringIdentityPolicy, EngineeringIdentityDelegation,
)


def _now(): return datetime.now(timezone.utc)
def _canon(value): return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"), default=str)
def _sha(value): return hashlib.sha256(_canon(value).encode()).hexdigest()

DEFAULT_STAGES = [
    {"key":"engineering_review","label":"Engineering Review","required_role":"engineering_user","required_groups":[]},
    {"key":"final_release","label":"Final Release","required_role":"engineering_admin","required_groups":[]},
]

def policy_payload(policy: EngineeringApprovalPolicy | None, entity_type: str) -> dict:
    if policy:
        return {"id":policy.id,"entity_type":policy.entity_type,"name":policy.name,"stages":policy.stages_json or [],
                "maker_checker_required":bool(policy.maker_checker_required),"distinct_approvers_required":bool(policy.distinct_approvers_required)}
    return {"id":None,"entity_type":entity_type,"name":"MGC Default 4-eyes","stages":DEFAULT_STAGES,
            "maker_checker_required":True,"distinct_approvers_required":True}

def resolve_policy(db: Session, entity_type: str, project_code: str | None, manufacturing_area: str | None):
    rows = db.scalars(select(EngineeringApprovalPolicy).where(EngineeringApprovalPolicy.entity_type==entity_type, EngineeringApprovalPolicy.active==True).order_by(EngineeringApprovalPolicy.created_at.desc())).all()
    ranked=[]
    for p in rows:
        if p.project_code and p.project_code != project_code: continue
        if p.manufacturing_area and p.manufacturing_area != manufacturing_area: continue
        score = (2 if p.project_code else 0) + (1 if p.manufacturing_area else 0)
        ranked.append((score,p))
    ranked.sort(key=lambda x:x[0], reverse=True)
    return ranked[0][1] if ranked else None

def entity_snapshot(entity_type: str, obj) -> dict:
    if entity_type == "work_instruction":
        return {"id":obj.id,"project_code":obj.project_code,"manufacturing_area":obj.manufacturing_area,"code":obj.code,"revision":obj.revision,"status":obj.status,"row_version":obj.row_version,"title":obj.title,"steps":obj.steps_json or [],"safety":obj.safety_points_json or [],"quality":obj.quality_points_json or [],"tools":obj.tools_json or [],"ppe":obj.ppe_json or [],"translation_status":obj.translation_status,"metadata":obj.metadata_json or {}}
    if entity_type == "manufacturing_layout":
        return {"id":obj.id,"project_code":obj.project_code,"manufacturing_area":obj.manufacturing_area,"code":obj.code,"revision":obj.revision,"status":obj.status,"row_version":obj.row_version,"title":obj.title,"source_document_id":obj.source_document_id,"metadata":obj.metadata_json or {}}
    if entity_type == "engineering_change":
        return {"id":obj.id,"code":obj.code,"eco_code":obj.eco_code,"part_number":obj.part_number,"from_revision":obj.from_revision,"to_revision":obj.to_revision,"status":obj.status,"row_version":obj.row_version,"risk_level":obj.risk_level,"impact":obj.impact_json or {},"metadata":obj.metadata_json or {}}
    if entity_type == "document":
        return {"id":obj.id,"project_code":obj.project_code,"manufacturing_area":obj.manufacturing_area,"filename":obj.filename,"doc_type":obj.doc_type,"part_number":obj.part_number,"revision":obj.revision,"sha256":obj.sha256,"status":getattr(obj.status,"value",obj.status)}
    if entity_type == "release_package":
        # Approval covers immutable package content identity, not workflow fields such as status/row_version.
        return {"id":obj.id,"project_code":obj.project_code,"manufacturing_area":obj.manufacturing_area,"code":obj.code,"title":obj.title,"release_sha256":obj.release_sha256,"source_change_id":obj.source_change_id,"metadata":obj.metadata_json or {}}
    raise ValueError("Unsupported approval entity type")

def object_for(db: Session, entity_type: str, entity_id: str):
    cls={"work_instruction":WorkInstruction,"manufacturing_layout":ManufacturingLayout,"engineering_change":ChangeRequest,"document":Document,"release_package":EngineeringReleasePackage}.get(entity_type)
    if not cls: raise ValueError("Unsupported entity type")
    row=db.get(cls,entity_id)
    if not row: raise LookupError("Entity not found")
    return row

def submit_case(db: Session, *, entity_type: str, entity_id: str, project_code: str | None, manufacturing_area: str | None, submitted_by: str, submitted_identity: dict | None = None) -> EngineeringApprovalCase:
    obj=object_for(db,entity_type,entity_id)
    snapshot=entity_snapshot(entity_type,obj); snapshot_hash=_sha(snapshot)
    prior=db.scalar(select(func.max(EngineeringApprovalCase.cycle_no)).where(EngineeringApprovalCase.entity_type==entity_type, EngineeringApprovalCase.entity_id==entity_id)) or 0
    policy=resolve_policy(db,entity_type,project_code,manufacturing_area); pp=policy_payload(policy,entity_type)
    case=EngineeringApprovalCase(entity_type=entity_type,entity_id=entity_id,project_code=project_code,manufacturing_area=manufacturing_area,policy_id=policy.id if policy else None,policy_snapshot_json=pp,cycle_no=int(prior)+1,status="pending",snapshot_sha256=snapshot_hash,submitted_by=submitted_by,submitted_identity_json=submitted_identity or {})
    db.add(case); db.commit(); db.refresh(case); return case

def _eligible(stage: dict, *, groups: list[str], is_admin: bool) -> bool:
    role=stage.get("required_role","engineering_user")
    if role=="engineering_admin": return is_admin
    if role=="group": return bool(set(stage.get("required_groups") or []) & set(groups))
    return True

def decide_case(db: Session, case: EngineeringApprovalCase, *, user: str, groups: list[str], is_admin: bool, decision: str, comment: str | None, identity_snapshot_payload: dict | None = None, assurance_payload: dict | None = None) -> EngineeringApprovalCase:
    if case.status != "pending": raise ValueError("Approval case is not pending")
    obj=object_for(db,case.entity_type,case.entity_id); current_hash=_sha(entity_snapshot(case.entity_type,obj))
    if current_hash != case.snapshot_sha256: raise ValueError("Entity changed after submission; submit a new approval cycle")
    policy=case.policy_snapshot_json or {}; stages=policy.get("stages") or DEFAULT_STAGES
    records=db.scalars(select(EngineeringApprovalRecord).where(EngineeringApprovalRecord.case_id==case.id).order_by(EngineeringApprovalRecord.stage_order)).all()
    idx=len(records)
    if idx>=len(stages): raise ValueError("All approval stages are already completed")
    stage=stages[idx]
    if not _eligible(stage, groups=groups, is_admin=is_admin): raise PermissionError("Current identity is not eligible for this approval stage")
    creator=getattr(obj,"created_by",None) or getattr(obj,"submitted_by",None)
    if policy.get("maker_checker_required",True) and creator and user==creator: raise PermissionError("Maker-checker rule: author cannot approve own object")
    if policy.get("distinct_approvers_required",True) and any(r.approver==user for r in records): raise PermissionError("Segregation of duties: approval stages require different approvers")
    prev=records[-1].record_hash if records else ""
    record_data={"case_id":case.id,"stage_key":stage["key"],"stage_order":idx+1,"approver":user,"decision":decision,"comment":comment,"snapshot_sha256":case.snapshot_sha256,"previous_hash":prev}
    rec=EngineeringApprovalRecord(**record_data,record_hash=_sha(record_data),identity_snapshot_json=identity_snapshot_payload or {},assurance_json=assurance_payload or {})
    db.add(rec)
    if decision=="rejected": case.status="rejected"; case.completed_at=_now()
    elif idx+1==len(stages): case.status="approved"; case.completed_at=_now()
    db.commit(); db.refresh(case); return case

def serialize_case(db: Session, case: EngineeringApprovalCase) -> dict:
    rs=db.scalars(select(EngineeringApprovalRecord).where(EngineeringApprovalRecord.case_id==case.id).order_by(EngineeringApprovalRecord.stage_order)).all()
    prev=""; integrity=True
    for r in rs:
        data={"case_id":case.id,"stage_key":r.stage_key,"stage_order":r.stage_order,"approver":r.approver,"decision":r.decision,"comment":r.comment,"snapshot_sha256":r.snapshot_sha256,"previous_hash":prev}
        if r.previous_hash != prev or r.record_hash != _sha(data): integrity=False; break
        prev=r.record_hash
    return {"id":case.id,"entity_type":case.entity_type,"entity_id":case.entity_id,"cycle_no":case.cycle_no,"status":case.status,"snapshot_sha256":case.snapshot_sha256,"submitted_by":case.submitted_by,"submitted_identity":case.submitted_identity_json or {},"policy":case.policy_snapshot_json,"approval_chain_integrity_valid":integrity,"records":[{"id":r.id,"stage_key":r.stage_key,"stage_order":r.stage_order,"approver":r.approver,"decision":r.decision,"comment":r.comment,"record_hash":r.record_hash,"previous_hash":r.previous_hash,"identity":r.identity_snapshot_json or {},"assurance":r.assurance_json or {},"created_at":r.created_at.isoformat()} for r in rs],"created_at":case.created_at.isoformat(),"completed_at":case.completed_at.isoformat() if case.completed_at else None}

def create_release_package(db: Session, *, project_code: str, manufacturing_area: str | None, code: str, title: str, source_change_id: str | None, items: list[tuple[str,str]], metadata: dict, user: str) -> EngineeringReleasePackage:
    if db.scalar(select(EngineeringReleasePackage).where(EngineeringReleasePackage.project_code==project_code, EngineeringReleasePackage.code==code)): raise ValueError("Release package code already exists")
    pkg=EngineeringReleasePackage(project_code=project_code,manufacturing_area=manufacturing_area,code=code,title=title,status="draft",source_change_id=source_change_id,created_by=user,metadata_json=metadata or {})
    db.add(pkg); db.flush()
    hashes=[]
    for et,eid in items:
        obj=object_for(db,et,eid); snap=entity_snapshot(et,obj)
        if snap.get("project_code") and snap.get("project_code")!=project_code: raise ValueError("Release package item belongs to another project")
        if manufacturing_area and snap.get("manufacturing_area") not in (None,manufacturing_area): raise ValueError("Release package item belongs to another manufacturing area")
        h=_sha(snap); hashes.append(h)
        db.add(EngineeringReleasePackageItem(package_id=pkg.id,entity_type=et,entity_id=eid,business_code=snap.get("code") or snap.get("part_number") or snap.get("filename"),business_revision=snap.get("revision") or snap.get("to_revision"),authority="plm_pdm" if et=="document" else "mgc",snapshot_sha256=h,snapshot_json=snap))
    pkg.release_sha256=_sha({"project_code":project_code,"code":code,"items":sorted(hashes)})
    db.commit(); db.refresh(pkg); return pkg

def package_items(db: Session, package_id: str): return db.scalars(select(EngineeringReleasePackageItem).where(EngineeringReleasePackageItem.package_id==package_id).order_by(EngineeringReleasePackageItem.captured_at)).all()
def verify_package(db: Session, pkg: EngineeringReleasePackage) -> tuple[bool,list[dict]]:
    drifts=[]
    for item in package_items(db,pkg.id):
        try: current=_sha(entity_snapshot(item.entity_type,object_for(db,item.entity_type,item.entity_id)))
        except Exception as exc: drifts.append({"entity_type":item.entity_type,"entity_id":item.entity_id,"reason":str(exc)}); continue
        if current!=item.snapshot_sha256: drifts.append({"entity_type":item.entity_type,"entity_id":item.entity_id,"captured":item.snapshot_sha256,"current":current})
    return (not drifts,drifts)
def submit_package(db: Session,pkg: EngineeringReleasePackage,user: str, submitted_identity: dict | None = None):
    if pkg.status!="draft": raise ValueError("Only draft package can be submitted")
    ok,drifts=verify_package(db,pkg)
    if not ok: raise ValueError(f"Release package contains stale items: {len(drifts)}")
    # Release Package cannot be used to bypass object-level engineering approval.
    for item in package_items(db,pkg.id):
        snap=item.snapshot_json or {}; status=str(snap.get("status") or "").lower()
        if item.entity_type in {"work_instruction","manufacturing_layout"} and status != "approved":
            raise ValueError(f"{item.entity_type} {item.business_code or item.entity_id} must be approved before package submission")
        if item.entity_type == "engineering_change" and status not in {"approved","implementation","implemented"}:
            raise ValueError("Engineering change must be approved before package submission")
        if item.entity_type == "document" and status != "ready":
            raise ValueError("Document/BOM evidence must be ready before package submission")
    # Snapshot must represent the submitted state, not the prior draft state.
    pkg.status="in_review"; db.flush()
    case=submit_case(db,entity_type="release_package",entity_id=pkg.id,project_code=pkg.project_code,manufacturing_area=pkg.manufacturing_area,submitted_by=user,submitted_identity=submitted_identity)
    pkg.approval_case_id=case.id; db.commit(); db.refresh(pkg); return pkg,case

def release_package(db: Session,pkg: EngineeringReleasePackage,user: str,is_admin: bool,released_identity: dict | None = None):
    if not is_admin: raise PermissionError("Engineering Admin required for production release")
    if pkg.status!="in_review" or not pkg.approval_case_id: raise ValueError("Package is not awaiting release")
    case=db.get(EngineeringApprovalCase,pkg.approval_case_id)
    if not case or case.status!="approved": raise ValueError("All approval stages must be approved before release")
    ok,drifts=verify_package(db,pkg)
    if not ok: raise ValueError(f"Release package changed after approval: {len(drifts)} stale items")
    if user==pkg.created_by: raise PermissionError("Maker-checker rule: package creator cannot perform final production release")
    pkg.status="released"; pkg.released_by=user; pkg.released_at=_now(); pkg.released_identity_json=released_identity or {}
    # Controlled supersession only for MGC-owned revisions. PLM/PDM document authority is never overwritten.
    for item in package_items(db,pkg.id):
        if item.entity_type=="work_instruction":
            current=db.get(WorkInstruction,item.entity_id)
            if current:
                siblings=db.scalars(select(WorkInstruction).where(WorkInstruction.project_code==current.project_code,WorkInstruction.code==current.code,WorkInstruction.id!=current.id,WorkInstruction.status=="approved")).all()
                for old in siblings:
                    old.status="obsolete"; old.metadata_json={**(old.metadata_json or {}),"superseded_by_release_package":pkg.id,"superseded_by_revision":current.revision}
                current.status="approved"; current.approved_by=current.approved_by or user
        elif item.entity_type=="manufacturing_layout":
            current=db.get(ManufacturingLayout,item.entity_id)
            if current:
                siblings=db.scalars(select(ManufacturingLayout).where(ManufacturingLayout.project_code==current.project_code,ManufacturingLayout.code==current.code,ManufacturingLayout.id!=current.id,ManufacturingLayout.status=="approved")).all()
                for old in siblings: old.status="obsolete"; old.metadata_json={**(old.metadata_json or {}),"superseded_by_release_package":pkg.id,"superseded_by_revision":current.revision}
                current.status="approved"
    db.commit(); db.refresh(pkg); return pkg

def serialize_package(db: Session,pkg: EngineeringReleasePackage) -> dict:
    items=package_items(db,pkg.id); ok,drifts=verify_package(db,pkg)
    case=serialize_case(db,db.get(EngineeringApprovalCase,pkg.approval_case_id)) if pkg.approval_case_id and db.get(EngineeringApprovalCase,pkg.approval_case_id) else None
    return {"id":pkg.id,"row_version":pkg.row_version,"project_code":pkg.project_code,"manufacturing_area":pkg.manufacturing_area,"code":pkg.code,"title":pkg.title,"status":pkg.status,"source_change_id":pkg.source_change_id,"release_sha256":pkg.release_sha256,"created_by":pkg.created_by,"released_by":pkg.released_by,"released_at":pkg.released_at.isoformat() if pkg.released_at else None,"released_identity":pkg.released_identity_json or {},"integrity":{"valid":ok,"drifts":drifts},"items":[{"id":x.id,"entity_type":x.entity_type,"entity_id":x.entity_id,"business_code":x.business_code,"business_revision":x.business_revision,"authority":x.authority,"snapshot_sha256":x.snapshot_sha256} for x in items],"approval":case,"metadata":pkg.metadata_json or {},"created_at":pkg.created_at.isoformat(),"updated_at":pkg.updated_at.isoformat()}

def governance_dashboard(db: Session) -> dict:
    now=_now()
    return {"status":"CONTROLLED","active_policies":db.scalar(select(func.count()).select_from(EngineeringApprovalPolicy).where(EngineeringApprovalPolicy.active==True)) or 0,"active_identity_policies":db.scalar(select(func.count()).select_from(EngineeringIdentityPolicy).where(EngineeringIdentityPolicy.active==True)) or 0,"active_delegations":db.scalar(select(func.count()).select_from(EngineeringIdentityDelegation).where(EngineeringIdentityDelegation.revoked_at.is_(None),EngineeringIdentityDelegation.valid_until>=now)) or 0,"pending_approval_cases":db.scalar(select(func.count()).select_from(EngineeringApprovalCase).where(EngineeringApprovalCase.status=="pending")) or 0,"rejected_approval_cases":db.scalar(select(func.count()).select_from(EngineeringApprovalCase).where(EngineeringApprovalCase.status=="rejected")) or 0,"released_packages":db.scalar(select(func.count()).select_from(EngineeringReleasePackage).where(EngineeringReleasePackage.status=="released")) or 0,"packages_in_review":db.scalar(select(func.count()).select_from(EngineeringReleasePackage).where(EngineeringReleasePackage.status=="in_review")) or 0,"qualified_electronic_signature":False,"identity_policy_enforcement":"scoped","record_type":"tamper_evident_engineering_approval_evidence"}


def release_manifest(db: Session, pkg: EngineeringReleasePackage) -> dict:
    """Canonical handover manifest. It never performs PLM/MES write-back."""
    items = package_items(db, pkg.id)
    case = db.get(EngineeringApprovalCase, pkg.approval_case_id) if pkg.approval_case_id else None
    records = db.scalars(select(EngineeringApprovalRecord).where(EngineeringApprovalRecord.case_id == case.id).order_by(EngineeringApprovalRecord.stage_order)).all() if case else []
    payload = {
        "schema": "mgc-engineering-release-manifest-v1",
        "package_id": pkg.id, "project_code": pkg.project_code, "manufacturing_area": pkg.manufacturing_area,
        "code": pkg.code, "status": pkg.status, "release_sha256": pkg.release_sha256,
        "released_by": pkg.released_by, "released_at": pkg.released_at.isoformat() if pkg.released_at else None,
        "released_identity": pkg.released_identity_json or {},
        "approval_case_id": case.id if case else None,
        "approval_chain_head": records[-1].record_hash if records else "",
        "items": [{"entity_type":i.entity_type,"entity_id":i.entity_id,"business_code":i.business_code,"business_revision":i.business_revision,"authority":i.authority,"snapshot_sha256":i.snapshot_sha256} for i in items],
        "production_writeback": False,
    }
    return {"manifest": payload, "manifest_sha256": _sha(payload), "qualified_electronic_signature": False}
