from __future__ import annotations

import hashlib
import json
import socket
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

from prometheus_client import Gauge
from sqlalchemy import delete, func, select, insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.adapters.registry import get_graph_projection_port, get_object_storage_port, get_search_port
from app.core.config import get_settings
from app.db.models import (
    Document,
    DocumentSearchChunk,
    ProjectionDeliveryReceipt,
    ProjectionOutboxEvent,
)

ACTIVE_STATUSES = ("pending", "retry")
TERMINAL_STATUSES = ("succeeded", "dead_letter", "superseded", "cancelled")
TARGET_SEARCH = "search"
TARGET_GRAPH = "graph"
TARGET_OBJECT_STORAGE = "object_storage"
TARGET_READ_MODEL = "read_model"

PROJECTION_BACKLOG = Gauge("mgc_projection_outbox_backlog", "Pending/retry/processing projection events")
PROJECTION_DLQ = Gauge("mgc_projection_outbox_dead_letter", "Projection events in dead-letter state")
PROJECTION_LAG_SECONDS = Gauge("mgc_projection_outbox_oldest_age_seconds", "Age of oldest unfinished projection event in seconds")


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _canonical(value) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")


def persist_document_chunks(db: Session, document_id: str, chunks: list[str]) -> int:
    """Replace the PostgreSQL-authoritative projection source inside the caller transaction."""
    db.execute(delete(DocumentSearchChunk).where(DocumentSearchChunk.document_id == document_id))
    rows = []
    for index, text in enumerate(chunks):
        clean = str(text or "").strip()
        if not clean:
            continue
        rows.append({
            "document_id": document_id,
            "chunk_index": index,
            "text": clean,
            "content_sha256": hashlib.sha256(clean.encode("utf-8")).hexdigest(),
            "metadata_json": {},
        })
    batch_size = max(1, min(int(getattr(get_settings(), "bulk_ingest_batch_size", 500)), 5000))
    for start in range(0, len(rows), batch_size):
        db.execute(insert(DocumentSearchChunk), rows[start:start + batch_size])
    db.flush()
    return len(rows)


def document_projection_version(db: Session, doc: Document) -> str:
    chunk_hashes = db.scalars(
        select(DocumentSearchChunk.content_sha256)
        .where(DocumentSearchChunk.document_id == doc.id)
        .order_by(DocumentSearchChunk.chunk_index)
    ).all()
    state = {
        "document_id": doc.id,
        "sha256": doc.sha256,
        "part_number": doc.part_number,
        "revision": doc.revision,
        "doc_type": doc.doc_type,
        "project_code": doc.project_code,
        "manufacturing_area": doc.manufacturing_area,
        "acl_groups": sorted(doc.acl_groups or []),
        "metadata": {k: v for k, v in (doc.extracted_metadata or {}).items() if k not in {"object_store", "projection_status"}},
        "chunks": list(chunk_hashes),
    }
    return hashlib.sha256(_canonical(state)).hexdigest()


def _event_key(target: str, event_type: str, aggregate_type: str, aggregate_id: str, source_version: str, generation: str = "") -> str:
    raw = f"{target}|{event_type}|{aggregate_type}|{aggregate_id}|{source_version}|{generation}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def enqueue_event(
    db: Session,
    *,
    target: str,
    event_type: str,
    aggregate_type: str,
    aggregate_id: str,
    source_version: str,
    payload: dict | None = None,
    correlation_id: str | None = None,
    generation: str = "",
) -> ProjectionOutboxEvent:
    cfg = get_settings()
    key = _event_key(target, event_type, aggregate_type, aggregate_id, source_version, generation)
    existing = db.scalar(select(ProjectionOutboxEvent).where(ProjectionOutboxEvent.idempotency_key == key))
    if existing:
        return existing
    row = ProjectionOutboxEvent(
        idempotency_key=key,
        target=target,
        event_type=event_type,
        aggregate_type=aggregate_type,
        aggregate_id=aggregate_id,
        source_version=source_version,
        payload_json=payload or {},
        status="pending",
        max_attempts=max(int(cfg.projection_max_attempts), 1),
        available_at=utcnow(),
        correlation_id=correlation_id,
    )
    try:
        with db.begin_nested():
            db.add(row)
            db.flush()
    except IntegrityError:
        # Concurrent enqueue of the same logical projection is a benign dedupe race.
        # The savepoint prevents rolling back authoritative engineering changes in the outer UoW.
        existing = db.scalar(select(ProjectionOutboxEvent).where(ProjectionOutboxEvent.idempotency_key == key))
        if existing:
            return existing
        raise
    return row


