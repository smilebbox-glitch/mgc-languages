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
from app.core.load_certification import canonical_payload_bytes as load_canonical_bytes, validate_integrity as validate_load_integrity  # noqa: E402
from app.core.production_certification import evaluate_target_host_evidence, normalize_profile  # noqa: E402
from app.core.release_acceptance import (  # noqa: E402
    APPROVED_BASELINE_SCHEMA,
    attach_integrity,
    build_release_acceptance,
    canonical_payload_bytes,
    validate_integrity,
)
from app.core.release_provenance import register_signed_artifact, ProvenanceError


def verify_signature(payload: bytes, signature: Path, public_key: Path) -> tuple[bool, str]:
    with tempfile.NamedTemporaryFile(prefix="mgc-acceptance-verify-", delete=False) as fh:
        fh.write(payload); temp = Path(fh.name)
    try:
        proc = subprocess.run(["openssl", "dgst", "-sha256", "-verify", str(public_key), "-signature", str(signature), str(temp)], capture_output=True, text=True)
        return proc.returncode == 0, (proc.stdout or proc.stderr or "").strip()
    finally:
        temp.unlink(missing_ok=True)


def sign_payload(payload: bytes, key: Path, signature: Path) -> None:
    with tempfile.NamedTemporaryFile(prefix="mgc-acceptance-sign-", delete=False) as fh:
        fh.write(payload); temp = Path(fh.name)
    try:
        proc = subprocess.run(["openssl", "dgst", "-sha256", "-sign", str(key), "-out", str(signature), str(temp)], capture_output=True, text=True)
        if proc.returncode != 0:
            raise RuntimeError((proc.stderr or proc.stdout or "openssl sign failed").strip())
    finally:
        temp.unlink(missing_ok=True)


def load_verified_load(path: Path, signature: Path, public_key: Path) -> dict:
    doc = json.loads(path.read_text(encoding="utf-8"))
    valid_digest, _claimed, _actual = validate_load_integrity(doc)
    if valid_digest is not True:
        raise ValueError("load evidence canonical digest invalid")
    ok, detail = verify_signature(load_canonical_bytes(doc), signature, public_key)
    integrity = doc.setdefault("integrity", {})
    integrity["detached_signature_verified"] = ok
    integrity["signature_verification_failed"] = not ok
    integrity["verification_tool"] = "openssl dgst -sha256 -verify"
    integrity["verification_detail"] = detail[:160]
    if not ok:
        raise ValueError("load evidence detached signature verification failed")
    return doc


def load_verified_baseline(path: Path, signature: Path, public_key: Path) -> dict:
    doc = json.loads(path.read_text(encoding="utf-8"))
    if doc.get("schema") != APPROVED_BASELINE_SCHEMA:
        raise ValueError("baseline schema mismatch")
    valid_digest, _claimed, _actual = validate_integrity(doc)
    if valid_digest is not True:
        raise ValueError("baseline canonical digest invalid")
    ok, detail = verify_signature(canonical_payload_bytes(doc), signature, public_key)
    integrity = doc.setdefault("integrity", {})
    integrity["detached_signature_verified"] = ok
    integrity["signature_verification_failed"] = not ok
    integrity["verification_tool"] = "openssl dgst -sha256 -verify"
    integrity["verification_detail"] = detail[:160]
    if not ok:
        raise ValueError("baseline detached signature verification failed")
    return doc


