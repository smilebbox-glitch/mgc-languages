from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any, Callable

from prometheus_client import Counter, Gauge
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.models import (
    EngineeringReadModel, ManufacturingLayout, ManufacturingLine, ProcessOperation,
    ProcessStation, ProjectionOutboxEvent, WorkInstruction,
)

TARGET_READ_MODEL = "read_model"
READ_MODEL_HITS = Counter("mgc_read_model_hits_total", "Persistent read model hits", ["model_type"])
READ_MODEL_REBUILDS = Counter("mgc_read_model_rebuilds_total", "Persistent read model rebuilds", ["model_type"])
CACHE_HITS = Counter("mgc_acceleration_cache_hits_total", "Optional Redis acceleration cache hits", ["surface"])
CACHE_MISSES = Counter("mgc_acceleration_cache_misses_total", "Optional Redis acceleration cache misses", ["surface"])
READ_MODEL_STALE = Gauge("mgc_read_model_stale", "Number of stale read models")


def utcnow():
    return datetime.now(timezone.utc)


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")


def payload_sha(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def acl_fingerprint(visible_document_ids: set[str], groups: list[str] | None = None) -> str:
    material = {"documents": sorted(str(x) for x in visible_document_ids), "groups": sorted(set(groups or []))}
    return payload_sha(material)[:24]


def redis_cache_get(key: str, *, surface: str) -> dict | None:
    cfg = get_settings()
    if not cfg.read_model_cache_enabled:
        return None
    try:
        import redis
        client = redis.Redis.from_url(cfg.redis_url, socket_connect_timeout=0.15, socket_timeout=0.15, decode_responses=True)
        raw = client.get(key)
        if not raw:
            CACHE_MISSES.labels(surface).inc(); return None
        CACHE_HITS.labels(surface).inc()
        return json.loads(raw)
    except Exception:
        CACHE_MISSES.labels(surface).inc()
        return None


def redis_cache_set(key: str, value: dict, *, ttl: int, surface: str) -> None:
    cfg = get_settings()
    if not cfg.read_model_cache_enabled:
        return
    try:
        import redis
        client = redis.Redis.from_url(cfg.redis_url, socket_connect_timeout=0.15, socket_timeout=0.15, decode_responses=True)
        client.setex(key, max(1, int(ttl)), json.dumps(value, ensure_ascii=False, separators=(",", ":"), default=str))
    except Exception:
        return


def redis_cache_delete_prefix(prefix: str) -> int:
    cfg = get_settings()
    if not cfg.read_model_cache_enabled:
        return 0
    deleted = 0
    try:
        import redis
        client = redis.Redis.from_url(cfg.redis_url, socket_connect_timeout=0.2, socket_timeout=0.2, decode_responses=True)
        batch = []
        for key in client.scan_iter(match=f"{prefix}*", count=200):
            batch.append(key)
            if len(batch) >= 200:
                deleted += int(client.delete(*batch) or 0); batch = []
        if batch:
            deleted += int(client.delete(*batch) or 0)
    except Exception:
        pass
    return deleted


def pending_read_model_invalidation(db: Session) -> bool:
    if not get_settings().read_model_pending_invalidation_bypass:
        return False
    return bool(db.scalar(select(func.count()).select_from(ProjectionOutboxEvent).where(
        ProjectionOutboxEvent.target == TARGET_READ_MODEL,
        ProjectionOutboxEvent.status.in_(("pending", "retry", "processing")),
    )) or 0)


def wi_coverage_payload(db: Session, project_code: str, manufacturing_area: str) -> dict:
    lines = int(db.scalar(select(func.count()).select_from(ManufacturingLine).where(
        ManufacturingLine.project_code == project_code, ManufacturingLine.manufacturing_area == manufacturing_area)) or 0)
    line_ids = select(ManufacturingLine.id).where(ManufacturingLine.project_code == project_code, ManufacturingLine.manufacturing_area == manufacturing_area)
    stations = int(db.scalar(select(func.count()).select_from(ProcessStation).where(ProcessStation.line_id.in_(line_ids))) or 0)
    station_ids = select(ProcessStation.id).where(ProcessStation.line_id.in_(line_ids))
    operations = int(db.scalar(select(func.count()).select_from(ProcessOperation).where(ProcessOperation.station_id.in_(station_ids))) or 0)
    wis = int(db.scalar(select(func.count()).select_from(WorkInstruction).where(WorkInstruction.project_code == project_code, WorkInstruction.manufacturing_area == manufacturing_area)) or 0)
    approved = int(db.scalar(select(func.count()).select_from(WorkInstruction).where(WorkInstruction.project_code == project_code, WorkInstruction.manufacturing_area == manufacturing_area, WorkInstruction.status == "approved")) or 0)
    foreign = int(db.scalar(select(func.count()).select_from(WorkInstruction).where(WorkInstruction.project_code == project_code, WorkInstruction.manufacturing_area == manufacturing_area, WorkInstruction.source_language.notin_(("ru", "auto")))) or 0)
    layouts = int(db.scalar(select(func.count()).select_from(ManufacturingLayout).where(ManufacturingLayout.project_code == project_code, ManufacturingLayout.manufacturing_area == manufacturing_area)) or 0)
    stations_any = int(db.scalar(select(func.count(func.distinct(WorkInstruction.station_id))).where(WorkInstruction.project_code == project_code, WorkInstruction.manufacturing_area == manufacturing_area, WorkInstruction.station_id.is_not(None))) or 0)
    stations_approved = int(db.scalar(select(func.count(func.distinct(WorkInstruction.station_id))).where(WorkInstruction.project_code == project_code, WorkInstruction.manufacturing_area == manufacturing_area, WorkInstruction.station_id.is_not(None), WorkInstruction.status == "approved")) or 0)
    return {
        "schema": "mgc-wi-coverage-read-model-v1",
        "project_code": project_code,
        "manufacturing_area": manufacturing_area,
        "counts": {"lines": lines, "stations": stations, "operations": operations, "instructions": wis, "approved_instructions": approved, "foreign_instructions": foreign, "layouts": layouts},
        "coverage": {
            "stations_with_instruction_pct": round(100 * stations_any / stations, 1) if stations else 0.0,
            "stations_with_approved_instruction_pct": round(100 * stations_approved / stations, 1) if stations else 0.0,
        },
        "authoritative": False,
        "rebuildable": True,
    }


def get_wi_coverage_read_model(db: Session, project_code: str, manufacturing_area: str) -> dict:
    key = f"wi_coverage:{project_code}:{manufacturing_area}"
    row = db.scalar(select(EngineeringReadModel).where(EngineeringReadModel.model_key == key))
    pending = pending_read_model_invalidation(db)
    if row and row.status == "fresh" and not pending:
        READ_MODEL_HITS.labels("wi_coverage").inc()
        return {**(row.payload_json or {}), "etag": row.payload_sha256, "generated_at": row.generated_at.isoformat() if row.generated_at else None, "cache_state": "read_model_hit"}
    payload = wi_coverage_payload(db, project_code, manufacturing_area)
    sha = payload_sha(payload)
    if row is None:
        row = EngineeringReadModel(model_key=key, model_type="wi_coverage", project_code=project_code, manufacturing_area=manufacturing_area)
        db.add(row)
    row.status = "fresh"
    row.payload_json = payload
    row.payload_sha256 = sha
    row.source_version = sha
    row.generated_at = utcnow()
    row.invalidated_at = None
    db.flush()
    db.commit(); db.refresh(row)
    READ_MODEL_REBUILDS.labels("wi_coverage").inc()
    return {**payload, "etag": sha, "generated_at": row.generated_at.isoformat(), "cache_state": "rebuilt"}


def invalidate_read_models(db: Session, *, project_code: str | None = None, manufacturing_area: str | None = None) -> int:
    q = select(EngineeringReadModel)
    if project_code:
        q = q.where(EngineeringReadModel.project_code == project_code)
    if manufacturing_area:
        q = q.where(EngineeringReadModel.manufacturing_area == manufacturing_area)
    rows = db.scalars(q).all()
    now = utcnow()
    for row in rows:
        row.status = "stale"; row.invalidated_at = now
    READ_MODEL_STALE.set(sum(1 for x in rows if x.status == "stale"))
    return len(rows)


def cache_key(surface: str, identity_key: str, *parts: str) -> str:
    safe = ":".join(str(p).replace(" ", "_") for p in parts)
    return f"mgc:v6310:{surface}:{identity_key}:{safe}"


def etag_for_payload(payload: dict) -> str:
    return '"' + payload_sha(payload) + '"'


def read_model_status(db: Session) -> dict:
    rows = db.scalars(select(EngineeringReadModel).order_by(EngineeringReadModel.updated_at.desc())).all()
    pending = int(db.scalar(select(func.count()).select_from(ProjectionOutboxEvent).where(
        ProjectionOutboxEvent.target == TARGET_READ_MODEL,
        ProjectionOutboxEvent.status.in_(("pending", "retry", "processing")),
    )) or 0)
    counts = {"fresh": 0, "stale": 0, "other": 0}
    for row in rows:
        counts[row.status if row.status in counts else "other"] += 1
    READ_MODEL_STALE.set(counts["stale"])
    return {
        "schema": "mgc-read-model-status-v1",
        "authoritative": False,
        "rebuildable": True,
        "counts": counts,
        "pending_invalidations": pending,
        "cache": {"redis_required_for_correctness": False, "ttl_seconds": get_settings().read_model_cache_ttl_seconds},
        "items": [{"model_key": x.model_key, "model_type": x.model_type, "project_code": x.project_code, "manufacturing_area": x.manufacturing_area, "status": x.status, "etag": x.payload_sha256, "generated_at": x.generated_at.isoformat() if x.generated_at else None, "invalidated_at": x.invalidated_at.isoformat() if x.invalidated_at else None} for x in rows[:100]],
    }


def rebuild_read_models(db: Session, *, project_code: str | None = None, manufacturing_area: str | None = None) -> dict:
    q = select(EngineeringReadModel)
    if project_code:
        q = q.where(EngineeringReadModel.project_code == project_code)
    if manufacturing_area:
        q = q.where(EngineeringReadModel.manufacturing_area == manufacturing_area)
    rows = db.scalars(q).all()
    rebuilt = 0
    skipped = 0
    for row in rows:
        if row.model_type == "wi_coverage" and row.project_code and row.manufacturing_area:
            payload = wi_coverage_payload(db, row.project_code, row.manufacturing_area)
            row.payload_json = payload
            row.payload_sha256 = payload_sha(payload)
            row.source_version = row.payload_sha256
            row.status = "fresh"
            row.generated_at = utcnow()
            row.invalidated_at = None
            rebuilt += 1
        else:
            skipped += 1
    db.commit()
    redis_cache_delete_prefix("mgc:v6310:")
    return {"rebuilt": rebuilt, "skipped": skipped, "authoritative_data_changed": False}
