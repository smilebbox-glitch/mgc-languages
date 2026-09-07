from __future__ import annotations

import hashlib, json, re
from urllib.parse import urlparse
from datetime import datetime, timezone
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.adapters.handover import GenericRestHandoverAdapter
from app.core.config import get_settings
from app.core.security import Identity, identity_snapshot
from app.db.models import ExternalSystem, EngineeringHandoverJob, EngineeringHandoverReceipt, EngineeringHandoverTarget, EngineeringReleasePackage
from app.ports.handover import HandoverWritePort
from app.services.approval_governance import release_manifest

TARGET_SOURCE_DOMAINS = {"plm", "pdm", "mes"}
TARGET_CONNECTOR_TYPES = {"engineering_rest", "plm_rest", "pdm_rest", "mes_rest"}
MODES = {"dry_run", "write"}


def _now(): return datetime.now(timezone.utc)
def _canon(value): return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"), default=str)
def _sha(value): return hashlib.sha256(_canon(value).encode()).hexdigest()
def _safe_code(value: str) -> str:
    code=value.strip().lower()
    if not re.fullmatch(r"[a-z0-9][a-z0-9._-]{1,94}[a-z0-9]", code): raise ValueError("Invalid handover target code")
    return code

def serialize_target(db: Session, row: EngineeringHandoverTarget) -> dict:
    system=db.get(ExternalSystem,row.external_system_id)
    return {"id":row.id,"code":row.code,"name":row.name,"external_system_id":row.external_system_id,"external_system_code":system.code if system else None,"source_domain":system.source_domain if system else None,"environment":row.environment,"enabled":row.enabled,"allow_write":row.allow_write,"idempotency_supported":row.idempotency_supported,"receipt_required":row.receipt_required,"write_path":row.write_path,"reconcile_path_template":row.reconcile_path_template,"allowed_project_codes":row.allowed_project_codes_json or [],"allowed_manufacturing_areas":row.allowed_manufacturing_areas_json or [],"metadata":row.metadata_json or {},"created_by":row.created_by,"created_at":row.created_at.isoformat()}

def create_target(db: Session, *, code: str, name: str, external_system_id: str, environment: str, allow_write: bool, idempotency_supported: bool = True, receipt_required: bool = True, write_path: str, reconcile_path_template: str | None, allowed_projects: list[str], allowed_areas: list[str], metadata: dict, user: str) -> EngineeringHandoverTarget:
    code=_safe_code(code)
    if db.scalar(select(EngineeringHandoverTarget).where(EngineeringHandoverTarget.code==code)): raise ValueError("Handover target code already exists")
    system=db.get(ExternalSystem,external_system_id)
    if not system or not system.enabled: raise ValueError("Enabled external integration system required")
    if system.source_domain not in TARGET_SOURCE_DOMAINS or system.connector_type not in TARGET_CONNECTOR_TYPES: raise ValueError("v6.3.7 write targets are restricted to approved PLM/PDM/MES REST gateways")
    if not write_path.startswith("/") or "://" in write_path: raise ValueError("write_path must be a relative gateway path")
    if reconcile_path_template and (not reconcile_path_template.startswith("/") or "://" in reconcile_path_template): raise ValueError("reconcile_path_template must be relative")
    if allow_write and not idempotency_supported: raise ValueError("Controlled write target must guarantee Idempotency-Key semantics")
    if allow_write and receipt_required and not reconcile_path_template: raise ValueError("Write target requiring receipt must configure reconciliation endpoint")
    row=EngineeringHandoverTarget(code=code,name=name.strip(),external_system_id=external_system_id,environment=environment.strip().lower() or "test",enabled=True,allow_write=bool(allow_write),idempotency_supported=bool(idempotency_supported),receipt_required=bool(receipt_required),write_path=write_path,reconcile_path_template=reconcile_path_template,allowed_project_codes_json=sorted(set(allowed_projects or [])),allowed_manufacturing_areas_json=sorted(set(allowed_areas or [])),metadata_json=metadata or {},created_by=user)
    db.add(row); db.commit(); db.refresh(row); return row

def _validate_target_scope(target: EngineeringHandoverTarget, pkg: EngineeringReleasePackage) -> None:
    if not target.enabled: raise ValueError("Handover target is disabled")
    if target.allowed_project_codes_json and pkg.project_code not in set(target.allowed_project_codes_json): raise PermissionError("Release package project is not allowlisted for this target")
    if target.allowed_manufacturing_areas_json and pkg.manufacturing_area not in set(target.allowed_manufacturing_areas_json): raise PermissionError("Manufacturing area is not allowlisted for this target")

