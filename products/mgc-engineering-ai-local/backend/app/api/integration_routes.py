from __future__ import annotations

import hashlib
import os
import re
import mimetypes
import shutil
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import Identity, get_identity, is_engineering_admin
from app.db.models import (
    CadConversionJob,
    Document,
    DocumentStatus,
    ExternalObject,
    ExternalObjectVersion,
    ExternalSystem,
    IntegrationEntityMapping,
    IntegrationIngestEvent,
    IntegrationRun,
    Project,
    Relationship,
    SyncCursor,
)
from app.db.session import get_db
from app.integrations import build_connector, supported_connector_types
from app.integrations.cad_gateway import CadGatewayConnector
from app.integrations.sync import IntegrationSyncBusy, replay_quarantined_event, sync_external_system
from app.integrations.webhook import verify_signature
from app.schemas.api import (
    CadConvertRequest, ExternalSystemCreate, ExternalSystemUpdate, IntegrationSyncRequest,
    IntegrationEntityMappingCreate, IntegrationEntityMappingUpdate, IntegrationReconciliationRequest, IntegrationCertificationRequest,
)
from app.services.audit import log_document_activity, log_event
from app.services.ingest import ingest_document
from app.services.integration_hardening import age_quality_snapshot, aggregate_system_quality, contract_for
from app.services.integration_reconciliation import build_reconciliation_report, canonical_target_exists, system_reconciliation_role
from app.services.integration_certification import live_contract_probe, runtime_posture, static_contract_report, sync_allowed
from app.services.native_cad import gateway_config_supports, native_cad_profile, preferred_conversion_target

router = APIRouter(tags=["integrations"])


def _webhook_secret(system: ExternalSystem) -> str:
    env_name = (system.secret_config_json or {}).get("webhook_secret_env")
    return os.getenv(str(env_name), "") if env_name else ""


def _now():
    return datetime.now(timezone.utc)


def _admin(identity: Identity):
    if not is_engineering_admin(identity):
        raise HTTPException(403, "Engineering AI administrator group required")


def _allowed(doc: Document, identity: Identity) -> bool:
    return bool(set(doc.acl_groups or ["all"]) & set(identity.groups + ["all"]))


def _validate_secret_refs(refs: dict) -> dict:
    for key, value in refs.items():
        if not key.endswith("_env"):
            raise HTTPException(400, f"Secret field '{key}' must be an environment-variable reference such as token_env")
        if not isinstance(value, str) or not value or len(value) > 128:
            raise HTTPException(400, f"Invalid environment variable reference for {key}")
    return refs



def _validate_required_fields(fields: list[str]) -> list[str]:
    if len(fields) > 64:
        raise HTTPException(400, "At most 64 integration required fields are allowed")
    out: list[str] = []
    for raw in fields:
        field = str(raw).strip()
        if not field or len(field) > 128 or not re.fullmatch(r"[A-Za-z0-9_.-]+", field):
            raise HTTPException(400, f"Invalid integration required field: {field!r}")
        if field not in out:
            out.append(field)
    return out

def _system_view(x: ExternalSystem, data_quality: dict | None = None) -> dict:
    return {
        "id": x.id,
        "code": x.code,
        "name": x.name,
        "connector_type": x.connector_type,
        "enabled": x.enabled,
        "config": x.config_json,
        "secret_refs": sorted((x.secret_config_json or {}).keys()),
        "acl_groups": x.acl_groups,
        "source_domain": x.source_domain,
        "reconciliation_role": system_reconciliation_role(x),
        "contract_version": x.contract_version,
        "expected_freshness_minutes": x.expected_freshness_minutes,
        "required_fields": x.required_fields or [],
        "contract": contract_for(x),
        "data_quality": data_quality if data_quality is not None else (x.last_quality_json or {"level": "UNKNOWN", "score": None}),
        "last_quality_at": x.last_quality_at.isoformat() if x.last_quality_at else None,
        "last_health_status": x.last_health_status,
        "last_health_at": x.last_health_at.isoformat() if x.last_health_at else None,
        "last_sync_status": x.last_sync_status,
        "last_sync_at": x.last_sync_at.isoformat() if x.last_sync_at else None,
    }


