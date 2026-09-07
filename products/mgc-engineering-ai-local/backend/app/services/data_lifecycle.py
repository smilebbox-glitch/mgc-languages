from __future__ import annotations

import hashlib, json
from datetime import datetime, timezone
from pathlib import Path
from sqlalchemy import delete, func, or_, select
from sqlalchemy.orm import Session

from app.adapters.registry import get_graph_projection_port, get_search_port
from app.core.config import get_settings
from app.core.security import Identity, identity_snapshot
from app.db.models import (
    AuditEvent, BOMItem, Document, DocumentSearchChunk, EngineeringApprovalRecord,
    EngineeringDataLifecycleState, EngineeringHandoverJob, EngineeringLegalHold,
    EngineeringLifecycleEvent, EngineeringPurgeRequest, EngineeringReleasePackage,
    EngineeringReleasePackageItem, EngineeringRetentionPolicy, ManufacturingLayout,
    ProjectionDeliveryReceipt, ProjectionOutboxEvent, Relationship, WorkInstruction,
)

SUPPORTED_ENTITY_TYPES = {"document", "work_instruction", "manufacturing_layout", "release_package", "approval_record", "handover_job"}
PURGE_SCOPES = {"projections_only", "authoritative"}


def _now(): return datetime.now(timezone.utc)
def _canon(value): return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"), default=str)
def _sha(value): return hashlib.sha256(_canon(value).encode()).hexdigest()


def _model(entity_type: str):
    return {
        "document": Document, "work_instruction": WorkInstruction, "manufacturing_layout": ManufacturingLayout,
        "release_package": EngineeringReleasePackage, "approval_record": EngineeringApprovalRecord,
        "handover_job": EngineeringHandoverJob,
    }.get(entity_type)


def entity_context(entity_type: str, row) -> tuple[str | None, str | None]:
    if entity_type == "handover_job":
        return None, None
    return getattr(row, "project_code", None), getattr(row, "manufacturing_area", None)


def entity_snapshot(entity_type: str, row) -> dict:
    data = {"entity_type": entity_type, "entity_id": row.id}
    for field in ("project_code","manufacturing_area","code","revision","status","sha256","filename","release_sha256","request_sha256","event_hash","updated_at","created_at"):
        if hasattr(row, field): data[field] = getattr(row, field)
    return data


def _append_event(db: Session, *, entity_type: str, entity_id: str, action: str, actor: str, details: dict) -> EngineeringLifecycleEvent:
    previous = db.scalar(select(EngineeringLifecycleEvent).where(
        EngineeringLifecycleEvent.entity_type == entity_type,
        EngineeringLifecycleEvent.entity_id == entity_id,
    ).order_by(EngineeringLifecycleEvent.created_at.desc(), EngineeringLifecycleEvent.id.desc()))
    previous_hash = previous.event_hash if previous else None
    payload = {"entity_type":entity_type,"entity_id":entity_id,"action":action,"actor":actor,"details":details,"previous_hash":previous_hash,"created_at":_now().isoformat()}
    row = EngineeringLifecycleEvent(entity_type=entity_type, entity_id=entity_id, action=action, actor=actor, details_json=details,
                                    previous_hash=previous_hash, event_hash=_sha(payload))
    db.add(row); db.flush(); return row


def resolve_policy(db: Session, *, entity_type: str, project_code: str | None, manufacturing_area: str | None) -> EngineeringRetentionPolicy | None:
    rows=db.scalars(select(EngineeringRetentionPolicy).where(EngineeringRetentionPolicy.entity_type==entity_type, EngineeringRetentionPolicy.active==True).order_by(EngineeringRetentionPolicy.created_at.desc())).all()
    matches=[]
    for p in rows:
        if p.project_code and p.project_code != project_code: continue
        if p.manufacturing_area and p.manufacturing_area != manufacturing_area: continue
        specificity=(2 if p.project_code else 0)+(1 if p.manufacturing_area else 0)
        matches.append((specificity,p))
    matches.sort(key=lambda x:x[0],reverse=True)
    return matches[0][1] if matches else None


