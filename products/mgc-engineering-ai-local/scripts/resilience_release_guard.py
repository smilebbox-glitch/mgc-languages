#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from app.core.resilience_certification import (  # noqa: E402
    canonical_payload_bytes,
    validate_release_bundle,
)


def load(path: str) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def public_key_sha256(path: str) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def verify_signature(evidence: dict, signature: str, public_key: str) -> dict:
    openssl = shutil.which("openssl")
    if not openssl:
        return {"verified": False, "algorithm": "openssl-sha256", "public_key_sha256": "", "errors": ["openssl_unavailable"]}
    with tempfile.NamedTemporaryFile("wb", delete=False) as tmp:
        tmp.write(canonical_payload_bytes(evidence))
        payload = tmp.name
    try:
        p = subprocess.run(
            [openssl, "dgst", "-sha256", "-verify", public_key, "-signature", signature, payload],
            text=True, capture_output=True, check=False,
        )
        return {
            "verified": p.returncode == 0,
            "algorithm": "openssl-sha256",
            "public_key_sha256": public_key_sha256(public_key),
            "errors": [] if p.returncode == 0 else ["signature_verification_failed"],
        }
    finally:
        Path(payload).unlink(missing_ok=True)


def main() -> int:
    ap = argparse.ArgumentParser(description="Fail-closed v6.3.34 resilience certification release gate")
    ap.add_argument("--report", required=True)
    ap.add_argument("--evidence", required=True)
    ap.add_argument("--signature", required=True)
    ap.add_argument("--public-key", required=True)
    ap.add_argument("--baseline", required=True)
    ap.add_argument("--campaign", required=True)
    args = ap.parse_args()

    report = load(args.report)
    evidence = load(args.evidence)
    baseline = load(args.baseline)
    campaign = load(args.campaign)
    sig = verify_signature(evidence, args.signature, args.public_key)
    valid, errors = validate_release_bundle(
        report,
        current_evidence=evidence,
        signature_verification=sig,
        baseline=baseline,
        campaign=campaign,
        require_go=True,
    )
    if not valid:
        raise SystemExit("NO_GO: resilience certification release gate failed: " + ", ".join(errors))
    print("PASS: resilience certification source bundle recomputed and GO")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