def _runtime_quality(db: Session, system: ExternalSystem) -> dict:
    objects = db.scalars(select(ExternalObject).where(ExternalObject.system_id == system.id)).all()
    quarantine = int(db.scalar(select(func.count()).select_from(IntegrationIngestEvent).where(
        IntegrationIngestEvent.system_id == system.id,
        IntegrationIngestEvent.status == "quarantined",
    )) or 0)
    return aggregate_system_quality(
        objects, expected_freshness_minutes=system.expected_freshness_minutes, quarantined=quarantine, failed=0
    )


@router.get("/auth/config")
def auth_config(identity: Identity = Depends(get_identity)):
    cfg = get_settings()
    return {"mode": cfg.auth_mode, "engineer_only": cfg.engineer_only_access, "is_admin": is_engineering_admin(identity)}




@router.post("/integrations/webhooks/{system_code}", status_code=202)
async def integration_webhook(
    system_code: str,
    request: Request,
    x_mgc_timestamp: str | None = Header(default=None, alias="X-MGC-Timestamp"),
    x_mgc_signature: str | None = Header(default=None, alias="X-MGC-Signature"),
    db: Session = Depends(get_db),
):
    system = db.scalar(select(ExternalSystem).where(ExternalSystem.code == system_code.lower(), ExternalSystem.enabled == True))  # noqa: E712
    if not system:
        raise HTTPException(404)
    secret = _webhook_secret(system)
    if not secret:
        raise HTTPException(503, "Webhook secret is not configured")
    body = await request.body()
    if not x_mgc_timestamp or not x_mgc_signature or not verify_signature(body, x_mgc_timestamp, x_mgc_signature, secret, get_settings().webhook_max_skew_seconds):
        raise HTTPException(401, "Invalid webhook signature")
    try:
        from app.workers.tasks import sync_external_system_task
        task = sync_external_system_task.delay(system.id)
        task_id = task.id
    except Exception as exc:
        raise HTTPException(503, f"Queue unavailable: {exc}")
    log_event(db, f"webhook:{system.code}", "INTEGRATION_WEBHOOK", "external_system", system.id, {"task_id": task_id})
    return {"accepted": True, "system": system.code, "task_id": task_id}


@router.get("/cad/gateways")
def cad_gateways(identity: Identity = Depends(get_identity), db: Session = Depends(get_db)):
    rows = db.scalars(select(ExternalSystem).where(ExternalSystem.connector_type == "cad_gateway", ExternalSystem.enabled == True).order_by(ExternalSystem.code)).all()  # noqa: E712
    return [{
        "code": x.code,
        "name": x.name,
        "vendor": (x.config_json or {}).get("vendor"),
        "vendors": (x.config_json or {}).get("vendors", []),
        "extensions": (x.config_json or {}).get("extensions", []),
        "last_health_status": x.last_health_status,
    } for x in rows]


@router.get("/cad/native-formats")
def native_cad_formats(identity: Identity = Depends(get_identity)):
    formats = []
    for ext in sorted(get_settings().proprietary_cad_extension_set):
        profile = native_cad_profile(ext)
        if profile:
            formats.append({
                "extension": ext,
                "vendor": profile.vendor,
                "product": profile.product,
                "document_kind": profile.document_kind,
                "preferred_target": profile.preferred_target,
                "alternate_targets": list(profile.alternate_targets),
            })
    return {"formats": formats}


@router.get("/integrations/types")
def connector_types(identity: Identity = Depends(get_identity)):
    _admin(identity)
    vendor_formats = []
    for ext in sorted(get_settings().proprietary_cad_extension_set):
        profile = native_cad_profile(ext)
        if profile:
            vendor_formats.append({"extension": ext, "vendor": profile.vendor, "product": profile.product, "kind": profile.document_kind})
    return {
        "types": supported_connector_types(),
        "deterministic_cad": ["step", "stp", "stl", "dxf"],
        "gateway_cad": sorted(get_settings().proprietary_cad_extension_set),
        "vendor_formats": vendor_formats,
        "security": "credentials are referenced via environment variables and are not returned by the API",
    }


