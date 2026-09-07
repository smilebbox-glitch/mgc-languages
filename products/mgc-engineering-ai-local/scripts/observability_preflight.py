#!/usr/bin/env python3
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
checks: list[tuple[str, bool]] = []

def add(name: str, ok: bool): checks.append((name, bool(ok)))

def text(path: str) -> str: return (ROOT / path).read_text(encoding="utf-8")

svc = text("backend/app/services/production_support.py")
router = text("backend/app/api/operations_routes.py")
logging = text("backend/app/core/request_logging.py")
models = text("backend/app/db/models.py")
config = text("backend/app/core/config.py")
main = text("backend/app/main.py")

add("operational health sample model", "class OperationalHealthSample" in models)
add("production incident model", "class ProductionIncident" in models)
add("dependency SLO/error budget", "def dependency_sli" in svc and "def error_budget" in svc)
add("queue + integration lag", "def queue_snapshot" in svc and "def integration_lag_snapshot" in svc)
add("privacy-safe support bundle", "contains_raw_logs\": False" in svc and "contains_document_content\": False" in svc and "contains_queries\": False" in svc)
add("support bundle redacts incident evidence", "redact_details(r.evidence_json" in svc)
add("bounded route-template HTTP metrics", "HTTP_REQUESTS" in logging and "route_template" in logging)
for forbidden in ['["user"]', '["vin"]', '["part_number"]', '["document_id"]', '["query"]']:
    add(f"no prometheus high-cardinality label {forbidden}", forbidden not in logging + svc)
add("operations API requires identity", "Depends(get_identity)" in router)
add("operations router mounted", "operations_router" in main)
add("health sample retention configured", "operational_health_retention_days" in config and "OperationalHealthSample.captured_at < cutoff" in svc)
add("human operator boundary", "human_operator_required" in svc)

failed=[n for n,ok in checks if not ok]
for name,ok in checks:
    print(f"{'PASS' if ok else 'FAIL'}  {name}")
print(f"\nObservability/reliability preflight: {len(checks)-len(failed)}/{len(checks)} PASS")
if failed:
    raise SystemExit(1)