def main() -> int:
    ap = argparse.ArgumentParser(description="MGC v6.3.34 automated release acceptance pipeline")
    ap.add_argument("--profile", required=True)
    ap.add_argument("--topology", required=True)
    ap.add_argument("--evidence", required=True, help="Target-host failover/RTO/RPO/LB evidence JSON")
    ap.add_argument("--load-evidence", required=True)
    ap.add_argument("--load-signature", required=True)
    ap.add_argument("--load-public-key", required=True)
    ap.add_argument("--baseline", default="")
    ap.add_argument("--baseline-signature", default="")
    ap.add_argument("--baseline-public-key", default="")
    ap.add_argument("--output", required=True)
    ap.add_argument("--signing-key", default="", help="Optional PEM key used to sign the final release acceptance evidence")
    ap.add_argument("--signature-output", default="")
    ap.add_argument("--require-go", action="store_true")
    ap.add_argument("--provenance-registry", default="")
    ap.add_argument("--provenance-key-id", default="")
    args = ap.parse_args()
    profile = normalize_profile(args.profile)
    topology = json.loads(Path(args.topology).read_text(encoding="utf-8"))
    source_evidence = json.loads(Path(args.evidence).read_text(encoding="utf-8"))
    try:
        load = load_verified_load(Path(args.load_evidence), Path(args.load_signature), Path(args.load_public_key))
        baseline = None
        baseline_args = [bool(args.baseline), bool(args.baseline_signature), bool(args.baseline_public_key)]
        if any(baseline_args) and not all(baseline_args):
            raise ValueError("--baseline, --baseline-signature and --baseline-public-key must be provided together")
        if args.baseline:
            baseline = load_verified_baseline(Path(args.baseline), Path(args.baseline_signature), Path(args.baseline_public_key))
    except (ValueError, OSError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr); return 2

    # Attach only verified load evidence; target-host evidence remains a separate retained source.
    merged = json.loads(json.dumps(source_evidence))
    merged["load_certification"] = load
    summary, saturation = load.get("summary") or {}, load.get("saturation") or {}
    merged["http"] = {**(merged.get("http") or {}), "requests": summary.get("requests"), "p50_ms": summary.get("p50_ms"), "p95_ms": summary.get("p95_ms"), "p99_ms": summary.get("p99_ms"), "error_rate": summary.get("error_rate"), "requests_per_second": summary.get("requests_per_second")}
    merged["database_pool"] = {**(merged.get("database_pool") or {}), "max_saturation_ratio": ((saturation.get("db_pool") or {}).get("max_saturation_ratio"))}
    technical = evaluate_target_host_evidence(profile=profile, topology=topology, evidence=merged)
    report = build_release_acceptance(profile=profile, production_report=technical, load_evidence=load, source_evidence=source_evidence, baseline=baseline)

    output = Path(args.output)
    signature_output = Path(args.signature_output) if args.signature_output else output.with_suffix(output.suffix + ".sig")
    if args.signing_key:
        sign_payload(canonical_payload_bytes(report), Path(args.signing_key), signature_output)
        report = attach_integrity(report, detached_signature_verified=False, signature_algorithm="openssl-dgst-sha256")
        report["integrity"]["detached_signature_path_hint"] = signature_output.name
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    provenance_sequence = None
    if args.provenance_registry or args.provenance_key_id:
        if not (args.provenance_registry and args.provenance_key_id and args.signing_key):
            print("ERROR: provenance registration requires --provenance-registry, --provenance-key-id and --signing-key", file=sys.stderr); return 2
        try:
            event = register_signed_artifact(Path(args.provenance_registry), kind="acceptance", document_path=output, signature_path=signature_output, key_id=args.provenance_key_id, actor="release-acceptance-pipeline")
            provenance_sequence = event.get("sequence")
        except ProvenanceError as exc:
            print(f"ERROR: provenance registration failed: {exc}", file=sys.stderr); return 2
    print(json.dumps({"output": str(output), "decision": report["decision"], "technical_decision": report["technical_decision"], "baseline_decision": report["baseline_regression"]["decision"], "canonical_sha256": report["integrity"]["canonical_sha256"], "signature": str(signature_output) if args.signing_key else None, "provenance_sequence": provenance_sequence}, ensure_ascii=False, indent=2))
    if args.require_go and report["decision"] != "GO":
        return 3
    return 0 if report["decision"] != "NO_GO" else 2


if __name__ == "__main__":
    raise SystemExit(main())
