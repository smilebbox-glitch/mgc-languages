#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> int:
    ap = argparse.ArgumentParser(description="Fail closed unless a production certification report is technical GO.")
    ap.add_argument("--report", required=True)
    ap.add_argument("--confirm", default="")
    args = ap.parse_args()
    report = json.loads(Path(args.report).read_text(encoding="utf-8"))
    if report.get("schema") != "mgc-production-certification-v1":
        print("NO_GO: unsupported production certification report schema")
        return 2
    if report.get("decision") != "GO":
        print(f"NO_GO: certification decision is {report.get('decision')}")
        return 2
    if report.get("production_authorized") is True:
        print("NO_GO: technical report must not self-authorize production")
        return 2
    if args.confirm != "APPROVED_CHANGE_WINDOW":
        print("NO_GO: exact --confirm APPROVED_CHANGE_WINDOW is required after human approval")
        return 2
    print("PASS: technical GO report accepted for an explicitly approved change window")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