def enqueue_document_projections(db: Session, doc: Document, *, generation: str = "", correlation_id: str | None = None) -> list[ProjectionOutboxEvent]:
    cfg = get_settings()
    if not cfg.projection_outbox_enabled:
        return []
    version = document_projection_version(db, doc)
    events: list[ProjectionOutboxEvent] = []
    common = dict(aggregate_type="document", aggregate_id=doc.id, source_version=version, correlation_id=correlation_id, generation=generation)
    if cfg.semantic_search_enabled:
        events.append(enqueue_event(db, target=TARGET_SEARCH, event_type="document_index_refresh", payload={"document_id": doc.id}, **common))
    if cfg.runtime_object_store_enabled:
        events.append(enqueue_event(db, target=TARGET_OBJECT_STORAGE, event_type="document_evidence_mirror", payload={"document_id": doc.id}, **common))
    if cfg.runtime_graph_enabled and doc.part_number:
        events.append(enqueue_event(db, target=TARGET_GRAPH, event_type="part_graph_refresh", payload={"document_id": doc.id, "part_number": doc.part_number}, **common))
    if getattr(cfg, "read_model_enabled", True):
        events.append(enqueue_event(
            db, target=TARGET_READ_MODEL, event_type="read_model_invalidate", aggregate_type="read_model",
            aggregate_id=f"{doc.project_code or '*'}:{doc.manufacturing_area or '*'}", source_version=version,
            payload={"project_code": doc.project_code, "manufacturing_area": doc.manufacturing_area, "cache_prefix": "mgc:v6310:"},
            correlation_id=correlation_id, generation=generation,
        ))
    return events


def _document_payload(doc: Document) -> dict:
    return {
        "id": doc.id,
        "filename": doc.filename,
        "part_number": doc.part_number,
        "revision": doc.revision,
        "doc_type": doc.doc_type,
        "project_code": doc.project_code,
        "manufacturing_area": doc.manufacturing_area,
        "acl_groups": doc.acl_groups,
        "metadata": doc.extracted_metadata or {},
    }


def _claim_batch(db: Session, *, worker_id: str, limit: int) -> list[str]:
    cfg = get_settings()
    now = utcnow()
    stale_before = now - timedelta(seconds=max(int(cfg.projection_lock_timeout_seconds), 30))
    # Recover work abandoned by a dead worker. Delivery remains safe because consumers are idempotent.
    stale = db.scalars(select(ProjectionOutboxEvent).where(
        ProjectionOutboxEvent.status == "processing",
        ProjectionOutboxEvent.locked_at < stale_before,
    )).all()
    for row in stale:
        row.locked_at = None
        row.locked_by = None
        if int(row.attempt_count or 0) >= int(row.max_attempts or 1):
            row.status = "dead_letter"
            row.completed_at = now
            row.last_error = "worker lease expired after retry budget was exhausted"
        else:
            row.status = "retry"
            row.available_at = now
            row.last_error = "worker lease expired; event safely requeued"

    stmt = (
        select(ProjectionOutboxEvent)
        .where(ProjectionOutboxEvent.status.in_(ACTIVE_STATUSES), ProjectionOutboxEvent.available_at <= now, ProjectionOutboxEvent.attempt_count < ProjectionOutboxEvent.max_attempts)
        .order_by(ProjectionOutboxEvent.created_at, ProjectionOutboxEvent.id)
        .limit(max(int(limit), 1))
    )
    if db.bind is not None and db.bind.dialect.name == "postgresql":
        stmt = stmt.with_for_update(skip_locked=True)
    rows = db.scalars(stmt).all()
    for row in rows:
        row.status = "processing"
        row.attempt_count = int(row.attempt_count or 0) + 1
        row.locked_at = now
        row.locked_by = worker_id
    db.commit()
    return [row.id for row in rows]


def _current_version_matches(db: Session, event: ProjectionOutboxEvent, doc: Document) -> bool:
    # Rebuild generations still target the current authoritative source_version stored in the event.
    return document_projection_version(db, doc) == event.source_version


