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
    RecoveryRegressionPolicy, build_baseline, build_campaign, canonical_payload_bytes,
    certify_recovery, validate_baseline, validate_campaign, validate_certification,
    validate_drill_evidence_for_certification,
)


def load(path: str) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def dump(path: str, doc: dict) -> None:
    Path(path).write_text(json.dumps(doc, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")


def key_sha256(path: str) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def openssl() -> str:
    exe = shutil.which("openssl")
    if not exe:
        raise SystemExit("openssl CLI is required for detached resilience-evidence signatures")
    return exe


def sign_evidence(evidence: dict, private_key: str, signature_output: str) -> None:
    valid, errors = validate_drill_evidence_for_certification(evidence)
    if not valid:
        raise SystemExit("Refusing to sign invalid/live-incomplete drill evidence: " + ", ".join(errors))
    with tempfile.NamedTemporaryFile("wb", delete=False) as tmp:
        tmp.write(canonical_payload_bytes(evidence)); payload = tmp.name
    try:
        p = subprocess.run([openssl(), "dgst", "-sha256", "-sign", private_key, "-out", signature_output, payload], text=True, capture_output=True, check=False)
        if p.returncode != 0:
            raise SystemExit("OpenSSL signing failed: " + (p.stderr or "unknown error").strip())
    finally:
        Path(payload).unlink(missing_ok=True)


def verify_signature(evidence: dict, signature: str, public_key: str) -> dict:
    valid, errors = validate_drill_evidence_for_certification(evidence)
    if not valid:
        return {"verified": False, "algorithm": "openssl-sha256", "public_key_sha256": key_sha256(public_key), "errors": errors}
    with tempfile.NamedTemporaryFile("wb", delete=False) as tmp:
        tmp.write(canonical_payload_bytes(evidence)); payload = tmp.name
    try:
        p = subprocess.run([openssl(), "dgst", "-sha256", "-verify", public_key, "-signature", signature, payload], text=True, capture_output=True, check=False)
        return {"verified": p.returncode == 0, "algorithm": "openssl-sha256", "public_key_sha256": key_sha256(public_key), "errors": [] if p.returncode == 0 else ["signature_verification_failed"]}
    finally:
        Path(payload).unlink(missing_ok=True)


def main() -> int:
    ap = argparse.ArgumentParser(description="MGC resilience certification & recovery-baseline governance")
    sub = ap.add_subparsers(dest="action", required=True)

    p = sub.add_parser("sign-evidence")
    p.add_argument("--evidence", required=True); p.add_argument("--private-key", required=True); p.add_argument("--signature-output", required=True)

    p = sub.add_parser("verify-signature")
    p.add_argument("--evidence", required=True); p.add_argument("--signature", required=True); p.add_argument("--public-key", required=True)

    p = sub.add_parser("baseline")
    p.add_argument("--evidence", required=True); p.add_argument("--signature", required=True); p.add_argument("--public-key", required=True)
    p.add_argument("--approval-reference", required=True); p.add_argument("--approved-at", required=True); p.add_argument("--approved-by-role", required=True)
    p.add_argument("--bootstrap", action="store_true"); p.add_argument("--confirm", default=""); p.add_argument("--output", required=True)

    p = sub.add_parser("campaign")
    p.add_argument("--baseline", required=True); p.add_argument("--campaign-id", required=True); p.add_argument("--scenario", action="append", required=True)
    p.add_argument("--profile", choices=["core","ai","advanced"], required=True); p.add_argument("--tier", choices=["staging","production"], required=True)
    p.add_argument("--approval-reference", required=True); p.add_argument("--approved-at", required=True); p.add_argument("--approved-by-role", required=True)
    p.add_argument("--max-rto-ratio", type=float, default=1.20); p.add_argument("--max-absolute-increase-seconds", type=float, default=5.0); p.add_argument("--rto-ceiling-seconds", type=float, default=120.0)
    p.add_argument("--confirm", default=""); p.add_argument("--output", required=True)

    p = sub.add_parser("certify")
    p.add_argument("--evidence", required=True); p.add_argument("--signature", required=True); p.add_argument("--public-key", required=True)
    p.add_argument("--baseline", required=True); p.add_argument("--campaign", required=True); p.add_argument("--output", required=True); p.add_argument("--require-go", action="store_true")

    p = sub.add_parser("validate")
    p.add_argument("--file", required=True); p.add_argument("--kind", choices=["baseline","campaign","certification"], required=True); p.add_argument("--require-go", action="store_true")
    args = ap.parse_args()

    if args.action == "sign-evidence":
        sign_evidence(load(args.evidence), args.private_key, args.signature_output)
        print(f"PASS: detached drill-evidence signature written to {args.signature_output}"); return 0
    if args.action == "verify-signature":
        result = verify_signature(load(args.evidence), args.signature, args.public_key); print(json.dumps(result, sort_keys=True, indent=2)); return 0 if result["verified"] else 2
    if args.action == "baseline":
        if args.confirm != "APPROVE-BASELINE": raise SystemExit("Refusing baseline promotion: pass --confirm APPROVE-BASELINE")
        evidence = load(args.evidence); sig = verify_signature(evidence, args.signature, args.public_key)
        doc = build_baseline(evidence, signature_verification=sig, approval_reference=args.approval_reference, approved_at=args.approved_at, approved_by_role=args.approved_by_role, bootstrap=args.bootstrap)
        dump(args.output, doc); print(f"PASS: approved recovery baseline written to {args.output}"); return 0
    if args.action == "campaign":
        if args.confirm != "APPROVE-CAMPAIGN": raise SystemExit("Refusing campaign approval: pass --confirm APPROVE-CAMPAIGN")
        policy = RecoveryRegressionPolicy(args.max_rto_ratio, args.max_absolute_increase_seconds, args.rto_ceiling_seconds)
        doc = build_campaign(campaign_id=args.campaign_id, baseline=load(args.baseline), scenarios=args.scenario, profile=args.profile, tier=args.tier, approval_reference=args.approval_reference, approved_at=args.approved_at, approved_by_role=args.approved_by_role, policy=policy)
        dump(args.output, doc); print(f"PASS: approved drill campaign written to {args.output}"); return 0
    if args.action == "certify":
        evidence = load(args.evidence); sig = verify_signature(evidence, args.signature, args.public_key)
        doc = certify_recovery(current_evidence=evidence, signature_verification=sig, baseline=load(args.baseline), campaign=load(args.campaign))
        dump(args.output, doc); print(f"{doc['decision']}: resilience certification written to {args.output}")
        return 0 if (doc["decision"] == "GO" or not args.require_go) else 2
    doc = load(args.file)
    if args.kind == "baseline": valid, errors = validate_baseline(doc)
    elif args.kind == "campaign": valid, errors = validate_campaign(doc)
    else: valid, errors = validate_certification(doc, require_go=args.require_go)
    print(json.dumps({"valid": valid, "errors": errors}, sort_keys=True)); return 0 if valid else 2

if __name__ == "__main__": raise SystemExit(main())
