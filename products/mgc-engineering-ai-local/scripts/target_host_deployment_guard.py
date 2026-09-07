#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from app.core.runtime_contract import APP_VERSION, SCHEMA_VERSION  # noqa: E402
from app.core.target_host_assurance import REPORT_SCHEMA, canonical_payload_bytes, validate_integrity  # noqa: E402


def verify_signature(report: dict, signature: Path, public_key: Path) -> bool:
    with tempfile.NamedTemporaryFile(prefix="mgc-host-assurance-verify-", delete=False) as fh:
        fh.write(canonical_payload_bytes(report)); temp = Path(fh.name)
    try:
        p = subprocess.run(["openssl", "dgst", "-sha256", "-verify", str(public_key), "-signature", str(signature), str(temp)], capture_output=True, text=True)
        return p.returncode == 0
    finally:
        temp.unlink(missing_ok=True)


def main() -> int:
    ap = argparse.ArgumentParser(description="Fail-closed target-host assurance gate for MGC deployment")
    ap.add_argument("--report", required=True)
    ap.add_argument("--signature", default="")
    ap.add_argument("--public-key", default="")
    ap.add_argument("--require-signature", action="store_true")
    args = ap.parse_args()
    try:
        report = json.loads(Path(args.report).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"ERROR: cannot read target-host assurance report: {exc}", file=sys.stderr); return 2
    valid, claimed, actual = validate_integrity(report)
    checks = {
        "report_schema": report.get("schema") == REPORT_SCHEMA,
        "release_match": report.get("release") == APP_VERSION,
        "schema_match": report.get("schema_version") == SCHEMA_VERSION,
        "decision_pass": report.get("decision") == "PASS",
        "integrity_valid": valid,
        "human_approval_preserved": report.get("human_approval_required") is True and report.get("production_authorized") is False,
    }
    signature_requested = bool(args.signature or args.public_key or args.require_signature)
    if signature_requested:
        if not (args.signature and args.public_key):
            checks["detached_signature_verified"] = False
        else:
            try:
                checks["detached_signature_verified"] = verify_signature(report, Path(args.signature), Path(args.public_key))
            except OSError:
                checks["detached_signature_verified"] = False
    for name, ok in checks.items():
        print(("PASS" if ok else "FAIL") + ": " + name)
    if not valid:
        print(f"integrity claimed={claimed} actual={actual}", file=sys.stderr)
    if not all(checks.values()):
        return 2
    print(f"PASS: target-host deployment assurance accepted for {APP_VERSION}/{SCHEMA_VERSION}; human deployment approval is still required.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