@router.get("/integrations")
def list_systems(identity: Identity = Depends(get_identity), db: Session = Depends(get_db)):
    _admin(identity)
    rows = db.scalars(select(ExternalSystem).order_by(ExternalSystem.code)).all()
    return [_system_view(x, _runtime_quality(db, x)) for x in rows]


@router.post("/integrations")
def create_system(req: ExternalSystemCreate, identity: Identity = Depends(get_identity), db: Session = Depends(get_db)):
    _admin(identity)
    if req.connector_type not in supported_connector_types():
        raise HTTPException(400, f"Unsupported connector type: {req.connector_type}")
    code = req.code.strip().lower()
    if not code:
        raise HTTPException(400, "Integration code is required")
    if db.scalar(select(ExternalSystem).where(ExternalSystem.code == code)):
        raise HTTPException(409, "Integration code already exists")
    system = ExternalSystem(
        code=code,
        name=req.name,
        connector_type=req.connector_type,
        enabled=req.enabled,
        config_json=req.config,
        secret_config_json=_validate_secret_refs(req.secrets),
        acl_groups=req.acl_groups or ["all"],
        source_domain=(req.source_domain or (req.connector_type.split("_", 1)[0] if req.connector_type.split("_", 1)[0] in {"plm", "pdm", "erp", "mes", "qms", "cad"} else ("files" if req.connector_type == "mounted_folder" else "engineering"))),
        contract_version=req.contract_version,
        expected_freshness_minutes=req.expected_freshness_minutes,
        required_fields=_validate_required_fields(req.required_fields),
    )
    db.add(system); db.commit(); db.refresh(system)
    log_event(db, identity.user, "INTEGRATION_CREATE", "external_system", system.id, {"code": system.code, "type": system.connector_type})
    return _system_view(system)


@router.patch("/integrations/{system_id}")
def update_system(system_id: str, req: ExternalSystemUpdate, identity: Identity = Depends(get_identity), db: Session = Depends(get_db)):
    _admin(identity)
    system = db.get(ExternalSystem, system_id)
    if not system:
        raise HTTPException(404)
    if req.name is not None: system.name = req.name
    if req.config is not None: system.config_json = req.config
    if req.secrets is not None: system.secret_config_json = _validate_secret_refs(req.secrets)
    if req.acl_groups is not None: system.acl_groups = req.acl_groups or ["all"]
    if req.enabled is not None: system.enabled = req.enabled
    if req.source_domain is not None: system.source_domain = req.source_domain
    if req.contract_version is not None: system.contract_version = req.contract_version
    if "expected_freshness_minutes" in req.model_fields_set: system.expected_freshness_minutes = req.expected_freshness_minutes
    if req.required_fields is not None: system.required_fields = _validate_required_fields(req.required_fields)
    db.commit(); db.refresh(system)
    log_event(db, identity.user, "INTEGRATION_UPDATE", "external_system", system.id, {"code": system.code})
    return _system_view(system)


@router.post("/integrations/{system_id}/health")
def health(system_id: str, identity: Identity = Depends(get_identity), db: Session = Depends(get_db)):
    _admin(identity)
    system = db.get(ExternalSystem, system_id)
    if not system:
        raise HTTPException(404)
    connector = build_connector(system.connector_type, system.config_json or {}, system.secret_config_json or {})
    result = connector.health()
    system.last_health_status = "ok" if result.ok else "failed"
    system.last_health_at = _now(); db.commit()
    log_event(db, identity.user, "INTEGRATION_HEALTH", "external_system", system.id, {"ok": result.ok})
    return {"ok": result.ok, "message": result.message, "latency_ms": result.latency_ms, "details": result.details}


@router.post("/integrations/{system_id}/certify")
def certify_integration(system_id: str, req: IntegrationCertificationRequest, identity: Identity = Depends(get_identity), db: Session = Depends(get_db)):
    _admin(identity)
    system = db.get(ExternalSystem, system_id)
    if not system:
        raise HTTPException(404)
    report = live_contract_probe(system, sample_limit=req.sample_limit) if req.live_probe else static_contract_report(system)
    report["runtime_posture"] = runtime_posture(db, system)
    log_event(db, identity.user, "INTEGRATION_CERTIFICATION", "external_system", system.id, {"decision": report["decision"], "scope": report["scope"], "domain": report.get("domain")})
    return report