def build_job_payload(db: Session, pkg: EngineeringReleasePackage, target: EngineeringHandoverTarget) -> tuple[dict, str, dict, str]:
    rm=release_manifest(db,pkg)
    manifest=rm["manifest"]; manifest_sha=rm["manifest_sha256"]
    payload={"schema":"mgc-release-handover-v1","target_code":target.code,"target_environment":target.environment,"release_manifest":manifest,"release_manifest_sha256":manifest_sha,"source_system":"MGC Engineering AI Local","machine_control":False}
    return manifest,manifest_sha,payload,_sha(payload)

def create_job(db: Session, *, package_id: str, target_code: str, idempotency_key: str, mode: str, identity: Identity) -> EngineeringHandoverJob:
    mode=(mode or ("dry_run" if get_settings().handover_dry_run_default else "write")).lower()
    if mode not in MODES: raise ValueError("mode must be dry_run or write")
    pkg=db.get(EngineeringReleasePackage,package_id)
    if not pkg or pkg.status!="released": raise ValueError("Only a released Engineering Release Package can be handed over")
    target=db.scalar(select(EngineeringHandoverTarget).where(EngineeringHandoverTarget.code==target_code.strip().lower()))
    if not target: raise LookupError("Handover target not found")
    _validate_target_scope(target,pkg)
    key=idempotency_key.strip()
    if len(key)<8 or len(key)>128: raise ValueError("Idempotency-Key must be 8..128 characters")
    manifest,msha,payload,rsha=build_job_payload(db,pkg,target)
    existing=db.scalar(select(EngineeringHandoverJob).where(EngineeringHandoverJob.target_id==target.id,EngineeringHandoverJob.idempotency_key==key))
    if existing:
        if existing.request_sha256!=rsha or existing.package_id!=pkg.id or existing.mode!=mode: raise ValueError("Idempotency-Key was already used for a different handover command")
        return existing
    status="dry_run_ready" if mode=="dry_run" else "pending_authorization"
    job=EngineeringHandoverJob(package_id=pkg.id,target_id=target.id,idempotency_key=key,mode=mode,status=status,manifest_sha256=msha,request_sha256=rsha,manifest_json=manifest,payload_json=payload,created_by=identity.user,maker_identity_json=identity_snapshot(identity))
    db.add(job)
    try: db.commit()
    except IntegrityError:
        db.rollback(); return db.scalar(select(EngineeringHandoverJob).where(EngineeringHandoverJob.target_id==target.id,EngineeringHandoverJob.idempotency_key==key))
    db.refresh(job); return job

def authorize_job(db: Session, job: EngineeringHandoverJob, *, identity: Identity, identity_policy_id: str | None, assurance: dict) -> EngineeringHandoverJob:
    if job.mode!="write": raise ValueError("Dry-run jobs do not require write authorization")
    if job.status not in {"pending_authorization","authorized"}: raise ValueError("Handover job is not awaiting authorization")
    if identity.is_service_account: raise PermissionError("Human checker identity required")
    if identity.user==job.created_by: raise PermissionError("Maker-checker rule: handover creator cannot authorize external write")
    if job.checker_user:
        if job.checker_user!=identity.user: raise ValueError("Handover job is already authorized by another checker")
        return job
    job.checker_user=identity.user; job.checker_identity_json=identity_snapshot(identity); job.checker_assurance_json={**(assurance or {}),"identity_policy_id":identity_policy_id}; job.authorized_at=_now(); job.status="authorized"
    db.commit(); db.refresh(job); return job

def _write_gate(db: Session, job: EngineeringHandoverJob) -> tuple[EngineeringHandoverTarget,ExternalSystem]:
    cfg=get_settings(); target=db.get(EngineeringHandoverTarget,job.target_id); system=db.get(ExternalSystem,target.external_system_id) if target else None
    if not target or not system: raise LookupError("Handover target integration is unavailable")
    if not cfg.handover_write_enabled: raise PermissionError("External handover write-back is globally disabled")
    allowed=cfg.handover_allowed_target_code_set
    if not allowed or target.code not in allowed: raise PermissionError("Target is not in HANDOVER_ALLOWED_TARGET_CODES")
    if not target.enabled or not target.allow_write: raise PermissionError("Target write-back is not enabled")
    if not target.idempotency_supported: raise PermissionError("Target does not satisfy required idempotency contract")
    if not system.enabled: raise PermissionError("External integration system is disabled")
    base_url=str((system.config_json or {}).get("base_url") or "")
    parsed=urlparse(base_url)
    host=(parsed.hostname or "").lower()
    allowed_hosts=cfg.handover_allowed_host_set
    if not host or not allowed_hosts or host not in allowed_hosts: raise PermissionError("Target host is not in HANDOVER_ALLOWED_HOSTS")
    if cfg.app_env.lower() in {"prod","production"} and parsed.scheme.lower()!="https": raise PermissionError("Production handover gateway must use HTTPS")
    if job.status not in {"authorized","failed"} or not job.checker_user: raise PermissionError("Maker-checker authorization is required before write-back")
    return target,system

