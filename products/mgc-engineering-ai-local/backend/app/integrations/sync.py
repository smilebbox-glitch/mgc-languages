from __future__ import annotations

import hashlib
import mimetypes
import shutil
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.models import (
    Document,
    DocumentStatus,
    ExternalObject,
    ExternalObjectVersion,
    ExternalSystem,
    IntegrationIngestEvent,
    IntegrationRun,
    SyncCursor,
)
from app.services.integration_hardening import (
    aggregate_system_quality,
    asset_from_snapshot,
    asset_snapshot,
    calculate_data_quality,
    contract_for,
    idempotency_key,
    parse_source_timestamp,
    publish_integration_quality,
    validate_asset_contract,
)

from app.services.data_lifecycle import enforce_upload_quota
from .registry import build_connector



class IntegrationSyncBusy(RuntimeError):
    pass


@contextmanager
def integration_sync_lock(db: Session, system_id: str):
    """Serialize one source-system sync on PostgreSQL; SQLite/dev is a no-op.

    The lock is session/connection scoped and bounded so a failed worker cannot make
    another replica wait forever. It protects checkpoint advancement and ingest-event
    idempotency from concurrent sync races.
    """
    bind = db.get_bind()
    if bind.dialect.name != "postgresql":
        yield
        return
    digest = hashlib.sha256(("mgc-integration-sync:" + system_id).encode()).digest()[:8]
    key = int.from_bytes(digest, "big") & ((1 << 63) - 1)
    timeout = max(float(get_settings().integration_sync_lock_timeout_seconds), 1.0)
    deadline = time.monotonic() + timeout
    # Keep a dedicated PostgreSQL connection open for the entire sync. The application
    # Session commits multiple times during large imports; a session-level lock taken on
    # that Session could otherwise be returned to the pool between commits.
    with bind.connect() as lock_conn:
        acquired = False
        try:
            while time.monotonic() < deadline:
                acquired = bool(lock_conn.execute(text("SELECT pg_try_advisory_lock(:key)"), {"key": key}).scalar())
                if acquired:
                    break
                time.sleep(0.25)
            if not acquired:
                raise IntegrationSyncBusy(f"Integration sync is already active for system {system_id}")
            yield
        finally:
            if acquired:
                lock_conn.execute(text("SELECT pg_advisory_unlock(:key)"), {"key": key})
                lock_conn.commit()

def _ingest(db, doc):
    from app.services.ingest import ingest_document
    return ingest_document(db, doc)


def _now():
    return datetime.now(timezone.utc)


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _immutable_path(system_id: str, external_id: str, digest: str, filename: str) -> Path:
    cfg = get_settings()
    safe_name = Path(filename).name
    external_bucket = hashlib.sha256(external_id.encode()).hexdigest()[:16]
    return cfg.storage_dir / "integrations" / system_id / external_bucket / digest[:16] / safe_name


def _quarantine_path(system: ExternalSystem, event: IntegrationIngestEvent, digest: str, filename: str) -> Path:
    safe_name = Path(filename).name
    return get_settings().storage_dir / "integration-quarantine" / system.code / event.id / digest[:16] / safe_name