@router.get("/integrations/{system_id}/runtime-posture")
def integration_runtime_posture(system_id: str, identity: Identity = Depends(get_identity), db: Session = Depends(get_db)):
    _admin(identity)
    system = db.get(ExternalSystem, system_id)
    if not system:
        raise HTTPException(404)
    return runtime_posture(db, system)


@router.post("/integrations/{system_id}/sync")
def sync(system_id: str, req: IntegrationSyncRequest, identity: Identity = Depends(get_identity), db: Session = Depends(get_db)):
    _admin(identity)
    system = db.get(ExternalSystem, system_id)
    if not system:
        raise HTTPException(404)
    if not system.enabled:
        raise HTTPException(409, "Integration is disabled")
    if system.connector_type == "cad_gateway":
        raise HTTPException(400, "CAD gateway is a converter and cannot be synchronized")
    allowed, posture = sync_allowed(db, system)
    if not allowed:
        raise HTTPException(409, {"code": "INTEGRATION_DEGRADED_READ_ONLY", "runtime_posture": posture})
    if req.reset_cursor:
        db.execute(delete(SyncCursor).where(SyncCursor.system_id == system.id)); db.commit()
    try:
        result = sync_external_system(db, system, identity.groups, req.page_limit, req.max_pages)
    except IntegrationSyncBusy as exc:
        raise HTTPException(409, str(exc))
    log_event(db, identity.user, "INTEGRATION_SYNC", "external_system", system.id, result)
    return result


@router.get("/integrations/{system_id}/runs")
def runs(system_id: str, limit: int = 50, identity: Identity = Depends(get_identity), db: Session = Depends(get_db)):
    _admin(identity)
    rows = db.scalars(select(IntegrationRun).where(IntegrationRun.system_id == system_id).order_by(IntegrationRun.started_at.desc()).limit(min(max(limit, 1), 200))).all()
    return [{
        "id": r.id, "status": r.status, "imported": r.imported_count, "skipped": r.skipped_count,
        "quarantined": r.quarantined_count, "replayed": r.replayed_count, "failed": r.failed_count,
        "data_quality": r.quality_json, "errors": r.error_json, "started_at": r.started_at.isoformat(),
        "finished_at": r.finished_at.isoformat() if r.finished_at else None,
    } for r in rows]


@router.get("/integrations/{system_id}/objects")
def objects(system_id: str, limit: int = 100, identity: Identity = Depends(get_identity), db: Session = Depends(get_db)):
    _admin(identity)
    system = db.get(ExternalSystem, system_id)
    if not system:
        raise HTTPException(404)
    rows = db.scalars(select(ExternalObject).where(ExternalObject.system_id == system_id).order_by(ExternalObject.last_seen_at.desc()).limit(min(max(limit, 1), 500))).all()
    out = []
    for x in rows:
        current_quality = age_quality_snapshot(x.data_quality_json or {}, x.source_modified_at, system.expected_freshness_minutes)
        out.append({
            "external_id": x.external_id, "object_type": x.object_type, "name": x.name, "part_number": x.part_number,
            "revision": x.revision, "document_id": x.document_id,
            "source_modified_at": x.source_modified_at.isoformat() if x.source_modified_at else None,
            "data_confidence_score": current_quality.get("score"), "data_confidence_level": current_quality.get("level"),
            "data_quality": current_quality, "last_seen_at": x.last_seen_at.isoformat(),
        })
    return out


@router.get("/integrations/{system_id}/objects/{external_id}/history")
def object_history(system_id: str, external_id: str, identity: Identity = Depends(get_identity), db: Session = Depends(get_db)):
    _admin(identity)
    rows = db.scalars(select(ExternalObjectVersion).where(ExternalObjectVersion.system_id == system_id, ExternalObjectVersion.external_id == external_id).order_by(ExternalObjectVersion.observed_at.desc())).all()
    return [{"id": x.id, "source_fingerprint": x.source_fingerprint, "document_id": x.document_id, "sha256": x.sha256, "metadata": x.metadata_json, "observed_at": x.observed_at.isoformat()} for x in rows]