def active_holds(db: Session, *, entity_type: str, entity_id: str, project_code: str | None, manufacturing_area: str | None) -> list[EngineeringLegalHold]:
    now=_now(); rows=db.scalars(select(EngineeringLegalHold).where(EngineeringLegalHold.active==True)).all(); out=[]
    for h in rows:
        if h.expires_at:
            exp=h.expires_at.replace(tzinfo=timezone.utc) if h.expires_at.tzinfo is None else h.expires_at
            if exp <= now: continue
        if h.project_code and h.project_code != project_code: continue
        if h.manufacturing_area and h.manufacturing_area != manufacturing_area: continue
        if h.entity_type and h.entity_type != entity_type: continue
        if h.entity_id and h.entity_id != entity_id: continue
        out.append(h)
    return out


def storage_usage(db: Session, *, project_code: str | None = None, manufacturing_area: str | None = None) -> dict:
    stmt=select(func.coalesce(func.sum(Document.size_bytes),0), func.count(Document.id))
    if project_code is not None: stmt=stmt.where(Document.project_code==project_code)
    if manufacturing_area is not None: stmt=stmt.where(Document.manufacturing_area==manufacturing_area)
    total,count=db.execute(stmt).one(); total=int(total or 0); cfg=get_settings()
    quota_mb=cfg.data_lifecycle_area_quota_mb if manufacturing_area else cfg.data_lifecycle_project_quota_mb
    quota_bytes=max(int(quota_mb),0)*1024*1024
    pct=(total/quota_bytes*100.0) if quota_bytes else 0.0
    return {"bytes":total,"documents":int(count or 0),"quota_bytes":quota_bytes,"quota_percent":round(pct,2),"warning":bool(quota_bytes and pct>=cfg.data_lifecycle_quota_warning_percent),"hard_limit_exceeded":bool(quota_bytes and total>quota_bytes)}


def enforce_upload_quota(db: Session, *, project_code: str | None, manufacturing_area: str | None, incoming_bytes: int) -> dict:
    checks=[]
    if project_code:
        usage=storage_usage(db,project_code=project_code); checks.append(("project",usage,get_settings().data_lifecycle_project_quota_mb))
    if manufacturing_area:
        usage=storage_usage(db,project_code=project_code,manufacturing_area=manufacturing_area); checks.append(("manufacturing_area",usage,get_settings().data_lifecycle_area_quota_mb))
    for scope,usage,quota_mb in checks:
        if int(quota_mb or 0)>0 and usage["bytes"]+int(incoming_bytes)>int(quota_mb)*1024*1024:
            raise PermissionError(f"{scope} engineering evidence quota exceeded")
    return {scope:usage for scope,usage,_ in checks}


def create_policy(db: Session, **kwargs) -> EngineeringRetentionPolicy:
    row=EngineeringRetentionPolicy(**kwargs); db.add(row); db.commit(); db.refresh(row); return row


def place_hold(db: Session, *, hold_code: str, project_code: str | None, manufacturing_area: str | None, entity_type: str | None, entity_id: str | None, reason: str, expires_at, user: str) -> EngineeringLegalHold:
    if not any([project_code, manufacturing_area, entity_type, entity_id]): raise ValueError("Legal hold must have a controlled scope")
    row=EngineeringLegalHold(hold_code=hold_code.strip().upper(),project_code=project_code,manufacturing_area=manufacturing_area,entity_type=entity_type,entity_id=entity_id,reason=reason.strip(),expires_at=expires_at,placed_by=user)
    db.add(row); db.flush(); _append_event(db,entity_type=entity_type or "scope",entity_id=entity_id or row.id,action="LEGAL_HOLD_PLACED",actor=user,details={"hold_code":row.hold_code,"project_code":project_code,"manufacturing_area":manufacturing_area}); db.commit(); db.refresh(row); return row


def release_hold(db: Session, row: EngineeringLegalHold, *, user: str, reason: str) -> EngineeringLegalHold:
    if not row.active: return row
    row.active=False; row.released_by=user; row.released_at=_now(); _append_event(db,entity_type=row.entity_type or "scope",entity_id=row.entity_id or row.id,action="LEGAL_HOLD_RELEASED",actor=user,details={"hold_code":row.hold_code,"reason":reason}); db.commit(); return row


