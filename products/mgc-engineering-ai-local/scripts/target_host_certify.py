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
from app.core.target_host_assurance import build_report, canonical_payload_bytes  # noqa: E402


def sign_payload(payload: bytes, key: Path, signature: Path) -> None:
    with tempfile.NamedTemporaryFile(prefix="mgc-host-assurance-sign-", delete=False) as fh:
        fh.write(payload); temp = Path(fh.name)
    try:
        p = subprocess.run(["openssl", "dgst", "-sha256", "-sign", str(key), "-out", str(signature), str(temp)], capture_output=True, text=True)
        if p.returncode != 0:
            raise RuntimeError((p.stderr or p.stdout or "openssl sign failed").strip())
    finally:
        temp.unlink(missing_ok=True)


def main() -> int:
    ap = argparse.ArgumentParser(description="MGC target-host deployment assurance certification")
    ap.add_argument("--profile", choices=["15", "30", "100"], required=True)
    ap.add_argument("--topology", required=True)
    ap.add_argument("--evidence", action="append", required=True, help="Repeat once per target node")
    ap.add_argument("--output", required=True)
    ap.add_argument("--signing-key", default="")
    ap.add_argument("--signature-output", default="")
    ap.add_argument("--require-pass", action="store_true")
    args = ap.parse_args()
    try:
        topology = json.loads(Path(args.topology).read_text(encoding="utf-8"))
        docs = [json.loads(Path(x).read_text(encoding="utf-8")) for x in args.evidence]
        report = build_report(profile=args.profile, topology=topology, evidence_documents=docs)
        output = Path(args.output)
        if args.signing_key:
            signature = Path(args.signature_output) if args.signature_output else output.with_suffix(output.suffix + ".sig")
            sign_payload(canonical_payload_bytes(report), Path(args.signing_key), signature)
            report["integrity"]["detached_signature_path_hint"] = signature.name
        output.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    except (OSError, ValueError, json.JSONDecodeError, RuntimeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr); return 2
    print(json.dumps({"output": str(output), "decision": report["decision"], "nodes": len(report["node_results"]), "canonical_sha256": report["integrity"]["canonical_sha256"]}, ensure_ascii=False, indent=2))
    if args.require_pass and report["decision"] != "PASS":
        return 3
    return 0 if report["decision"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