@router.get("/integrations/{system_id}/quality")
def integration_quality(system_id: str, identity: Identity = Depends(get_identity), db: Session = Depends(get_db)):
    _admin(identity)
    system = db.get(ExternalSystem, system_id)
    if not system:
        raise HTTPException(404)
    outstanding_total = int(db.scalar(select(func.count()).select_from(IntegrationIngestEvent).where(
        IntegrationIngestEvent.system_id == system_id,
        IntegrationIngestEvent.status == "quarantined",
    )) or 0)
    outstanding = db.scalars(select(IntegrationIngestEvent).where(
        IntegrationIngestEvent.system_id == system_id,
        IntegrationIngestEvent.status == "quarantined",
    ).order_by(IntegrationIngestEvent.first_received_at.desc()).limit(20)).all()
    return {
        "system": _system_view(system, _runtime_quality(db, system)),
        "outstanding_quarantine": outstanding_total,
        "recent_quarantine": [{
            "id": e.id, "external_id": e.external_id, "object_type": e.object_type,
            "status": e.status, "attempt_count": e.attempt_count, "validation": e.validation_json,
            "data_quality": e.quality_json, "error": e.error_json,
            "first_received_at": e.first_received_at.isoformat(),
        } for e in outstanding],
    }


@router.get("/integrations/{system_id}/quarantine")
def integration_quarantine(system_id: str, limit: int = 100, identity: Identity = Depends(get_identity), db: Session = Depends(get_db)):
    _admin(identity)
    if not db.get(ExternalSystem, system_id):
        raise HTTPException(404)
    rows = db.scalars(select(IntegrationIngestEvent).where(
        IntegrationIngestEvent.system_id == system_id,
        IntegrationIngestEvent.status.in_(["quarantined", "failed"]),
    ).order_by(IntegrationIngestEvent.first_received_at.desc()).limit(min(max(limit, 1), 500))).all()
    return [{
        "id": e.id, "external_id": e.external_id, "object_type": e.object_type, "status": e.status,
        "attempt_count": e.attempt_count, "payload_sha256": e.payload_sha256,
        "has_replay_payload": bool(e.quarantine_path), "validation": e.validation_json,
        "data_quality": e.quality_json, "error": e.error_json,
        "first_received_at": e.first_received_at.isoformat(),
        "last_attempt_at": e.last_attempt_at.isoformat(),
    } for e in rows]


@router.post("/integrations/{system_id}/quarantine/{event_id}/replay")
def replay_integration_event(system_id: str, event_id: str, identity: Identity = Depends(get_identity), db: Session = Depends(get_db)):
    _admin(identity)
    system = db.get(ExternalSystem, system_id)
    event = db.get(IntegrationIngestEvent, event_id)
    if not system or not event or event.system_id != system_id:
        raise HTTPException(404)
    result = replay_quarantined_event(db, system, event)
    log_event(db, identity.user, "INTEGRATION_REPLAY", "integration_ingest_event", event.id, {
        "system": system.code, "external_id": event.external_id, "result": result.get("status"),
    })
    return result


