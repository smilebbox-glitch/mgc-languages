#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.services.performance_certification import PROFILES, capacity_envelope  # noqa: E402

REQUIRED_INDEX_NAMES = {
    "idx_v604_bom_parent_revision_child",
    "idx_v604_relationship_subject_predicate",
    "idx_v604_relationship_object_predicate",
    "idx_v604_vehicle_build_project_vin_status",
    "idx_v604_genealogy_build_part_supplier_lot",
    "idx_v604_series_project_time_part",
    "idx_v604_external_object_system_type_part",
    "idx_v604_ingest_system_status_received",
    "idx_v604_mapping_project_type_status",
}


def _source_contains_indexes() -> tuple[bool, list[str]]:
    text = (ROOT / "backend/app/db/migrations.py").read_text(encoding="utf-8")
    missing = sorted(x for x in REQUIRED_INDEX_NAMES if x not in text)
    return not missing, missing


def main() -> None:
    ap = argparse.ArgumentParser(description="MGC v6.0.9 performance/capacity preflight")
    ap.add_argument("--profile", choices=sorted(PROFILES), default="ci")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    # Avoid importing the script as a module with hyphen/packaging assumptions.
    cpus = max(1, os.cpu_count() or 1)
    ram = None
    p = Path("/proc/meminfo")
    if p.exists():
        for line in p.read_text(encoding="utf-8", errors="ignore").splitlines():
            if line.startswith("MemTotal:"):
                ram = int(line.split()[1]) / 1024 / 1024
                break
    ok, missing = _source_contains_indexes()
    result = {
        "status": "PASS" if ok else "FAIL",
        "profile": args.profile,
        "critical_index_declarations": {"status": "PASS" if ok else "FAIL", "missing": missing},
        "capacity_envelope": capacity_envelope(logical_cpus=cpus, ram_gib=ram, profile=args.profile),
        "governance": {
            "container_results_are_not_enterprise_certification": True,
            "live_postgresql_redis_qdrant_test_required": args.profile != "ci",
        },
    }
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"performance preflight: {result['status']}")
        print(json.dumps(result, ensure_ascii=False, indent=2))
    raise SystemExit(0 if ok else 2)


if __name__ == "__main__":
    main()
