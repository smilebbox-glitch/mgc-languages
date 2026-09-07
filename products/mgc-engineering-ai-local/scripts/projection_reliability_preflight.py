#!/usr/bin/env python3
"""v6.3.2 static gates for transactional outbox and rebuildable projections."""
from pathlib import Path
import ast
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

checks=[]
def check(name, ok, detail=""):
    checks.append((name, bool(ok), detail))

from app.core.runtime_contract import APP_VERSION, SCHEMA_VERSION
from app.db.models import DocumentSearchChunk, ProjectionOutboxEvent, ProjectionDeliveryReceipt

check("release_version", APP_VERSION == "6.3.34", APP_VERSION)
check("schema_version", SCHEMA_VERSION == "6.3.13", SCHEMA_VERSION)
check("authoritative_chunk_table", DocumentSearchChunk.__tablename__ == "document_search_chunks")
check("outbox_table", ProjectionOutboxEvent.__tablename__ == "projection_outbox_events")
check("receipt_table", ProjectionDeliveryReceipt.__tablename__ == "projection_delivery_receipts")

outbox=(ROOT/"backend/app/services/projection_outbox.py").read_text()
ingest=(ROOT/"backend/app/services/ingest.py").read_text()
vector=(ROOT/"backend/app/services/vector_store.py").read_text()
graph=(ROOT/"backend/app/services/graph_store.py").read_text()
worker=(ROOT/"backend/app/workers/tasks.py").read_text()
beat=(ROOT/"backend/app/workers/celery_app.py").read_text()
ops=(ROOT/"backend/app/api/operations_routes.py").read_text()

check("ingest_persists_projection_source", "persist_document_chunks" in ingest)
check("ingest_enqueues_transactionally", "enqueue_document_projections" in ingest)
check("ingest_has_no_direct_projection_ports", "get_search_port" not in ingest and "get_graph_projection_port" not in ingest and "get_object_storage_port" not in ingest)
check("outbox_dedupe_key", "idempotency_key" in outbox and "_event_key" in outbox)
check("outbox_retry", 'status = "retry"' in outbox and "projection_retry_base_seconds" in outbox)
check("outbox_dlq", 'status = "dead_letter"' in outbox)
check("outbox_worker_lease", "projection_lock_timeout_seconds" in outbox and "worker lease expired" in outbox)
check("outbox_supersedes_stale_events", "newer_authoritative_version" in outbox)
check("delivery_receipt", "ProjectionDeliveryReceipt" in outbox)
check("legacy_backfill", "ensure_document_projection_source" in outbox)
check("manual_rebuild", "enqueue_rebuild" in outbox)
check("dlq_replay", "replay_dead_letter" in outbox)
check("health_lag", "oldest_event_age_seconds" in outbox and "projection_lag_warning_seconds" in outbox)
check("qdrant_ids_deterministic", "uuid.uuid5" in vector and "sha256" in vector)
check("graph_replacement_semantics", "DELETE r" in graph and "HAS_DOCUMENT|CONTAINS" in graph)
check("worker_task", 'name="process_projection_outbox"' in worker)
check("beat_schedule", "process-projection-outbox" in beat)
check("ops_status_api", '@router.get("/projections")' in ops)
check("ops_rebuild_api", '@router.post("/projections/rebuild")' in ops)
check("ops_dlq_api", '/projections/dlq/{event_id}/replay' in ops)
check("core_failure_non_gating", '"optional_projection_failure_blocks_core": False' in outbox)

for name, ok, detail in checks:
    print(f"{'PASS' if ok else 'FAIL'} | {name}" + (f" | {detail}" if detail else ""))
failed=[x for x in checks if not x[1]]
print(f"\n{len(checks)-len(failed)}/{len(checks)} PASS")
raise SystemExit(1 if failed else 0)