def _copy_once(source: Path, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    if not target.exists():
        shutil.copy2(source, target)


def _source_fingerprint(asset, digest: str | None = None) -> str:
    return str(asset.checksum or asset.modified_at or asset.revision or digest or "")


def _accept_staged_asset(
    db: Session,
    system: ExternalSystem,
    asset,
    staged: Path,
    digest: str,
    existing: ExternalObject | None,
    event: IntegrationIngestEvent,
    quality: dict,
    source_modified_at: datetime | None,
    source_fingerprint: str,
) -> tuple[Document, bool]:
    """Persist immutable document + external object. Returns (document, imported_new_document)."""
    existing_doc = db.get(Document, existing.document_id) if existing and existing.document_id else None
    imported = False
    if existing_doc and existing_doc.sha256 == digest:
        doc = existing_doc
    else:
        permanent = _immutable_path(system.id, asset.external_id, digest, asset.name)
        area = str((asset.metadata or {}).get("manufacturing_area") or "").strip() or None
        enforce_upload_quota(db, project_code=asset.project_code, manufacturing_area=area, incoming_bytes=staged.stat().st_size)
        _copy_once(staged, permanent)
        provenance = {
            "external_system": system.code,
            "external_system_id": system.id,
            "external_id": asset.external_id,
            "external_kind": asset.kind,
            "source_domain": system.source_domain,
            "integration_contract": system.contract_version,
            "source_modified_at": source_modified_at.isoformat() if source_modified_at else None,
            "data_quality": quality,
            "ingest_event_id": event.id,
        }
        doc = Document(
            filename=asset.name,
            stored_path=str(permanent),
            source_path=f"{system.name}:{asset.external_id}",
            mime_type=mimetypes.guess_type(asset.name)[0] or "application/octet-stream",
            extension=permanent.suffix.lower(),
            size_bytes=permanent.stat().st_size,
            sha256=digest,
            status=DocumentStatus.uploaded,
            part_number=asset.part_number,
            revision=asset.revision,
            project_code=asset.project_code,
            manufacturing_area=area,
            acl_groups=(system.acl_groups or ["all"]),
            extracted_metadata={**(asset.metadata or {}), **provenance},
        )
        db.add(doc); db.commit(); db.refresh(doc)
        doc = _ingest(db, doc)
        imported = True

    if not existing:
        existing = ExternalObject(system_id=system.id, external_id=asset.external_id)
        db.add(existing)
    existing.object_type = asset.kind
    existing.name = asset.name
    existing.revision = asset.revision
    existing.part_number = asset.part_number
    existing.source_fingerprint = source_fingerprint or digest
    existing.document_id = doc.id
    existing.metadata_json = asset.metadata or {}
    existing.source_modified_at = source_modified_at
    existing.data_confidence_score = quality.get("score")
    existing.data_confidence_level = quality.get("level")
    existing.data_quality_json = quality
    existing.last_seen_at = _now()

    version_fingerprint = source_fingerprint or digest
    version = db.scalar(select(ExternalObjectVersion).where(
        ExternalObjectVersion.system_id == system.id,
        ExternalObjectVersion.external_id == asset.external_id,
        ExternalObjectVersion.source_fingerprint == version_fingerprint,
    ))
    if not version:
        db.add(ExternalObjectVersion(
            system_id=system.id,
            external_id=asset.external_id,
            source_fingerprint=version_fingerprint,
            document_id=doc.id,
            sha256=doc.sha256,
            metadata_json={**(asset.metadata or {}), "data_quality": quality, "ingest_event_id": event.id},
        ))
    event.document_id = doc.id
    event.payload_sha256 = digest
    event.status = "accepted"
    event.accepted_at = _now()
    event.quality_json = quality
    event.error_json = {}
    db.commit()
    return doc, imported


def _system_quality(db: Session, system: ExternalSystem, *, run_failed: int = 0) -> dict:
    objects = db.scalars(select(ExternalObject).where(ExternalObject.system_id == system.id)).all()
    outstanding_quarantine = int(db.scalar(select(func.count()).select_from(IntegrationIngestEvent).where(
        IntegrationIngestEvent.system_id == system.id,
        IntegrationIngestEvent.status == "quarantined",
    )) or 0)
    quality = aggregate_system_quality(objects, expected_freshness_minutes=system.expected_freshness_minutes, quarantined=outstanding_quarantine, failed=run_failed)
    system.last_quality_json = quality
    system.last_quality_at = _now()
    publish_integration_quality(system.code, quality)
    return quality


def _sync_external_system_locked(db: Session, system: ExternalSystem, groups: list[str], page_limit: int = 100, max_pages: int = 20) -> dict:
    run = IntegrationRun(system_id=system.id, status="running", started_at=_now())
    db.add(run); db.commit(); db.refresh(run)
    connector = build_connector(system.connector_type, system.config_json or {}, system.secret_config_json or {})
    contract = contract_for(system)
    cursor_row = db.scalar(select(SyncCursor).where(SyncCursor.system_id == system.id))
    saved_checkpoint = cursor_row.cursor if cursor_row else None
    page_cursor = saved_checkpoint
    new_checkpoint = saved_checkpoint
    imported = skipped = failed = quarantined = 0
    errors: list[dict] = []
    staging_root = get_settings().storage_dir / "integration-staging" / run.id
    try:
        for _ in range(max_pages):
            page = connector.list_assets(page_cursor, page_limit)
            for asset in page.assets:
                existing = db.scalar(select(ExternalObject).where(
                    ExternalObject.system_id == system.id,
                    ExternalObject.external_id == asset.external_id,
                ))
                stable_source_identity = bool(asset.checksum or asset.modified_at or asset.revision)
                event = None
                key = None
                if stable_source_identity:
                    key = idempotency_key(system, asset)
                    event = db.scalar(select(IntegrationIngestEvent).where(
                        IntegrationIngestEvent.system_id == system.id,
                        IntegrationIngestEvent.idempotency_key == key,
                    ))
                    if event and event.status in {"accepted", "replayed"}:
                        skipped += 1
                        if existing:
                            existing.last_seen_at = _now(); db.commit()
                        continue
                    if event and event.status == "quarantined":
                        # Explicit operator replay is required. This prevents endless source polling
                        # from repeatedly ingesting the same contract violation.
                        skipped += 1
                        continue
                    if not event:
                        event = IntegrationIngestEvent(
                            system_id=system.id,
                            integration_run_id=run.id,
                            idempotency_key=key,
                            external_id=str(asset.external_id),
                            object_type=asset.kind,
                            contract_version=contract["version"],
                            source_revision=asset.revision,
                            source_fingerprint=_source_fingerprint(asset),
                            status="received",
                            validation_json={"asset_snapshot": asset_snapshot(asset), "contract": contract},
                        )
                        db.add(event); db.commit(); db.refresh(event)
                    else:
                        event.integration_run_id = run.id
                        event.attempt_count = int(event.attempt_count or 0) + 1
                        event.last_attempt_at = _now()
                        event.error_json = {}
                        db.commit()
                try:
                    staged = connector.fetch_asset(asset, staging_root / hashlib.sha256(str(asset.external_id).encode()).hexdigest()[:16])
                    digest = _sha256(staged)
                    # A weak source identity cannot safely support pre-download deduplication. The
                    # immutable payload digest becomes the idempotency identity instead.
                    if not stable_source_identity:
                        key = idempotency_key(system, asset, payload_sha256=digest)
                        event = db.scalar(select(IntegrationIngestEvent).where(
                            IntegrationIngestEvent.system_id == system.id,
                            IntegrationIngestEvent.idempotency_key == key,
                        ))
                        if event and event.status in {"accepted", "replayed"}:
                            skipped += 1
                            if existing:
                                existing.last_seen_at = _now(); db.commit()
                            continue
                        if event and event.status == "quarantined":
                            skipped += 1
                            continue
                        if not event:
                            event = IntegrationIngestEvent(
                                system_id=system.id,
                                integration_run_id=run.id,
                                idempotency_key=key,
                                external_id=str(asset.external_id),
                                object_type=asset.kind,
                                contract_version=contract["version"],
                                source_revision=asset.revision,
                                source_fingerprint=digest,
                                status="received",
                                validation_json={"asset_snapshot": asset_snapshot(asset), "contract": contract},
                            )
                            db.add(event); db.commit(); db.refresh(event)
                        else:
                            event.integration_run_id = run.id
                            event.attempt_count = int(event.attempt_count or 0) + 1
                            event.last_attempt_at = _now()
                            event.error_json = {}
                            db.commit()

                    validation = validate_asset_contract(asset, contract)
                    quality = calculate_data_quality(asset, contract, validation, payload_sha256=digest)
                    source_dt = parse_source_timestamp(asset.modified_at) if validation.get("source_modified_at") else None
                    assert event is not None
                    event.payload_sha256 = digest
                    event.source_modified_at = source_dt
                    event.source_fingerprint = _source_fingerprint(asset, digest)
                    event.validation_json = {**validation, "asset_snapshot": asset_snapshot(asset), "contract": contract}
                    event.quality_json = quality
                    event.last_attempt_at = _now()
                    if not validation["valid"]:
                        target = _quarantine_path(system, event, digest, asset.name)
                        _copy_once(staged, target)
                        event.quarantine_path = str(target)
                        event.status = "quarantined"
                        event.error_json = {"reason": "CONTRACT_VALIDATION_FAILED", "errors": validation["errors"]}
                        quarantined += 1
                        db.commit()
                        continue
                    doc, was_imported = _accept_staged_asset(
                        db, system, asset, staged, digest, existing, event, quality, source_dt,
                        _source_fingerprint(asset, digest),
                    )
                    if was_imported:
                        imported += 1
                    else:
                        skipped += 1
                except Exception as exc:
                    failed += 1
                    if event is not None:
                        event.status = "failed"
                        event.error_json = {"reason": "INGEST_EXCEPTION", "error": str(exc)[:2000]}
                        event.last_attempt_at = _now()
                        db.commit()
                    errors.append({"external_id": str(asset.external_id), "error": str(exc)[:1000]})
            if page.checkpoint is not None:
                new_checkpoint = page.checkpoint
            page_cursor = page.next_cursor
            if not page_cursor:
                break
        if not cursor_row:
            cursor_row = SyncCursor(system_id=system.id, cursor=new_checkpoint)
            db.add(cursor_row)
        else:
            cursor_row.cursor = new_checkpoint
        cursor_row.updated_at = _now()
        system.last_sync_at = _now()
        system.last_sync_status = "ok" if failed == 0 and quarantined == 0 else "partial"
        run.status = system.last_sync_status
        run.imported_count = imported
        run.skipped_count = skipped
        run.failed_count = failed
        run.quarantined_count = quarantined
        run.error_json = {"errors": errors[:100]}
        run.quality_json = _system_quality(db, system, run_failed=failed)
    except Exception as exc:
        system.last_sync_status = "failed"
        run.status = "failed"
        run.failed_count = failed + 1
        run.error_json = {"fatal": str(exc)[:2000], "errors": errors[:100]}
        run.quality_json = _system_quality(db, system, run_failed=failed + 1)
    finally:
        run.finished_at = _now()
        db.commit()
        shutil.rmtree(staging_root, ignore_errors=True)
    return {
        "run_id": run.id,
        "status": run.status,
        "imported": run.imported_count,
        "skipped": run.skipped_count,
        "quarantined": run.quarantined_count,
        "failed": run.failed_count,
        "data_quality": run.quality_json,
        "errors": run.error_json,
    }


def sync_external_system(db: Session, system: ExternalSystem, groups: list[str], page_limit: int = 100, max_pages: int = 20) -> dict:
    with integration_sync_lock(db, system.id):
        return _sync_external_system_locked(db, system, groups, page_limit, max_pages)

def replay_quarantined_event(db: Session, system: ExternalSystem, event: IntegrationIngestEvent) -> dict:
    """Safely replay an immutable quarantined payload after an operator fixes the contract/mapping."""
    if event.system_id != system.id:
        raise ValueError("Event does not belong to integration")
    if event.status not in {"quarantined", "failed"}:
        return {"event_id": event.id, "status": event.status, "replayed": False, "reason": "EVENT_NOT_REPLAYABLE"}
    snapshot = (event.validation_json or {}).get("asset_snapshot") or {}
    if not event.quarantine_path or not Path(event.quarantine_path).is_file():
        return {"event_id": event.id, "status": event.status, "replayed": False, "reason": "SOURCE_RESYNC_REQUIRED"}

    run = IntegrationRun(system_id=system.id, status="running", started_at=_now())
    db.add(run); db.commit(); db.refresh(run)
    event.integration_run_id = run.id
    event.attempt_count = int(event.attempt_count or 0) + 1
    event.last_attempt_at = _now()
    asset = asset_from_snapshot(snapshot)
    contract = contract_for(system)
    staged = Path(event.quarantine_path)
    digest = _sha256(staged)
    validation = validate_asset_contract(asset, contract)
    quality = calculate_data_quality(asset, contract, validation, payload_sha256=digest)
    event.validation_json = {**validation, "asset_snapshot": snapshot, "contract": contract}
    event.quality_json = quality
    event.payload_sha256 = digest
    if not validation["valid"]:
        event.status = "quarantined"
        event.error_json = {"reason": "CONTRACT_VALIDATION_FAILED", "errors": validation["errors"]}
        run.status = "partial"
        run.quarantined_count = 1
        run.quality_json = _system_quality(db, system)
        run.finished_at = _now(); db.commit()
        return {"event_id": event.id, "status": event.status, "replayed": False, "validation": validation, "data_quality": quality}

    existing = db.scalar(select(ExternalObject).where(
        ExternalObject.system_id == system.id,
        ExternalObject.external_id == event.external_id,
    ))
    source_dt = parse_source_timestamp(asset.modified_at) if validation.get("source_modified_at") else None
    doc, imported = _accept_staged_asset(
        db, system, asset, staged, digest, existing, event, quality, source_dt,
        _source_fingerprint(asset, digest),
    )
    event.status = "replayed"
    event.accepted_at = _now()
    run.status = "ok"
    run.imported_count = 1 if imported else 0
    run.skipped_count = 0 if imported else 1
    run.replayed_count = 1
    run.quality_json = _system_quality(db, system)
    run.finished_at = _now()
    system.last_sync_at = _now()
    system.last_sync_status = "ok"
    db.commit()
    return {
        "event_id": event.id,
        "run_id": run.id,
        "status": event.status,
        "replayed": True,
        "document_id": doc.id,
        "imported": imported,
        "data_quality": quality,
    }
