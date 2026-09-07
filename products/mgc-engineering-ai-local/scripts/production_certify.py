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
from app.core.load_certification import (  # noqa: E402
    LOAD_EVIDENCE_SCHEMA,
    canonical_payload_bytes,
    validate_integrity,
)
from app.core.production_certification import evaluate_target_host_evidence, normalize_profile  # noqa: E402


def _verify_detached_signature(load: dict, signature: Path, public_key: Path) -> tuple[bool, str]:
    with tempfile.NamedTemporaryFile(prefix="mgc-load-verify-", delete=False) as fh:
        fh.write(canonical_payload_bytes(load)); temp = Path(fh.name)
    try:
        proc = subprocess.run(
            ["openssl", "dgst", "-sha256", "-verify", str(public_key), "-signature", str(signature), str(temp)],
            capture_output=True, text=True,
        )
        detail = (proc.stdout or proc.stderr or "").strip()
        return proc.returncode == 0, detail
    finally:
        temp.unlink(missing_ok=True)


def _attach_load_evidence(evidence: dict, load: dict, *, signature: str, public_key: str) -> dict:
    out = dict(evidence)
    load = json.loads(json.dumps(load))
    integrity = load.setdefault("integrity", {})
    integrity["detached_signature_verified"] = False
    integrity.pop("signature_verification_failed", None)

    valid_digest, _claimed, _actual = validate_integrity(load)
    if valid_digest is False:
        integrity["signature_verification_failed"] = True
    if bool(signature) != bool(public_key):
        raise ValueError("--load-signature and --load-public-key must be provided together")
    if signature and public_key and valid_digest is not False:
        ok, detail = _verify_detached_signature(load, Path(signature), Path(public_key))
        integrity["detached_signature_verified"] = ok
        integrity["signature_verification_failed"] = not ok
        integrity["verification_tool"] = "openssl dgst -sha256 -verify"
        integrity["verification_detail"] = detail[:160]

    out["load_certification"] = load
    summary = load.get("summary") or {}
    saturation = load.get("saturation") or {}
    out["http"] = {
        "requests": summary.get("requests"),
        "p50_ms": summary.get("p50_ms"),
        "p95_ms": summary.get("p95_ms"),
        "p99_ms": summary.get("p99_ms"),
        "error_rate": summary.get("error_rate"),
        "requests_per_second": summary.get("requests_per_second"),
    }
    out["database_pool"] = {
        **(out.get("database_pool") or {}),
        "max_saturation_ratio": ((saturation.get("db_pool") or {}).get("max_saturation_ratio")),
    }
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="Evaluate target-host MGC production acceptance evidence.")
    ap.add_argument("--profile", required=True, help="15, 30 or 100")
    ap.add_argument("--topology", required=True)
    ap.add_argument("--evidence", required=True)
    ap.add_argument("--load-evidence", default="", help=f"Optional {LOAD_EVIDENCE_SCHEMA} JSON; required for v6.3.34 technical GO")
    ap.add_argument("--load-signature", default="", help="Detached signature produced by production_load_certify.py")
    ap.add_argument("--load-public-key", default="", help="PEM public key used to verify detached load-evidence signature")
    ap.add_argument("--output", default="")
    ap.add_argument("--require-go", action="store_true", help="Exit non-zero unless technical decision is GO")
    args = ap.parse_args()
    profile = normalize_profile(args.profile)
    topology = json.loads(Path(args.topology).read_text(encoding="utf-8"))
    evidence = json.loads(Path(args.evidence).read_text(encoding="utf-8"))
    if args.load_evidence:
        load = json.loads(Path(args.load_evidence).read_text(encoding="utf-8"))
        try:
            evidence = _attach_load_evidence(evidence, load, signature=args.load_signature, public_key=args.load_public_key)
        except ValueError as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            return 2
    elif args.load_signature or args.load_public_key:
        print("ERROR: signature/public key require --load-evidence", file=sys.stderr)
        return 2
    result = evaluate_target_host_evidence(profile=profile, topology=topology, evidence=evidence)
    result["load_evidence_ingested"] = bool(args.load_evidence)
    result["load_signature_verified"] = bool(((evidence.get("load_certification") or {}).get("integrity") or {}).get("detached_signature_verified"))
    text = json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True)
    print(text)
    if args.output:
        Path(args.output).write_text(text + "\n", encoding="utf-8")
    if args.require_go and result["decision"] != "GO":
        return 2
    return 0 if result["decision"] != "NO_GO" else 2


if __name__ == "__main__":
    raise SystemExit(main())