@router.post("/cad/convert")
def convert_native_cad(req: CadConvertRequest, identity: Identity = Depends(get_identity), db: Session = Depends(get_db)):
    source = db.get(Document, req.document_id)
    if not source or not _allowed(source, identity):
        raise HTTPException(404)
    if source.extension not in get_settings().proprietary_cad_extension_set:
        raise HTTPException(400, "Document is not configured as native CAD")

    gateways = db.scalars(
        select(ExternalSystem).where(
            ExternalSystem.connector_type == "cad_gateway",
            ExternalSystem.enabled == True,  # noqa: E712
        ).order_by(ExternalSystem.code)
    ).all()
    gateway_system = None
    if req.gateway_system_code:
        gateway_system = next((g for g in gateways if g.code == req.gateway_system_code.lower()), None)
        if not gateway_system:
            raise HTTPException(404, "Enabled CAD gateway not found")
        if not gateway_config_supports(gateway_system.config_json or {}, source.extension):
            declared = gateway_system.config_json or {}
            if declared.get("vendor") or declared.get("vendors") or declared.get("extensions"):
                raise HTTPException(409, f"CAD gateway '{gateway_system.code}' does not declare support for {source.extension}")
    else:
        # Prefer a gateway that explicitly declares the correct vendor/extension.
        gateway_system = next((g for g in gateways if gateway_config_supports(g.config_json or {}, source.extension)), None)
        # Backward-compatible generic gateway is allowed only if no declared match exists.
        if not gateway_system:
            gateway_system = next((g for g in gateways if not any((g.config_json or {}).get(k) for k in ("vendor", "vendors", "extensions"))), None)
        if not gateway_system:
            profile = native_cad_profile(source.extension)
            product = profile.product if profile else source.extension
            raise HTTPException(404, f"No enabled local CAD gateway is configured for {product}")

    requested_target = req.target_format.lower().lstrip(".")
    target = preferred_conversion_target(source.extension) if requested_target == "auto" else requested_target
    # T-FLEX GRB is polymorphic. Keep 'auto' so the local T-FLEX gateway can
    # inspect whether the file is drawing-first or model-first.
    if source.extension == ".grb" and requested_target == "auto":
        target = "auto"

    job = CadConversionJob(
        document_id=source.id,
        source_format=source.extension.lstrip("."),
        target_format=target,
        status="running",
        gateway_system_id=gateway_system.id,
    )
    db.add(job); db.commit(); db.refresh(job)
    try:
        connector = build_connector(gateway_system.connector_type, gateway_system.config_json or {}, gateway_system.secret_config_json or {})
        if not isinstance(connector, CadGatewayConnector):
            raise RuntimeError("Configured system is not a CAD gateway")
        staging_dir = get_settings().storage_dir / "cad-conversion-staging" / job.id
        converted, conversion_meta = connector.convert(Path(source.stored_path), target, staging_dir)
        digest = hashlib.sha256(converted.read_bytes()).hexdigest()
        previous_rel = db.scalar(select(Relationship).where(Relationship.subject_type == "document", Relationship.subject_id == source.id, Relationship.predicate == "converted_to").order_by(Relationship.created_at.desc()))
        previous_doc = db.get(Document, previous_rel.object_id) if previous_rel else None
        same_gateway = bool(
            previous_rel
            and (previous_rel.metadata_json or {}).get("gateway") == conversion_meta.get("gateway")
            and (previous_rel.metadata_json or {}).get("sdk_version") == conversion_meta.get("sdk_version")
            and (previous_rel.metadata_json or {}).get("target_format") == conversion_meta.get("target_format")
        )
        if previous_doc and previous_doc.sha256 == digest and same_gateway:
            derived = previous_doc
        else:
            permanent = get_settings().storage_dir / "derived" / source.id / digest[:16] / converted.name
            permanent.parent.mkdir(parents=True, exist_ok=True)
            if not permanent.exists():
                permanent.write_bytes(converted.read_bytes())
            derived = Document(
                filename=converted.name,
                stored_path=str(permanent),
                source_path=f"derived:{source.id}",
                mime_type=mimetypes.guess_type(converted.name)[0] or "application/octet-stream",
                extension=permanent.suffix.lower(),
                size_bytes=permanent.stat().st_size,
                sha256=digest,
                status=DocumentStatus.uploaded,
                part_number=source.part_number,
                revision=source.revision,
                project_code=source.project_code,
                acl_groups=source.acl_groups,
                extracted_metadata={"derived_from_document_id": source.id, "conversion": conversion_meta},
            )
            db.add(derived); db.commit(); db.refresh(derived)
            derived = ingest_document(db, derived)
        if not (previous_rel and previous_rel.object_id == derived.id and same_gateway):
            db.add(Relationship(
                subject_type="document",
                subject_id=source.id,
                predicate="converted_to",
                object_type="document",
                object_id=derived.id,
                evidence_document_id=source.id,
                metadata_json=conversion_meta,
            ))
        job.status = "ready"; job.output_document_id = derived.id; job.metadata_json = conversion_meta; db.commit()
        shutil.rmtree(staging_dir, ignore_errors=True)
        profile = native_cad_profile(source.extension)
        conversion_event = {
            "output_document_id": derived.id,
            "gateway": gateway_system.code,
            "vendor": profile.vendor if profile else conversion_meta.get("vendor"),
            "target_format": conversion_meta.get("target_format"),
        }
        log_event(db, identity.user, "CAD_CONVERT", "document", source.id, conversion_event)
        log_document_activity(db, source.id, identity.user, "CAD_CONVERT", "Нативный CAD подготовлен для инженерного анализа", conversion_event)
        log_document_activity(db, derived.id, identity.user, "CAD_DERIVATIVE_CREATED", "Создана контролируемая производная из нативного CAD", {"source_document_id": source.id, **conversion_event})
        return {
            "job_id": job.id,
            "status": job.status,
            "source_document_id": source.id,
            "output_document_id": derived.id,
            "gateway": gateway_system.code,
            "metadata": conversion_meta,
        }
    except Exception as exc:
        try:
            shutil.rmtree(get_settings().storage_dir / "cad-conversion-staging" / job.id, ignore_errors=True)
        except Exception:
            pass
        job.status = "failed"; job.error = f"{type(exc).__name__}: {exc}"; db.commit()
        status_code = 503 if type(exc).__name__ == "CircuitOpenError" else 502
        raise HTTPException(status_code, job.error)



