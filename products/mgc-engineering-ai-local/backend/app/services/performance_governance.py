from __future__ import annotations

import base64
import json
from dataclasses import dataclass, asdict
from typing import Iterable, TypeVar

from app.core.config import get_settings
from app.core.db_performance import performance_snapshot

T = TypeVar("T")

@dataclass(frozen=True)
class ScaleProfile:
    code: str
    named_users: int
    target_concurrent_users: int
    db_pool_size: int
    db_max_overflow: int
    request_p95_ms: int
    db_query_p95_ms: int
    max_statements_per_request: int
    note: str

SCALE_PROFILES: dict[str, ScaleProfile] = {
    "pilot_15": ScaleProfile("pilot_15", 15, 5, 10, 10, 500, 100, 40, "Small controlled engineering pilot; CPU-first reference."),
    "pilot_30": ScaleProfile("pilot_30", 30, 10, 15, 15, 500, 100, 40, "Department pilot; validate representative BOM/WI/Object 360 workloads."),
    "enterprise_100": ScaleProfile("enterprise_100", 100, 30, 30, 30, 750, 150, 50, "Reference only. Target-host benchmark and DBA review are mandatory."),
}

def scale_profiles() -> list[dict]:
    return [asdict(v) for v in SCALE_PROFILES.values()]

def performance_governance_snapshot(engine=None) -> dict:
    cfg = get_settings()
    selected = SCALE_PROFILES.get(cfg.performance_scale_profile, SCALE_PROFILES["pilot_30"])
    db = performance_snapshot(engine)
    pool = db.get("pool") or {}
    size = int(pool.get("size") or 0)
    checked = int(pool.get("checked_out") or 0)
    saturation = (checked / size) if size else 0.0
    return {
        "schema": "mgc-performance-governance-v639",
        "selected_profile": asdict(selected),
        "database": db,
        "operational_status": "WARN" if size and saturation >= 0.9 else "OK",
        "pool_saturation_ratio": round(saturation, 4),
        "pagination": {"default_limit": cfg.cursor_page_default_limit, "max_limit": cfg.cursor_page_max_limit, "strategy": "keyset/cursor for new high-cardinality endpoints"},
        "bulk_ingestion": {"batch_size": cfg.bulk_ingest_batch_size, "single_transaction_unbounded_batches": False},
        "certification_required": True,
        "production_capacity_claim": False,
    }

def encode_cursor(created_at, row_id: str) -> str:
    raw = json.dumps({"created_at": created_at.isoformat(), "id": str(row_id)}, separators=(",", ":"), sort_keys=True).encode()
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")

def decode_cursor(cursor: str) -> tuple[str, str]:
    try:
        padded = cursor + "=" * (-len(cursor) % 4)
        obj = json.loads(base64.urlsafe_b64decode(padded.encode()).decode())
        return str(obj["created_at"]), str(obj["id"])
    except Exception as exc:
        raise ValueError("Invalid cursor") from exc

def bounded_batch(items: Iterable[T], batch_size: int | None = None) -> Iterable[list[T]]:
    size = max(1, min(int(batch_size or get_settings().bulk_ingest_batch_size), 5000))
    batch: list[T] = []
    for item in items:
        batch.append(item)
        if len(batch) >= size:
            yield batch
            batch = []
    if batch:
        yield batch
