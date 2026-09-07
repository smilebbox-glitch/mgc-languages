#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.db.models import ExternalSystem  # noqa: E402
from app.services.integration_certification import CERTIFICATION_SCHEMA, live_contract_probe, static_contract_report  # noqa: E402


def _load(path: Path) -> ExternalSystem:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("schema") != "mgc.integration-adapter-contract.v1":
        raise SystemExit(f"Unsupported integration contract schema: {payload.get('schema')!r}")
    system = payload.get("system") or {}
    code = str(system.get("code") or path.stem).strip().lower()
    return ExternalSystem(
        id=f"contract-{code}",
        code=code,
        name=str(system.get("name") or code),
        connector_type=str(system.get("connector_type") or ""),
        enabled=True,
        config_json=system.get("config") or {},
        secret_config_json=system.get("secret_refs") or {},
        acl_groups=["all"],
        source_domain=str(system.get("source_domain") or ""),
        contract_version=str(system.get("contract_version") or "mgc-integration-v1"),
        expected_freshness_minutes=system.get("expected_freshness_minutes"),
        required_fields=system.get("required_fields") or [],
    )


def main() -> int:
    ap = argparse.ArgumentParser(description="MGC v6.3.34 real integration contract certification")
    ap.add_argument("--contract", required=True)
    ap.add_argument("--live", action="store_true", help="Perform bounded read-only live probe")
    ap.add_argument("--sample-limit", type=int, default=20)
    ap.add_argument("--output", default="")
    ap.add_argument("--require-pass", action="store_true")
    args = ap.parse_args()

    system = _load(Path(args.contract))
    report = live_contract_probe(system, sample_limit=args.sample_limit) if args.live else static_contract_report(system)
    report["contract_file"] = Path(args.contract).name
    report["schema"] = CERTIFICATION_SCHEMA
    text = json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    if args.output:
        Path(args.output).write_text(text, encoding="utf-8")
    print(text, end="")
    if args.require_pass and report["decision"] != "PASS":
        return 2
    return 0 if report["decision"] == "PASS" else (3 if report["decision"] == "CONDITIONAL" else 2)


if __name__ == "__main__":
    raise SystemExit(main())