def _mapping_view(x: IntegrationEntityMapping, db: Session) -> dict:
    obj = db.scalar(select(ExternalObject).where(ExternalObject.system_id == x.system_id, ExternalObject.external_id == x.source_external_id))
    stale_reasons = []
    if obj and x.source_fingerprint and obj.source_fingerprint and x.source_fingerprint != obj.source_fingerprint:
        stale_reasons.append("SOURCE_FINGERPRINT_CHANGED")
    return {
        "id": x.id, "system_id": x.system_id, "project_code": x.project_code,
        "source_entity_type": x.source_entity_type, "source_external_id": x.source_external_id,
        "source_key": x.source_key, "canonical_entity_type": x.canonical_entity_type,
        "canonical_key": x.canonical_key, "mapping_method": x.mapping_method, "status": x.status,
        "confidence": x.confidence, "source_fingerprint": x.source_fingerprint,
        "stale": bool(stale_reasons), "stale_reasons": stale_reasons,
        "notes": x.notes, "created_by": x.created_by, "verified_by": x.verified_by,
        "last_verified_at": x.last_verified_at.isoformat() if x.last_verified_at else None,
        "created_at": x.created_at.isoformat(), "updated_at": x.updated_at.isoformat(),
    }


@router.get("/integrations/mappings")
def list_entity_mappings(system_id: str | None = None, project_code: str | None = None, identity: Identity = Depends(get_identity), db: Session = Depends(get_db)):
    _admin(identity)
    q = select(IntegrationEntityMapping).order_by(IntegrationEntityMapping.updated_at.desc())
    if system_id: q = q.where(IntegrationEntityMapping.system_id == system_id)
    if project_code: q = q.where((IntegrationEntityMapping.project_code == project_code) | (IntegrationEntityMapping.project_code.is_(None)))
    return [_mapping_view(x, db) for x in db.scalars(q).all()]