def archive_entity(db: Session, *, entity_type: str, entity_id: str, identity: Identity, reason: str) -> EngineeringDataLifecycleState:
    model=_model(entity_type)
    if not model: raise ValueError("Unsupported lifecycle entity type")
    row=db.get(model,entity_id)
    if not row: raise LookupError("Entity not found")
    project,area=entity_context(entity_type,row)
    state=db.scalar(select(EngineeringDataLifecycleState).where(EngineeringDataLifecycleState.entity_type==entity_type,EngineeringDataLifecycleState.entity_id==entity_id))
    if not state:
        state=EngineeringDataLifecycleState(entity_type=entity_type,entity_id=entity_id,project_code=project,manufacturing_area=area); db.add(state)
    state.state="archived"; state.archived_by=identity.user; state.archived_at=_now(); state.reason=reason.strip()
    _append_event(db,entity_type=entity_type,entity_id=entity_id,action="ARCHIVED",actor=identity.user,details={"reason":reason,"snapshot_sha256":_sha(entity_snapshot(entity_type,row))})
    db.commit(); db.refresh(state); return state


def create_purge_request(db: Session, *, entity_type: str, entity_id: str, purge_scope: str, reason: str, identity: Identity) -> EngineeringPurgeRequest:
    if purge_scope not in PURGE_SCOPES: raise ValueError("Unsupported purge scope")
    model=_model(entity_type)
    if not model: raise ValueError("Unsupported lifecycle entity type")
    row=db.get(model,entity_id)
    if not row: raise LookupError("Entity not found")
    project,area=entity_context(entity_type,row)
    holds=active_holds(db,entity_type=entity_type,entity_id=entity_id,project_code=project,manufacturing_area=area)
    if holds: raise PermissionError("Active legal hold blocks purge request")
    if entity_type=="release_package": raise PermissionError("Released package records are immutable retention evidence and are not purgeable")
    snapshot=entity_snapshot(entity_type,row)
    req=EngineeringPurgeRequest(entity_type=entity_type,entity_id=entity_id,project_code=project,manufacturing_area=area,purge_scope=purge_scope,entity_snapshot_sha256=_sha(snapshot),reason=reason.strip(),created_by=identity.user,maker_identity_json=identity_snapshot(identity))
    db.add(req); db.flush(); _append_event(db,entity_type=entity_type,entity_id=entity_id,action="PURGE_REQUESTED",actor=identity.user,details={"purge_request_id":req.id,"scope":purge_scope,"snapshot_sha256":req.entity_snapshot_sha256}); db.commit(); db.refresh(req); return req


def authorize_purge(db: Session, req: EngineeringPurgeRequest, *, identity: Identity) -> EngineeringPurgeRequest:
    if identity.is_service_account: raise PermissionError("Human checker required")
    if identity.user==req.created_by: raise PermissionError("Purge maker cannot authorize own request")
    if req.status!="pending_authorization": return req
    req.status="authorized"; req.checker_user=identity.user; req.checker_identity_json=identity_snapshot(identity); req.authorized_at=_now(); _append_event(db,entity_type=req.entity_type,entity_id=req.entity_id,action="PURGE_AUTHORIZED",actor=identity.user,details={"purge_request_id":req.id,"scope":req.purge_scope}); db.commit(); return req


def _document_is_protected(db: Session, doc: Document) -> list[str]:
    reasons=[]
    if db.scalar(select(EngineeringReleasePackageItem.id).where(EngineeringReleasePackageItem.entity_type=="document",EngineeringReleasePackageItem.entity_id==doc.id).limit(1)): reasons.append("release_package")
    if db.scalar(select(WorkInstruction.id).where(WorkInstruction.source_document_id==doc.id).limit(1)): reasons.append("work_instruction_source")
    if db.scalar(select(ManufacturingLayout.id).where(ManufacturingLayout.source_document_id==doc.id).limit(1)): reasons.append("layout_source")
    if db.scalar(select(BOMItem.id).where(BOMItem.source_document_id==doc.id).limit(1)): reasons.append("bom_source")
    if db.scalar(select(Relationship.id).where(or_(Relationship.evidence_document_id==doc.id,Relationship.subject_id==doc.id,Relationship.object_id==doc.id)).limit(1)): reasons.append("relationship_evidence")
    return reasons