def _deliver(db: Session, event: ProjectionOutboxEvent) -> dict:
    receipt = db.scalar(select(ProjectionDeliveryReceipt).where(ProjectionDeliveryReceipt.idempotency_key == event.idempotency_key))
    if receipt:
        return {"deduplicated": True, **(receipt.result_json or {})}

    if event.target == TARGET_READ_MODEL and event.aggregate_type == "read_model":
        from app.services.read_models import invalidate_read_models, redis_cache_delete_prefix
        payload = event.payload_json or {}
        invalidated = invalidate_read_models(db, project_code=payload.get("project_code"), manufacturing_area=payload.get("manufacturing_area"))
        deleted = redis_cache_delete_prefix(payload.get("cache_prefix") or "mgc:v6310:")
        return {"invalidated_read_models": invalidated, "deleted_cache_keys": deleted, "rebuildable": True}

    if event.aggregate_type != "document":
        raise RuntimeError(f"unsupported aggregate_type: {event.aggregate_type}")
    doc = db.get(Document, event.aggregate_id)
    if not doc:
        return {"superseded": True, "reason": "aggregate_deleted"}
    if not _current_version_matches(db, event, doc):
        return {"superseded": True, "reason": "newer_authoritative_version"}

    if event.target == TARGET_SEARCH:
        chunks = db.scalars(
            select(DocumentSearchChunk.text)
            .where(DocumentSearchChunk.document_id == doc.id)
            .order_by(DocumentSearchChunk.chunk_index)
        ).all()
        port = get_search_port()
        # Replacement semantics make retry after a worker crash idempotent.
        port.delete_document(doc.id)
        indexed = port.index_chunks(_document_payload(doc), list(chunks))
        return {"adapter": port.mode, "indexed_chunks": indexed, "authoritative_chunks": len(chunks)}

    if event.target == TARGET_GRAPH:
        if not doc.part_number:
            return {"superseded": True, "reason": "part_number_removed"}
        port = get_graph_projection_port()
        return {"adapter": port.mode, **(port.sync_part(db, doc.part_number) or {})}

    if event.target == TARGET_OBJECT_STORAGE:
        port = get_object_storage_port()
        result = port.mirror_file(Path(doc.stored_path), f"documents/{doc.id}/{doc.filename}")
        if result:
            doc.extracted_metadata = {**(doc.extracted_metadata or {}), "object_store": result}
        return {"adapter": port.mode, "mirror": result}

    raise RuntimeError(f"unsupported projection target: {event.target}")


def _finish_success(db: Session, event: ProjectionOutboxEvent, result: dict) -> None:
    now = utcnow()
    if result.get("superseded"):
        event.status = "superseded"
    else:
        receipt = db.scalar(select(ProjectionDeliveryReceipt).where(ProjectionDeliveryReceipt.idempotency_key == event.idempotency_key))
        if not receipt:
            db.add(ProjectionDeliveryReceipt(
                event_id=event.id,
                idempotency_key=event.idempotency_key,
                target=event.target,
                result_json=result,
            ))
        event.status = "succeeded"
    event.result_json = result
    event.last_error = None
    event.completed_at = now
    event.locked_at = None
    event.locked_by = None
    db.commit()


def _finish_failure(db: Session, event: ProjectionOutboxEvent, exc: Exception) -> None:
    cfg = get_settings()
    event.last_error = f"{type(exc).__name__}: {exc}"[:4000]
    event.locked_at = None
    event.locked_by = None
    if event.attempt_count >= max(int(event.max_attempts or cfg.projection_max_attempts), 1):
        event.status = "dead_letter"
        event.completed_at = utcnow()
    else:
        delay = min(
            max(int(cfg.projection_retry_base_seconds), 1) * (2 ** max(event.attempt_count - 1, 0)),
            max(int(cfg.projection_retry_max_seconds), 1),
        )
        event.status = "retry"
        event.available_at = utcnow() + timedelta(seconds=delay)
    db.commit()


def process_projection_event(db: Session, event_id: str) -> dict:
    event = db.get(ProjectionOutboxEvent, event_id)
    if not event:
        return {"event_id": event_id, "status": "missing"}
    if event.status not in {"processing", "pending", "retry"}:
        return {"event_id": event.id, "status": event.status}
    try:
        result = _deliver(db, event)
        _finish_success(db, event, result)
        return {"event_id": event.id, "status": event.status, "result": result}
    except Exception as exc:
        _finish_failure(db, event, exc)
        return {"event_id": event.id, "status": event.status, "error": event.last_error}


