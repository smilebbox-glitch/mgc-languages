#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from app.core.runtime_contract import APP_VERSION, SCHEMA_VERSION


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    root = Path(sys.argv[1]).resolve()
    required = ["postgres.dump", "storage.tar.gz", "CONSISTENCY_SNAPSHOT.json"]
    missing = [name for name in required if not (root / name).is_file()]
    if missing:
        raise SystemExit("missing authoritative backup artifacts: " + ", ".join(missing))

    consistency = json.loads((root / "CONSISTENCY_SNAPSHOT.json").read_text(encoding="utf-8"))
    if consistency.get("schema") != "mgc.authoritative-consistency.v1":
        raise SystemExit("unsupported consistency snapshot schema")
    if consistency.get("status") != "pass" or int(consistency.get("critical_findings") or 0) != 0:
        raise SystemExit("authoritative consistency snapshot is not PASS")
    if not consistency.get("policy", {}).get("backup_eligible"):
        raise SystemExit("consistency snapshot is not eligible for certified backup")
    if consistency.get("schema_version") != SCHEMA_VERSION:
        raise SystemExit(f"consistency snapshot schema mismatch: {consistency.get('schema_version')} != {SCHEMA_VERSION}")

    names = required[:]
    if (root / "qdrant.snapshot").is_file():
        names.append("qdrant.snapshot")
    files = {name: {"sha256": sha256(root / name), "size_bytes": (root / name).stat().st_size} for name in names}
    quiesce_mode = os.environ.get("MGC_BACKUP_QUIESCE_MODE", "true").lower() == "true"
    quiesced_services = [x for x in os.environ.get("MGC_BACKUP_QUIESCED_SERVICES", "").split(",") if x]
    manifest = {
        "schema": "mgc-core-backup-v2",
        "application_version": APP_VERSION,
        "schema_version": SCHEMA_VERSION,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "consistency_epoch_id": consistency.get("epoch_id"),
        "authoritative_fingerprints": {
            "database_logical_sha256": consistency.get("database", {}).get("logical_sha256"),
            "storage_tree_sha256": consistency.get("storage", {}).get("tree_sha256"),
        },
        "quiesced": quiesce_mode,
        "quiesced_services": quiesced_services,
        "certifiable_authoritative_backup": bool(quiesce_mode),
        "restorable_authoritative_set": ["postgres", "evidence_storage"],
        "optional_rebuildable_snapshot_set": ["qdrant_index"] if "qdrant.snapshot" in names else [],
        "derived_or_transient_not_backed_up": ["redis_queue", "neo4j_projection", "engineering_read_models", "local_model_weights", "container_images"],
        "files": files,
        "contains_secrets": False,
    }
    (root / "BACKUP_MANIFEST.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    lines = [f"{meta['sha256']}  {name}" for name, meta in sorted(files.items())]
    (root / "SHA256SUMS").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
