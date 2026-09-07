#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    ap = argparse.ArgumentParser(description="MGC v6.3.34 PLM/PDM/ERP/MES/QMS contract suite")
    ap.add_argument("--contracts-dir", default="ops/integrations/contracts")
    ap.add_argument("--output", default="")
    ap.add_argument("--require-pass", action="store_true")
    args = ap.parse_args()
    directory = ROOT / args.contracts_dir
    rows = []
    for path in sorted(directory.glob("*.json")):
        proc = subprocess.run(
            [sys.executable, str(ROOT / "scripts/integration_certify.py"), "--contract", str(path)],
            cwd=ROOT, text=True, capture_output=True, shell=False,
        )
        try:
            payload = json.loads(proc.stdout)
        except Exception:
            payload = {"decision": "NO_GO", "error": "invalid certification output"}
        rows.append({"contract": path.name, "decision": payload.get("decision"), "returncode": proc.returncode})
    decisions = [x["decision"] for x in rows]
    status = "PASS" if rows and all(x == "PASS" for x in decisions) else ("NO_GO" if any(x == "NO_GO" for x in decisions) else "CONDITIONAL")
    report = {
        "schema": "mgc.integration-contract-suite.v1",
        "release": "6.3.34",
        "status": status,
        "contracts": rows,
        "production_authorized": False,
    }
    text = json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    if args.output:
        Path(args.output).write_text(text, encoding="utf-8")
    print(text, end="")
    if args.require_pass and status != "PASS":
        return 2
    return 0 if status == "PASS" else 3


if __name__ == "__main__":
    raise SystemExit(main())