def drain_projection_outbox(db_factory, *, limit: int | None = None, worker_id: str | None = None) -> dict:
    cfg = get_settings()
    if not cfg.projection_worker_enabled:
        return {"status": "disabled", "claimed": 0, "processed": 0}
    worker = worker_id or f"{socket.gethostname()}:{uuid.uuid4().hex[:8]}"
    batch = min(max(int(limit or cfg.projection_batch_size), 1), 500)
    with db_factory() as claim_db:
        ids = _claim_batch(claim_db, worker_id=worker, limit=batch)
    results = []
    for event_id in ids:
        with db_factory() as event_db:
            results.append(process_projection_event(event_db, event_id))
    return {
        "status": "ok",
        "worker_id": worker,
        "claimed": len(ids),
        "processed": len(results),
        "succeeded": sum(1 for x in results if x.get("status") == "succeeded"),
        "dead_letter": sum(1 for x in results if x.get("status") == "dead_letter"),
        "retry": sum(1 for x in results if x.get("status") == "retry"),
        "superseded": sum(1 for x in results if x.get("status") == "superseded"),
        "results": results,
    }


def projection_health(db: Session) -> dict:
    now = utcnow()
    counts = {status: int(db.scalar(select(func.count()).select_from(ProjectionOutboxEvent).where(ProjectionOutboxEvent.status == status)) or 0)
              for status in ("pending", "retry", "processing", "succeeded", "dead_letter", "superseded")}
    oldest = db.scalar(select(func.min(ProjectionOutboxEvent.created_at)).where(ProjectionOutboxEvent.status.in_(("pending", "retry", "processing"))))
    if oldest and oldest.tzinfo is None:
        oldest = oldest.replace(tzinfo=timezone.utc)
    lag = max(int((now - oldest).total_seconds()), 0) if oldest else 0
    by_target = {}
    rows = db.execute(select(ProjectionOutboxEvent.target, ProjectionOutboxEvent.status, func.count()).group_by(ProjectionOutboxEvent.target, ProjectionOutboxEvent.status)).all()
    for target, status, count in rows:
        by_target.setdefault(target, {})[status] = int(count)
    cfg = get_settings()
    PROJECTION_BACKLOG.set(counts["pending"] + counts["retry"] + counts["processing"])
    PROJECTION_DLQ.set(counts["dead_letter"])
    PROJECTION_LAG_SECONDS.set(lag)
    status = "healthy"
    if counts["dead_letter"]:
        status = "degraded"
    elif lag > int(cfg.projection_lag_warning_seconds):
        status = "lagging"
    return {
        "status": status,
        "backlog": counts["pending"] + counts["retry"] + counts["processing"],
        "oldest_event_age_seconds": lag,
        "dead_letter": counts["dead_letter"],
        "counts": counts,
        "by_target": by_target,
        "policy": {
            "postgresql_authoritative": True,
            "delivery": "at_least_once_with_idempotent_consumers",
            "logical_processing": "effectively_once_per_idempotency_key",
            "optional_projection_failure_blocks_core": False,
        },
    }


def list_outbox(db: Session, *, status: str | None = None, target: str | None = None, limit: int = 100) -> list[dict]:
    stmt = select(ProjectionOutboxEvent)
    if status:
        stmt = stmt.where(ProjectionOutboxEvent.status == status)
    if target:
        stmt = stmt.where(ProjectionOutboxEvent.target == target)
    rows = db.scalars(stmt.order_by(ProjectionOutboxEvent.created_at.desc()).limit(min(max(limit, 1), 500))).all()
    return [{
        "id": x.id, "target": x.target, "event_type": x.event_type, "aggregate_type": x.aggregate_type,
        "aggregate_id": x.aggregate_id, "source_version": x.source_version, "status": x.status,
        "attempt_count": x.attempt_count, "max_attempts": x.max_attempts, "available_at": x.available_at,
        "locked_at": x.locked_at, "locked_by": x.locked_by, "last_error": x.last_error,
        "created_at": x.created_at, "completed_at": x.completed_at,
    } for x in rows]