@router.post("/integrations/mappings")
def create_entity_mapping(req: IntegrationEntityMappingCreate, identity: Identity = Depends(get_identity), db: Session = Depends(get_db)):
    _admin(identity)
    system = db.get(ExternalSystem, req.system_id)
    if not system: raise HTTPException(404, "Integration not found")
    if not db.scalar(select(Project).where(Project.code == req.project_code)):
        raise HTTPException(404, "Project not found")
    obj = db.scalar(select(ExternalObject).where(ExternalObject.system_id == req.system_id, ExternalObject.external_id == req.source_external_id))
    if not obj: raise HTTPException(404, "External object not found")
    if not canonical_target_exists(db, req.project_code, req.canonical_entity_type, req.canonical_key):
        raise HTTPException(409, "Canonical target does not exist in the selected project")
    existing = db.scalar(select(IntegrationEntityMapping).where(
        IntegrationEntityMapping.system_id == req.system_id,
        IntegrationEntityMapping.source_entity_type == req.source_entity_type,
        IntegrationEntityMapping.source_external_id == req.source_external_id,
        IntegrationEntityMapping.source_key == (req.source_key.strip().upper() if req.source_key else None),
        IntegrationEntityMapping.canonical_entity_type == req.canonical_entity_type,
    ))
    if existing: raise HTTPException(409, "Mapping already exists")
    row = IntegrationEntityMapping(
        system_id=req.system_id, project_code=req.project_code, source_entity_type=req.source_entity_type,
        source_external_id=req.source_external_id, source_key=(req.source_key.strip().upper() if req.source_key else None), canonical_entity_type=req.canonical_entity_type,
        canonical_key=req.canonical_key.strip().upper(), mapping_method="manual", status="confirmed",
        source_fingerprint=obj.source_fingerprint, confidence=1.0, notes=req.notes, created_by=identity.user,
        verified_by=identity.user, last_verified_at=_now(),
    )
    db.add(row); db.commit(); db.refresh(row)
    log_event(db, identity.user, "INTEGRATION_MAPPING_CREATE", "integration_entity_mapping", row.id, {"system": system.code, "source_external_id": row.source_external_id, "canonical_key": row.canonical_key})
    return _mapping_view(row, db)


@router.patch("/integrations/mappings/{mapping_id}")
def update_entity_mapping(mapping_id: str, req: IntegrationEntityMappingUpdate, identity: Identity = Depends(get_identity), db: Session = Depends(get_db)):
    _admin(identity)
    row = db.get(IntegrationEntityMapping, mapping_id)
    if not row: raise HTTPException(404)
    if req.status is not None: row.status = req.status
    if req.canonical_key is not None:
        if row.project_code and not canonical_target_exists(db, row.project_code, row.canonical_entity_type, req.canonical_key):
            raise HTTPException(409, "Canonical target does not exist in the selected project")
        row.canonical_key = req.canonical_key.strip().upper()
    if req.notes is not None: row.notes = req.notes
    if req.reverify:
        obj = db.scalar(select(ExternalObject).where(ExternalObject.system_id == row.system_id, ExternalObject.external_id == row.source_external_id))
        if not obj: raise HTTPException(409, "External object no longer exists")
        row.source_fingerprint = obj.source_fingerprint
        row.verified_by = identity.user
        row.last_verified_at = _now()
        if row.status != "retired": row.status = "confirmed"
    db.commit(); db.refresh(row)
    log_event(db, identity.user, "INTEGRATION_MAPPING_UPDATE", "integration_entity_mapping", row.id, {"status": row.status, "reverified": req.reverify})
    return _mapping_view(row, db)


@router.post("/integrations/reconciliation")
def reconciliation(req: IntegrationReconciliationRequest, identity: Identity = Depends(get_identity), db: Session = Depends(get_db)):
    _admin(identity)
    if not db.scalar(select(Project).where(Project.code == req.project_code)):
        raise HTTPException(404, "Project not found")
    roles = req.required_roles or ["ebom", "mbom", "genealogy", "defects"]
    invalid = sorted(set(roles) - {"ebom", "mbom", "genealogy", "defects"})
    if invalid: raise HTTPException(400, f"Unsupported reconciliation roles: {', '.join(invalid)}")
    policy = {
        "required_roles": roles, "min_mapping_coverage": req.min_mapping_coverage,
        "min_freshness_compliance": req.min_freshness_compliance, "min_sync_success_rate": req.min_sync_success_rate,
    }
    result = build_reconciliation_report(db, req.project_code, policy=policy)
    log_event(db, identity.user, "INTEGRATION_RECONCILIATION", "project", req.project_code, {"pilot_status": result["pilot_acceptance"]["status"], "schema": result["schema"]})
    return result
