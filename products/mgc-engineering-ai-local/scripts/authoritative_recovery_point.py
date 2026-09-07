#!/usr/bin/env python3
"""Create a consistency-bound recovery point for external DB/evidence HA operations."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from app.core.authoritative_ha import database_authority_probe, read_evidence_marker
from app.core.config import get_settings
from app.core.runtime_contract import APP_VERSION, SCHEMA_VERSION
from app.db.session import SessionLocal
from app.services.dr_consistency import build_consistency_snapshot, postgres_pitr_status

SCHEMA = "mgc-authoritative-recovery-point-v1"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--output", required=True)
    ap.add_argument("--max-findings", type=int, default=100)
    args = ap.parse_args()
    cfg = get_settings()
    db_auth = database_authority_probe()
    if not db_auth.enabled or not db_auth.safe:
        raise SystemExit("Refusing recovery point: writable approved PostgreSQL primary is not proven")
    marker = read_evidence_marker()
    if not marker or marker.get("state") != "active":
        raise SystemExit("Refusing recovery point: active evidence generation is not proven")
    with SessionLocal() as db:
        snap = build_consistency_snapshot(db, Path(cfg.storage_dir), hash_files=True, hash_database=True, max_findings=args.max_findings)
        pitr = postgres_pitr_status(db)
    if snap.get("status") != "pass" or not snap.get("policy", {}).get("backup_eligible"):
        raise SystemExit("Refusing recovery point: authoritative consistency snapshot failed")
    out = {
        "schema": SCHEMA,
        "application_version": APP_VERSION,
        "schema_version": SCHEMA_VERSION,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "database_system_identifier": db_auth.system_identifier,
        "database_wal_lsn": pitr.get("checkpoint_lsn"),
        "database_logical_sha256": snap.get("database", {}).get("logical_sha256"),
        "evidence_cluster_id": marker.get("cluster_id"),
        "evidence_generation": marker.get("generation"),
        "evidence_tree_sha256": snap.get("storage", {}).get("tree_sha256"),
        "consistency_epoch_id": snap.get("epoch_id"),
        "production_authorized": False,
    }
    path = Path(args.output)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(out, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": "pass", "output": str(path), "evidence_generation": out["evidence_generation"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