def execute_purge(db: Session, req: EngineeringPurgeRequest, *, identity: Identity) -> EngineeringPurgeRequest:
    if identity.is_service_account: raise PermissionError("Human identity required")
    if req.status!="authorized" or not req.checker_user: raise PermissionError("Maker-checker authorization required")
    if identity.user==req.created_by: raise PermissionError("Maker cannot execute own purge")
    model=_model(req.entity_type); row=db.get(model,req.entity_id) if model else None
    if not row: raise LookupError("Entity not found")
    project,area=entity_context(req.entity_type,row)
    if active_holds(db,entity_type=req.entity_type,entity_id=req.entity_id,project_code=project,manufacturing_area=area): raise PermissionError("Active legal hold blocks purge execution")
    if _sha(entity_snapshot(req.entity_type,row)) != req.entity_snapshot_sha256: raise ValueError("Entity changed after purge authorization; create a new request")
    result={"scope":req.purge_scope,"authoritative_deleted":False,"postgresql_chunks_deleted":False}
    if req.purge_scope=="projections_only":
        if req.entity_type!="document": raise ValueError("Projection purge currently supports documents only")
        search=get_search_port(); graph=get_graph_projection_port()
        search.delete_document(row.id); graph_result=graph.delete_document(row.id)
        result.update({"qdrant_or_search_projection":"deleted_or_noop","search_adapter":search.mode,"neo4j_projection":graph_result,"postgresql_authoritative_preserved":True,"local_evidence_preserved":True})
        state=db.scalar(select(EngineeringDataLifecycleState).where(EngineeringDataLifecycleState.entity_type==req.entity_type,EngineeringDataLifecycleState.entity_id==req.entity_id))
        if not state: state=EngineeringDataLifecycleState(entity_type=req.entity_type,entity_id=req.entity_id,project_code=project,manufacturing_area=area); db.add(state)
        state.state="projections_purged"; state.metadata_json={**(state.metadata_json or {}),"last_projection_purge_at":_now().isoformat()}
    else:
        cfg=get_settings()
        if not cfg.data_lifecycle_authoritative_purge_enabled: raise PermissionError("Authoritative purge is globally disabled")
        if req.entity_type!="document": raise PermissionError("v6.3.8 authoritative purge is limited to unreferenced documents")
        policy=resolve_policy(db,entity_type="document",project_code=project,manufacturing_area=area)
        if not policy or not policy.allow_authoritative_purge: raise PermissionError("Retention policy does not allow authoritative purge")
        age_days=max(0,(_now()-(row.created_at.replace(tzinfo=timezone.utc) if row.created_at.tzinfo is None else row.created_at)).days)
        if age_days < int(policy.retain_for_days): raise PermissionError("Retention period has not elapsed")
        protected=_document_is_protected(db,row)
        if protected: raise PermissionError("Authoritative document is referenced by controlled engineering evidence: "+", ".join(protected))
        search=get_search_port(); graph=get_graph_projection_port(); search.delete_document(row.id); graph.delete_document(row.id)
        path=Path(row.stored_path)
        db.execute(delete(DocumentSearchChunk).where(DocumentSearchChunk.document_id==row.id))
        db.execute(delete(ProjectionDeliveryReceipt).where(ProjectionDeliveryReceipt.event_id.in_(select(ProjectionOutboxEvent.id).where(ProjectionOutboxEvent.aggregate_type=="document",ProjectionOutboxEvent.aggregate_id==row.id))))
        db.execute(delete(ProjectionOutboxEvent).where(ProjectionOutboxEvent.aggregate_type=="document",ProjectionOutboxEvent.aggregate_id==row.id))
        db.delete(row); db.flush()
        if path.exists() and path.is_file(): path.unlink()
        result.update({"authoritative_deleted":True,"postgresql_chunks_deleted":True,"local_evidence_deleted":True})
    req.status="executed"; req.executed_by=identity.user; req.executed_at=_now(); req.result_json=result
    _append_event(db,entity_type=req.entity_type,entity_id=req.entity_id,action="PURGE_EXECUTED",actor=identity.user,details={"purge_request_id":req.id,**result}); db.commit(); return req


