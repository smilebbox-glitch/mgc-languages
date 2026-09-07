#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> int:
    ap = argparse.ArgumentParser(description="Compare v6.3.14 authoritative consistency snapshots")
    ap.add_argument("expected")
    ap.add_argument("actual")
    ap.add_argument("--output")
    args = ap.parse_args()

    expected = json.loads(Path(args.expected).read_text(encoding="utf-8"))
    actual = json.loads(Path(args.actual).read_text(encoding="utf-8"))
    checks = {
        "snapshot_schema": expected.get("schema") == actual.get("schema") == "mgc.authoritative-consistency.v1",
        "schema_version": expected.get("schema_version") == actual.get("schema_version"),
        "database_logical_sha256": bool(expected.get("database", {}).get("logical_sha256")) and expected.get("database", {}).get("logical_sha256") == actual.get("database", {}).get("logical_sha256"),
        "storage_tree_sha256": bool(expected.get("storage", {}).get("tree_sha256")) and expected.get("storage", {}).get("tree_sha256") == actual.get("storage", {}).get("tree_sha256"),
        "actual_integrity": actual.get("status") == "pass" and int(actual.get("critical_findings") or 0) == 0,
    }
    report = {
        "schema": "mgc.authoritative-consistency-compare.v1",
        "status": "pass" if all(checks.values()) else "fail",
        "checks": checks,
        "expected_epoch_id": expected.get("epoch_id"),
        "expected_database_sha256": expected.get("database", {}).get("logical_sha256"),
        "actual_database_sha256": actual.get("database", {}).get("logical_sha256"),
        "expected_storage_sha256": expected.get("storage", {}).get("tree_sha256"),
        "actual_storage_sha256": actual.get("storage", {}).get("tree_sha256"),
        "actual_critical_findings": actual.get("critical_findings"),
    }
    payload = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        Path(args.output).write_text(payload, encoding="utf-8")
    print(payload, end="")
    return 0 if report["status"] == "pass" else 3


if __name__ == "__main__":
    raise SystemExit(main())