def execute_job(db: Session, job: EngineeringHandoverJob, *, identity: Identity, adapter: HandoverWritePort | None = None) -> EngineeringHandoverJob:
    if job.mode!="write": raise ValueError("Dry-run job cannot execute external write")
    if identity.is_service_account: raise PermissionError("Human identity required for controlled handover execution")
    if identity.user==job.created_by: raise PermissionError("Maker cannot execute own outbound handover")
    if job.status in {"delivered","reconciled"}: return job
    target,system=_write_gate(db,job)
    if int(job.attempt_count or 0) >= max(1,int(get_settings().handover_max_attempts)):
        raise PermissionError("Handover retry budget exhausted; operator review required")
    # Ensure the release manifest has not changed between command creation and execution.
    pkg=db.get(EngineeringReleasePackage,job.package_id)
    if not pkg or pkg.status!="released": raise ValueError("Release Package is no longer in released state")
    manifest,msha,payload,rsha=build_job_payload(db,pkg,target)
    if msha!=job.manifest_sha256 or rsha!=job.request_sha256: raise ValueError("Release Package/manifest changed after handover command creation; create a new job")
    job.attempt_count=int(job.attempt_count or 0)+1; job.status="delivering"; db.commit()
    headers={"Idempotency-Key":job.idempotency_key,"X-MGC-Handover-Job-ID":job.id,"X-MGC-Manifest-SHA256":job.manifest_sha256,"X-MGC-Request-SHA256":job.request_sha256}
    adapter=adapter or GenericRestHandoverAdapter()
    try:
        result=adapter.execute(system=system,target=target,payload=job.payload_json or {},headers=headers)
    except Exception as exc:
        job.status="failed"; job.error_json={"type":type(exc).__name__,"message":str(exc)[:1000]}; db.commit(); raise
    response=result.response or {}; response_sha=_sha(response)
    if result.ok and target.receipt_required and not result.external_receipt_id:
        job.status="failed"; job.error_json={"type":"MissingReceipt","message":"Target accepted request without required reconciliation receipt"}; db.commit(); raise RuntimeError("Target did not return required reconciliation receipt")
    job.status="delivered" if result.ok else "failed"; job.external_receipt_id=result.external_receipt_id; job.response_json=response; job.response_sha256=response_sha; job.executed_by=identity.user; job.execution_identity_json=identity_snapshot(identity); job.executed_at=_now(); job.error_json={}
    receipt=EngineeringHandoverReceipt(job_id=job.id,external_receipt_id=result.external_receipt_id,status=result.status or ("accepted" if result.ok else "failed"),response_sha256=response_sha,response_json=response,target_state_sha256=result.target_state_sha256)
    db.add(receipt); db.commit(); db.refresh(job); return job

def reconcile_job(db: Session, job: EngineeringHandoverJob, *, identity: Identity, adapter: HandoverWritePort | None = None) -> EngineeringHandoverJob:
    if job.status not in {"delivered","reconciled"}: raise ValueError("Only a delivered handover can be reconciled")
    if not job.external_receipt_id: raise ValueError("External receipt ID is required for reconciliation")
    if job.status=="reconciled": return job
    target=db.get(EngineeringHandoverTarget,job.target_id); system=db.get(ExternalSystem,target.external_system_id) if target else None
    if not target or not system: raise LookupError("Handover target integration is unavailable")
    # Reconciliation is read-only but still restricted to allowlisted, controlled targets.
    allowed=get_settings().handover_allowed_target_code_set
    if not allowed or target.code not in allowed: raise PermissionError("Target is not in HANDOVER_ALLOWED_TARGET_CODES")
    headers={"X-MGC-Handover-Job-ID":job.id,"X-MGC-Manifest-SHA256":job.manifest_sha256}
    adapter=adapter or GenericRestHandoverAdapter()
    result=adapter.reconcile(system=system,target=target,external_receipt_id=job.external_receipt_id,headers=headers)
    receipt=db.scalar(select(EngineeringHandoverReceipt).where(EngineeringHandoverReceipt.job_id==job.id))
    if not receipt: raise LookupError("Delivery receipt is missing")
    proof=result.response or {}
    echoed_manifest=str(proof.get("manifest_sha256") or proof.get("release_manifest_sha256") or "")
    echoed_request=str(proof.get("request_sha256") or "")
    if echoed_manifest and echoed_manifest != job.manifest_sha256:
        receipt.status="mismatch"; receipt.reconciled_at=_now(); job.status="reconciliation_failed"; job.reconciliation_json={"reason":"manifest_sha256_mismatch","reported":echoed_manifest}; db.commit(); raise ValueError("External reconciliation manifest hash does not match released handover")
    if echoed_request and echoed_request != job.request_sha256:
        receipt.status="mismatch"; receipt.reconciled_at=_now(); job.status="reconciliation_failed"; job.reconciliation_json={"reason":"request_sha256_mismatch","reported":echoed_request}; db.commit(); raise ValueError("External reconciliation request hash does not match handover command")
    if target.receipt_required and not (echoed_manifest or result.target_state_sha256):
        receipt.status="unverified"; receipt.reconciled_at=_now(); job.status="reconciliation_failed"; job.reconciliation_json={"reason":"missing_target_hash_proof"}; db.commit(); raise ValueError("External reconciliation did not provide required hash proof")
    receipt.status=result.status or "reconciled"; receipt.target_state_sha256=result.target_state_sha256; receipt.reconciled_at=_now(); receipt.response_json={**(receipt.response_json or {}),"reconciliation":proof}
    job.status="reconciled"; job.reconciled_at=_now(); job.reconciliation_json=proof
    db.commit(); db.refresh(job); return job