def evidence_lineage(db: Session, *, entity_type: str, entity_id: str) -> dict:
    model=_model(entity_type); row=db.get(model,entity_id) if model else None
    if not row: raise LookupError("Entity not found")
    out={"entity":entity_snapshot(entity_type,row),"references":[],"release_packages":[],"lifecycle":[]}
    if entity_type=="document":
        for wi in db.scalars(select(WorkInstruction).where(WorkInstruction.source_document_id==entity_id)).all(): out["references"].append({"type":"work_instruction","id":wi.id,"code":wi.code,"revision":wi.revision})
        for lay in db.scalars(select(ManufacturingLayout).where(ManufacturingLayout.source_document_id==entity_id)).all(): out["references"].append({"type":"manufacturing_layout","id":lay.id,"code":lay.code,"revision":lay.revision})
        for rel in db.scalars(select(Relationship).where(or_(Relationship.evidence_document_id==entity_id,Relationship.subject_id==entity_id,Relationship.object_id==entity_id))).all(): out["references"].append({"type":"relationship","id":rel.id,"predicate":rel.predicate})
    items=db.scalars(select(EngineeringReleasePackageItem).where(EngineeringReleasePackageItem.entity_type==entity_type,EngineeringReleasePackageItem.entity_id==entity_id)).all()
    for item in items:
        pkg=db.get(EngineeringReleasePackage,item.package_id); out["release_packages"].append({"package_id":item.package_id,"code":pkg.code if pkg else None,"status":pkg.status if pkg else None,"snapshot_sha256":item.snapshot_sha256})
    events=db.scalars(select(EngineeringLifecycleEvent).where(EngineeringLifecycleEvent.entity_type==entity_type,EngineeringLifecycleEvent.entity_id==entity_id).order_by(EngineeringLifecycleEvent.created_at)).all()
    out["lifecycle"]=[{"action":e.action,"actor":e.actor,"event_hash":e.event_hash,"previous_hash":e.previous_hash,"created_at":e.created_at.isoformat()} for e in events]
    return out


def lifecycle_dashboard(db: Session) -> dict:
    cfg=get_settings(); now=_now()
    active_holds=int(db.scalar(select(func.count()).select_from(EngineeringLegalHold).where(EngineeringLegalHold.active==True,or_(EngineeringLegalHold.expires_at.is_(None),EngineeringLegalHold.expires_at>now))) or 0)
    return {
        "status":"CONTROLLED",
        "authoritative_purge_enabled":bool(cfg.data_lifecycle_authoritative_purge_enabled),
        "active_policies":int(db.scalar(select(func.count()).select_from(EngineeringRetentionPolicy).where(EngineeringRetentionPolicy.active==True)) or 0),
        "active_legal_holds":active_holds,
        "pending_purge_authorizations":int(db.scalar(select(func.count()).select_from(EngineeringPurgeRequest).where(EngineeringPurgeRequest.status=="pending_authorization")) or 0),
        "authorized_purges":int(db.scalar(select(func.count()).select_from(EngineeringPurgeRequest).where(EngineeringPurgeRequest.status=="authorized")) or 0),
        "archived_entities":int(db.scalar(select(func.count()).select_from(EngineeringDataLifecycleState).where(EngineeringDataLifecycleState.state=="archived")) or 0),
        "projection_purges":int(db.scalar(select(func.count()).select_from(EngineeringDataLifecycleState).where(EngineeringDataLifecycleState.state=="projections_purged")) or 0),
        "released_packages_immutable":True,
        "projection_purge_preserves_postgresql_chunks":True,
        "machine_control":False,
    }