def replay_dead_letter(db: Session, event_id: str) -> ProjectionOutboxEvent | None:
    row = db.get(ProjectionOutboxEvent, event_id)
    if not row or row.status != "dead_letter":
        return None
    row.status = "retry"
    row.available_at = utcnow()
    row.locked_at = None
    row.locked_by = None
    row.last_error = None
    row.completed_at = None
    # Preserve attempt_count for audit, but grant a fresh controlled retry budget.
    row.max_attempts = int(row.attempt_count or 0) + max(int(get_settings().projection_max_attempts), 1)
    db.commit(); db.refresh(row)
    return row


def ensure_document_projection_source(db: Session, doc: Document) -> dict:
    """Backfill v6.3.1-and-older documents before a projection rebuild.

    The local evidence file is authoritative. If a rich parser is unavailable in the current
    runtime, metadata evidence is persisted instead of pretending full extraction succeeded.
    """
    existing = int(db.scalar(select(func.count()).select_from(DocumentSearchChunk).where(DocumentSearchChunk.document_id == doc.id)) or 0)
    if existing:
        return {"backfilled": False, "chunks": existing, "mode": "existing"}
    from app.services.chunking import chunk_text
    text = ""
    mode = "metadata_fallback"
    path = Path(doc.stored_path)
    if path.exists() and doc.extension not in {".step", ".stp", ".stl", ".dxf", ".catpart", ".catproduct", ".prt", ".jt", ".sldprt", ".sldasm", ".x_t", ".x_b"}:
        try:
            from app.services.document_parser import parse_document
            text, _ = parse_document(path)
            mode = "evidence_reparse"
        except Exception:
            text = ""
    if not text.strip():
        text = "\n".join([
            f"File: {doc.filename}",
            f"Part: {doc.part_number or '-'}",
            f"Revision: {doc.revision or '-'}",
            f"Type: {doc.doc_type or '-'}",
            json.dumps({k: v for k, v in (doc.extracted_metadata or {}).items() if k != "object_store"}, ensure_ascii=False, sort_keys=True, default=str),
        ])
    chunks = chunk_text(text)
    count = persist_document_chunks(db, doc.id, chunks)
    doc.indexed_chunks = count
    db.flush()
    return {"backfilled": True, "chunks": count, "mode": mode}


def enqueue_rebuild(db: Session, *, target: str | None = None, project_code: str | None = None, manufacturing_area: str | None = None) -> dict:
    allowed_targets = {TARGET_SEARCH, TARGET_GRAPH, TARGET_OBJECT_STORAGE}
    if target and target not in allowed_targets:
        raise ValueError("Unsupported projection target")
    generation = f"rebuild-{uuid.uuid4()}"
    stmt = select(Document)
    if project_code:
        stmt = stmt.where(Document.project_code == project_code)
    if manufacturing_area:
        stmt = stmt.where(Document.manufacturing_area == manufacturing_area)
    docs = db.scalars(stmt.order_by(Document.id)).all()
    created = 0
    backfilled = 0
    cfg = get_settings()
    for doc in docs:
        source = ensure_document_projection_source(db, doc)
        if source["backfilled"]:
            backfilled += 1
        version = document_projection_version(db, doc)
        common = dict(aggregate_type="document", aggregate_id=doc.id, source_version=version, correlation_id=generation, generation=generation)
        if (not target or target == TARGET_SEARCH) and cfg.semantic_search_enabled:
            enqueue_event(db, target=TARGET_SEARCH, event_type="document_index_refresh", payload={"document_id": doc.id, "rebuild": True}, **common); created += 1
        if (not target or target == TARGET_OBJECT_STORAGE) and cfg.runtime_object_store_enabled:
            enqueue_event(db, target=TARGET_OBJECT_STORAGE, event_type="document_evidence_mirror", payload={"document_id": doc.id, "rebuild": True}, **common); created += 1
        if (not target or target == TARGET_GRAPH) and cfg.runtime_graph_enabled and doc.part_number:
            enqueue_event(db, target=TARGET_GRAPH, event_type="part_graph_refresh", payload={"document_id": doc.id, "part_number": doc.part_number, "rebuild": True}, **common); created += 1
    db.commit()
    return {"generation": generation, "documents": len(docs), "events_created": created, "legacy_documents_backfilled": backfilled, "target": target or "active"}