def serialize_job(db: Session, job: EngineeringHandoverJob) -> dict:
    target=db.get(EngineeringHandoverTarget,job.target_id); receipt=db.scalar(select(EngineeringHandoverReceipt).where(EngineeringHandoverReceipt.job_id==job.id))
    return {"id":job.id,"package_id":job.package_id,"target":serialize_target(db,target) if target else None,"idempotency_key":job.idempotency_key,"mode":job.mode,"status":job.status,"manifest_sha256":job.manifest_sha256,"request_sha256":job.request_sha256,"created_by":job.created_by,"maker_identity":job.maker_identity_json or {},"checker_user":job.checker_user,"checker_identity":job.checker_identity_json or {},"checker_assurance":job.checker_assurance_json or {},"authorized_at":job.authorized_at.isoformat() if job.authorized_at else None,"executed_by":job.executed_by,"execution_identity":job.execution_identity_json or {},"executed_at":job.executed_at.isoformat() if job.executed_at else None,"external_receipt_id":job.external_receipt_id,"response_sha256":job.response_sha256,"attempt_count":job.attempt_count,"error":job.error_json or {},"reconciled_at":job.reconciled_at.isoformat() if job.reconciled_at else None,"reconciliation":job.reconciliation_json or {},"receipt":{"status":receipt.status,"response_sha256":receipt.response_sha256,"target_state_sha256":receipt.target_state_sha256,"received_at":receipt.received_at.isoformat(),"reconciled_at":receipt.reconciled_at.isoformat() if receipt.reconciled_at else None} if receipt else None,"created_at":job.created_at.isoformat(),"updated_at":job.updated_at.isoformat()}

def handover_dashboard(db: Session) -> dict:
    cfg=get_settings()
    statuses={name:int(db.scalar(select(func.count()).select_from(EngineeringHandoverJob).where(EngineeringHandoverJob.status==name)) or 0) for name in ("pending_authorization","authorized","delivering","delivered","reconciled","failed","reconciliation_failed")}
    oldest=db.scalar(select(func.min(EngineeringHandoverJob.executed_at)).where(EngineeringHandoverJob.status=="delivered"))
    if oldest and oldest.tzinfo is None: oldest=oldest.replace(tzinfo=timezone.utc)
    oldest_age=max(0.0,(_now()-oldest).total_seconds()) if oldest else 0.0
    max_age=max(60,int(cfg.handover_reconciliation_max_age_seconds))
    degraded=bool(statuses["failed"] or statuses["reconciliation_failed"] or oldest_age>max_age)
    return {
        "status":"READ_ONLY" if not cfg.handover_write_enabled else "CONTROLLED_WRITE_ENABLED",
        "operational_status":"WARN" if degraded else "OK",
        "write_enabled":bool(cfg.handover_write_enabled),
        "dry_run_default":bool(cfg.handover_dry_run_default),
        "configured_targets":int(db.scalar(select(func.count()).select_from(EngineeringHandoverTarget).where(EngineeringHandoverTarget.enabled==True)) or 0),
        "write_enabled_targets":int(db.scalar(select(func.count()).select_from(EngineeringHandoverTarget).where(EngineeringHandoverTarget.enabled==True,EngineeringHandoverTarget.allow_write==True)) or 0),
        **statuses,
        "oldest_unreconciled_age_seconds":round(oldest_age,1),
        "reconciliation_max_age_seconds":max_age,
        "machine_control":False,
    }
