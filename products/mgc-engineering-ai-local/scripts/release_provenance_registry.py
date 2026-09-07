#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.core.release_provenance import (  # noqa: E402
    ProvenanceError,
    build_audit_report,
    compare_releases,
    initialize_registry,
    register_public_key,
    register_signed_artifact,
    registry_summary,
    revoke_public_key,
    verify_registry,
)
from app.core.release_provenance_governance import (  # noqa: E402
    create_checkpoint,
    export_auditor_bundle,
    place_legal_hold,
    record_external_anchor,
    release_legal_hold,
    retention_status,
    seal_latest_checkpoint_to_worm,
    set_retention_policy,
    verify_auditor_bundle,
    verify_governance,
)


def dump(obj: object) -> None:
    print(json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True))


def main() -> int:
    ap = argparse.ArgumentParser(description="MGC v6.3.34 release provenance governance, trust anchoring & retention")
    ap.add_argument("--registry", required=True, help="Registry root; keep on controlled local/shared release-evidence storage")
    sub = ap.add_subparsers(dest="command", required=True)

    p = sub.add_parser("init")
    p.add_argument("--registry-id", required=True)
    p.add_argument("--actor", default="release-engineering")

    p = sub.add_parser("key-register")
    p.add_argument("--key-id", required=True)
    p.add_argument("--public-key", required=True)
    p.add_argument("--actor", default="release-engineering")
    p.add_argument("--valid-days", type=int, default=180)
    p.add_argument("--rotation-warning-days", type=int, default=30)
    p.add_argument("--not-before", default="")
    p.add_argument("--expires-at", default="")

    p = sub.add_parser("key-revoke")
    p.add_argument("--key-id", required=True)
    p.add_argument("--reason", required=True)
    p.add_argument("--actor", default="release-engineering")

    for name, kind in [
        ("acceptance-register", "acceptance"),
        ("baseline-register", "baseline"),
        ("load-register", "load"),
        ("failover-register", "failover"),
    ]:
        p = sub.add_parser(name)
        p.set_defaults(kind=kind)
        p.add_argument("--document", required=True)
        p.add_argument("--signature", default="")
        p.add_argument("--key-id", default="")
        p.add_argument("--actor", default="release-engineering")

    sub.add_parser("verify")
    sub.add_parser("summary")

    p = sub.add_parser("compare")
    p.add_argument("--profile", required=True, choices=["15", "30", "100"])
    p.add_argument("--release-a", required=True)
    p.add_argument("--release-b", required=True)

    p = sub.add_parser("audit")
    p.add_argument("--output", default="")

    p = sub.add_parser("retention-set")
    p.add_argument("--policy-id", required=True)
    p.add_argument("--retention-json", default="{}", help="JSON object overriding retention days by evidence kind")
    p.add_argument("--actor", default="release-governance")

    p = sub.add_parser("hold-place")
    p.add_argument("--hold-id", required=True)
    p.add_argument("--reason", required=True)
    p.add_argument("--release", default="")
    p.add_argument("--object-sha256", default="")
    p.add_argument("--actor", default="release-governance")

    p = sub.add_parser("hold-release")
    p.add_argument("--hold-id", required=True)
    p.add_argument("--reason", required=True)
    p.add_argument("--actor", default="release-governance")

    p = sub.add_parser("checkpoint")
    p.add_argument("--actor", default="release-governance")

    p = sub.add_parser("anchor")
    p.add_argument("--adapter-command-json", required=True)
    p.add_argument("--provider", default="external")
    p.add_argument("--actor", default="release-governance")

    p = sub.add_parser("worm-seal")
    p.add_argument("--adapter-command-json", required=True)
    p.add_argument("--provider", default="external-worm")
    p.add_argument("--retain-days", type=int, default=3650)
    p.add_argument("--lock-mode", choices=["COMPLIANCE", "GOVERNANCE"], default="COMPLIANCE")
    p.add_argument("--actor", default="release-governance")

    p = sub.add_parser("governance")
    p.add_argument("--require-external-anchor", action="store_true")
    p.add_argument("--require-worm-receipt", action="store_true")
    p.add_argument("--anchor-max-age-hours", type=int, default=24)

    p = sub.add_parser("auditor-export")
    p.add_argument("--output", required=True)

    p = sub.add_parser("auditor-verify")
    p.add_argument("--bundle", required=True)

    args = ap.parse_args()
    registry = Path(args.registry)
    try:
        if args.command == "init":
            dump(initialize_registry(registry, registry_id=args.registry_id, actor=args.actor)); return 0
        if args.command == "key-register":
            dump(register_public_key(registry, key_id=args.key_id, public_key=Path(args.public_key), actor=args.actor, valid_days=args.valid_days, rotation_warning_days=args.rotation_warning_days, not_before=args.not_before or None, expires_at=args.expires_at or None)); return 0
        if args.command == "key-revoke":
            dump(revoke_public_key(registry, key_id=args.key_id, reason=args.reason, actor=args.actor)); return 0
        if args.command.endswith("-register"):
            sig = Path(args.signature) if args.signature else None
            key_id = args.key_id or None
            event = register_signed_artifact(registry, kind=args.kind, document_path=Path(args.document), signature_path=sig, key_id=key_id, actor=args.actor)
            dump(event); return 0
        if args.command == "verify":
            result = verify_registry(registry); dump(result); return 0 if result["status"] == "PASS" else 2
        if args.command == "summary":
            result = registry_summary(registry); dump(result); return 0 if result.get("status") == "PASS" else 2
        if args.command == "compare":
            dump(compare_releases(registry, release_a=args.release_a, release_b=args.release_b, profile=args.profile)); return 0
        if args.command == "audit":
            report = build_audit_report(registry)
            if args.output:
                out = Path(args.output); out.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
                dump({"status": report["registry_verification"]["status"], "output": str(out), "tip_sha256": report["registry_verification"]["tip_sha256"]})
            else:
                dump(report)
            return 0 if report["registry_verification"]["status"] == "PASS" else 2
        if args.command == "retention-set":
            overrides = json.loads(args.retention_json)
            if not isinstance(overrides, dict):
                raise ProvenanceError("retention-json must be a JSON object")
            dump(set_retention_policy(registry, policy_id=args.policy_id, retention_days=overrides, actor=args.actor)); return 0
        if args.command == "hold-place":
            dump(place_legal_hold(registry, hold_id=args.hold_id, reason=args.reason, release=args.release or None, object_sha256=args.object_sha256 or None, actor=args.actor)); return 0
        if args.command == "hold-release":
            dump(release_legal_hold(registry, hold_id=args.hold_id, reason=args.reason, actor=args.actor)); return 0
        if args.command == "checkpoint":
            dump(create_checkpoint(registry, actor=args.actor)); return 0
        if args.command == "anchor":
            dump(record_external_anchor(registry, command_json=args.adapter_command_json, provider=args.provider, actor=args.actor)); return 0
        if args.command == "worm-seal":
            dump(seal_latest_checkpoint_to_worm(registry, command_json=args.adapter_command_json, retain_days=args.retain_days, lock_mode=args.lock_mode, provider=args.provider, actor=args.actor)); return 0
        if args.command == "governance":
            result = verify_governance(registry, require_external_anchor=args.require_external_anchor, require_worm_receipt=args.require_worm_receipt, anchor_max_age_hours=args.anchor_max_age_hours); dump(result); return 0 if result["status"] in {"PASS", "CONDITIONAL"} else 2
        if args.command == "auditor-export":
            dump(export_auditor_bundle(registry, output=args.output)); return 0
        if args.command == "auditor-verify":
            result = verify_auditor_bundle(args.bundle); dump(result); return 0 if result["status"] == "PASS" else 2
    except (ProvenanceError, OSError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
