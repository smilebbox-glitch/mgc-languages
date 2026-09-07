#!/usr/bin/env python3
"""Manage the target-local evidence HA generation marker.

The .mgc-ha marker is operational fencing metadata and MUST NOT be copied by evidence
replication or authoritative backup/restore. Promotion never proves replication itself;
--recovery-point is required to bind the promoted target to an independently verified
PostgreSQL/evidence consistency point.
"""
from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path

MARKER_SCHEMA = "mgc-evidence-ha-marker-v1"
RECOVERY_SCHEMA = "mgc-authoritative-recovery-point-v1"


def atomic_write(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.parent.is_symlink() or path.is_symlink():
        raise SystemExit("Refusing evidence marker write through symlink")
    tmp = path.with_name(path.name + f".tmp-{os.getpid()}")
    data = (json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o640)
    try:
        with os.fdopen(fd, "wb", closefd=True) as fh:
            fh.write(data)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, path)
        dir_fd = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(dir_fd)
        finally:
            os.close(dir_fd)
    finally:
        if tmp.exists():
            tmp.unlink()


def load(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or data.get("schema") != MARKER_SCHEMA:
        raise SystemExit("Invalid evidence HA marker")
    return data


def marker_path(storage: Path, rel: str) -> Path:
    root = storage.resolve()
    rel_path = Path(rel)
    if not rel or rel_path.is_absolute():
        raise SystemExit("Marker path must be relative to storage root")
    p = Path(os.path.abspath(str(root / rel_path)))
    try:
        relative = p.relative_to(root)
    except ValueError as exc:
        raise SystemExit("Marker path escapes storage root") from exc
    current = root
    for part in relative.parts:
        current = current / part
        if current.exists() and current.is_symlink():
            raise SystemExit("Marker path contains a symlink")
    return p


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--storage", required=True)
    ap.add_argument("--marker", default=".mgc-ha/STORAGE_EPOCH.json")
    sub = ap.add_subparsers(dest="cmd", required=True)

    init = sub.add_parser("init")
    init.add_argument("--cluster-id", required=True)
    init.add_argument("--database-system-identifier", required=True)
    init.add_argument("--state", choices=["active", "standby"], default="standby")
    init.add_argument("--generation", type=int, default=1)

    demote = sub.add_parser("demote")
    demote.add_argument("--confirm", required=True)

    promote = sub.add_parser("promote")
    promote.add_argument("--cluster-id", required=True)
    promote.add_argument("--database-system-identifier", required=True)
    promote.add_argument("--expected-generation", type=int, required=True)
    promote.add_argument("--recovery-point", required=True)
    promote.add_argument("--confirm", required=True)

    sub.add_parser("show")

    args = ap.parse_args()
    storage = Path(args.storage)
    path = marker_path(storage, args.marker)

    if args.cmd == "init":
        if path.exists():
            raise SystemExit("Marker already exists; use promote/demote explicitly")
        if args.generation < 1:
            raise SystemExit("Generation must be >= 1")
        payload = {
            "schema": MARKER_SCHEMA,
            "cluster_id": args.cluster_id,
            "database_system_identifier": args.database_system_identifier,
            "generation": args.generation,
            "state": args.state,
            "updated_at_utc": now(),
            "promotion_evidence": None,
            "production_authorized": False,
        }
        atomic_write(path, payload)
    elif args.cmd == "demote":
        if args.confirm != "DEMOTE_EVIDENCE":
            raise SystemExit("Refusing demotion without --confirm DEMOTE_EVIDENCE")
        payload = load(path)
        payload.update({"state": "standby", "updated_at_utc": now(), "production_authorized": False})
        atomic_write(path, payload)
    elif args.cmd == "promote":
        if args.confirm != "PROMOTE_EVIDENCE":
            raise SystemExit("Refusing promotion without --confirm PROMOTE_EVIDENCE")
        payload = load(path)
        if int(payload.get("generation") or 0) != args.expected_generation:
            raise SystemExit("Generation changed; refuse stale promotion")
        if str(payload.get("cluster_id") or "") != args.cluster_id:
            raise SystemExit("Evidence cluster id mismatch")
        rp = json.loads(Path(args.recovery_point).read_text(encoding="utf-8"))
        if rp.get("schema") != RECOVERY_SCHEMA:
            raise SystemExit("Invalid recovery point schema")
        if rp.get("evidence_cluster_id") != args.cluster_id:
            raise SystemExit("Recovery point belongs to another evidence cluster")
        if rp.get("database_system_identifier") != args.database_system_identifier:
            raise SystemExit("Recovery point belongs to another PostgreSQL cluster")
        if int(rp.get("evidence_generation") or 0) != args.expected_generation:
            raise SystemExit("Recovery point generation mismatch")
        if not rp.get("database_logical_sha256") or not rp.get("evidence_tree_sha256"):
            raise SystemExit("Recovery point is missing authoritative fingerprints")
        payload.update({
            "database_system_identifier": args.database_system_identifier,
            "generation": args.expected_generation + 1,
            "state": "active",
            "updated_at_utc": now(),
            "promotion_evidence": {
                "recovery_point_schema": RECOVERY_SCHEMA,
                "consistency_epoch_id": rp.get("consistency_epoch_id"),
                "database_logical_sha256": rp.get("database_logical_sha256"),
                "evidence_tree_sha256": rp.get("evidence_tree_sha256"),
            },
            "production_authorized": False,
        })
        atomic_write(path, payload)
    else:
        payload = load(path)

    print(json.dumps(load(path), ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
