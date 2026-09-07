#!/usr/bin/env python3
"""MGC Engineering AI Local operations CLI.

v6.3.34 consolidates operator-facing entry points while preserving the proven
implementation scripts underneath.  This module never executes user input via
an implicit shell.  Destructive operations require exact confirmation tokens.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable, Sequence

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))
from app.core.runtime_contract import APP_VERSION, SCHEMA_VERSION  # noqa: E402

CLI_SCHEMA = "mgc.operations-cli.v1"


@dataclass(frozen=True)
class StepResult:
    name: str
    argv: list[str]
    status: str
    returncode: int
    stdout: str = ""
    stderr: str = ""


def _safe_env(extra: dict[str, str] | None = None) -> dict[str, str]:
    env = os.environ.copy()
    if extra:
        env.update({str(k): str(v) for k, v in extra.items()})
    return env


def run_step(
    name: str,
    argv: Sequence[str],
    *,
    dry_run: bool = False,
    capture: bool = True,
    env: dict[str, str] | None = None,
) -> StepResult:
    cmd = [str(x) for x in argv]
    if dry_run:
        return StepResult(name=name, argv=cmd, status="DRY_RUN", returncode=0)
    proc = subprocess.run(
        cmd,
        cwd=ROOT,
        env=_safe_env(env),
        shell=False,
        text=True,
        capture_output=capture,
    )
    return StepResult(
        name=name,
        argv=cmd,
        status="PASS" if proc.returncode == 0 else "FAIL",
        returncode=proc.returncode,
        stdout=(proc.stdout or "").strip() if capture else "",
        stderr=(proc.stderr or "").strip() if capture else "",
    )


def _emit(results: Iterable[StepResult], *, as_json: bool, extra: dict | None = None) -> int:
    rows = list(results)
    rc = 0 if all(r.returncode == 0 for r in rows) else 2
    if as_json:
        payload = {
            "schema": CLI_SCHEMA,
            "version": APP_VERSION,
            "schema_version": SCHEMA_VERSION,
            "status": "PASS" if rc == 0 else "FAIL",
            "steps": [asdict(r) for r in rows],
        }
        if extra:
            payload.update(extra)
        print(json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2))
    else:
        if extra:
            for key, value in extra.items():
                if key not in {"details"}:
                    print(f"{key}: {value}")
        for r in rows:
            print(f"[{r.status}] {r.name}")
            if r.stdout:
                print(r.stdout)
            if r.stderr:
                print(r.stderr, file=sys.stderr)
    return rc


def _require(value: str, expected: str, operation: str) -> None:
    if value != expected:
        raise SystemExit(f"Refusing {operation}: pass --confirm {expected}")


VERIFY_SCOPES: dict[str, list[tuple[str, list[str]]]] = {
    "quick": [
        ("build", [sys.executable, "scripts/build_preflight.py"]),
        ("api-access", [sys.executable, "scripts/api_access_preflight.py"]),
        ("operational-resilience", [sys.executable, "scripts/operational_resilience_preflight.py"]),
        ("provenance", [sys.executable, "scripts/release_provenance_preflight.py"]),
    ],
    "security": [
        ("docker-security", [sys.executable, "scripts/docker_security_preflight.py"]),
        ("compose-security", [sys.executable, "scripts/compose_security_preflight.py"]),
        ("api-access", [sys.executable, "scripts/api_access_preflight.py"]),
        ("enterprise-security", [sys.executable, "scripts/enterprise_security_preflight.py"]),
        ("secret-scan", [sys.executable, "scripts/secret_scan.py"]),
    ],
    "architecture": [
        ("architecture", [sys.executable, "scripts/architecture_simplification_preflight.py"]),
        ("contexts", [sys.executable, "scripts/context_router_preflight.py"]),
        ("ports-adapters", [sys.executable, "scripts/ports_adapters_preflight.py"]),
        ("domain-integrity", [sys.executable, "scripts/domain_integrity_preflight.py"]),
    ],
    "release": [
        ("rolling", [sys.executable, "scripts/rolling_upgrade_preflight.py"]),
        ("blue-green", [sys.executable, "scripts/blue_green_cutover_preflight.py"]),
        ("ha", [sys.executable, "scripts/ha_failover_preflight.py"]),
        ("authoritative-ha", [sys.executable, "scripts/db_evidence_ha_preflight.py"]),
        ("multi-host", [sys.executable, "scripts/multihost_topology_preflight.py"]),
        ("production-certification", [sys.executable, "scripts/production_certification_preflight.py"]),
        ("load-certification", [sys.executable, "scripts/production_load_certification_preflight.py"]),
        ("release-acceptance", [sys.executable, "scripts/release_acceptance_preflight.py"]),
        ("release-provenance", [sys.executable, "scripts/release_provenance_preflight.py"]),
        ("external-trust", [sys.executable, "scripts/external_trust_retention_preflight.py"]),
        ("integration-certification", [sys.executable, "scripts/integration_certification_preflight.py"]),
        ("integration-runtime-assurance", [sys.executable, "scripts/integration_runtime_assurance_preflight.py"]),
        ("target-host-assurance", [sys.executable, "scripts/target_host_assurance_preflight.py"]),
        ("incident-evidence", [sys.executable, "scripts/incident_evidence_preflight.py"]),
        ("resilience-drill", [sys.executable, "scripts/resilience_drill_preflight.py"]),
        ("resilience-certification", [sys.executable, "scripts/resilience_certification_preflight.py"]),
        ("pilot-readiness", [sys.executable, "scripts/pilot_readiness_preflight.py"]),
        ("multi-vehicle-applicability", [sys.executable, "scripts/multi_vehicle_applicability_preflight.py"]),
    ],
}
VERIFY_SCOPES["full"] = VERIFY_SCOPES["security"] + VERIFY_SCOPES["architecture"] + VERIFY_SCOPES["release"]


def cmd_status(args: argparse.Namespace) -> int:
    docker = shutil.which("docker")
    extra = {
        "source_version": APP_VERSION,
        "schema_version": SCHEMA_VERSION,
        "docker_cli": bool(docker),
        "runtime_checked": bool(docker and not args.offline),
    }
    rows: list[StepResult] = []
    if docker and not args.offline:
        rows.append(run_step("compose-services", [docker, "compose", "ps", "--format", "json"], capture=True))
    elif args.require_runtime:
        rows.append(StepResult("docker-runtime", ["docker", "compose", "ps"], "FAIL", 2, stderr="docker CLI unavailable"))
    return _emit(rows, as_json=args.json, extra=extra)


def cmd_verify(args: argparse.Namespace) -> int:
    rows: list[StepResult] = []
    for name, argv in VERIFY_SCOPES[args.scope]:
        row = run_step(name, argv, dry_run=args.dry_run, capture=True)
        rows.append(row)
        if row.returncode != 0 and args.fail_fast:
            break
    return _emit(rows, as_json=args.json, extra={"scope": args.scope})


def cmd_deploy(args: argparse.Namespace) -> int:
    _require(args.confirm, "DEPLOY", "deployment")
    if args.target_version != APP_VERSION:
        raise SystemExit(f"Refusing deployment target {args.target_version}: this package certifies {APP_VERSION}")
    rows: list[StepResult] = []
    if not args.host_assurance and not args.dry_run:
        raise SystemExit("Refusing deployment: --host-assurance PASS report is required by v6.3.34")
    resilience_required = {
        "--resilience-certification": args.resilience_certification,
        "--resilience-evidence": args.resilience_evidence,
        "--resilience-evidence-signature": args.resilience_evidence_signature,
        "--resilience-public-key": args.resilience_public_key,
        "--resilience-baseline": args.resilience_baseline,
        "--resilience-campaign": args.resilience_campaign,
    }
    missing_resilience = [name for name, value in resilience_required.items() if not value]
    if missing_resilience and not args.dry_run:
        raise SystemExit("Refusing deployment: complete resilience source bundle is required by v6.3.34: " + ", ".join(missing_resilience))
    if args.host_assurance:
        guard = [sys.executable, "scripts/target_host_deployment_guard.py", "--report", args.host_assurance]
        if args.host_assurance_signature:
            guard += ["--signature", args.host_assurance_signature]
        if args.host_assurance_public_key:
            guard += ["--public-key", args.host_assurance_public_key]
        if args.require_signed_host_assurance:
            guard.append("--require-signature")
        gate = run_step("target-host-assurance-gate", guard, dry_run=False, capture=True)
        rows.append(gate)
        if gate.returncode != 0:
            return _emit(rows, as_json=args.json, extra={"mode": args.mode, "target_version": APP_VERSION})
    if not missing_resilience:
        resilience_guard = [
            sys.executable, "scripts/resilience_release_guard.py",
            "--report", args.resilience_certification,
            "--evidence", args.resilience_evidence,
            "--signature", args.resilience_evidence_signature,
            "--public-key", args.resilience_public_key,
            "--baseline", args.resilience_baseline,
            "--campaign", args.resilience_campaign,
        ]
        resilience_gate = run_step("resilience-certification-gate", resilience_guard, dry_run=False, capture=True)
        rows.append(resilience_gate)
        if resilience_gate.returncode != 0:
            return _emit(rows, as_json=args.json, extra={"mode": args.mode, "target_version": APP_VERSION})
    env = {
        "MGC_TARGET_VERSION": APP_VERSION,
        "MGC_CANDIDATE_VERSION": APP_VERSION,
        "MGC_TARGET_HOST_ASSURANCE_REPORT": args.host_assurance,
        "MGC_TARGET_HOST_ASSURANCE_SIGNATURE": args.host_assurance_signature,
        "MGC_TARGET_HOST_ASSURANCE_PUBLIC_KEY": args.host_assurance_public_key,
        "MGC_REQUIRE_SIGNED_HOST_ASSURANCE": "true" if args.require_signed_host_assurance else "false",
        "MGC_RESILIENCE_CERTIFICATION_REPORT": args.resilience_certification,
        "MGC_RESILIENCE_EVIDENCE": args.resilience_evidence,
        "MGC_RESILIENCE_EVIDENCE_SIGNATURE": args.resilience_evidence_signature,
        "MGC_RESILIENCE_PUBLIC_KEY": args.resilience_public_key,
        "MGC_RESILIENCE_BASELINE": args.resilience_baseline,
        "MGC_RESILIENCE_CAMPAIGN": args.resilience_campaign,
    }
    mapping = {
        "rolling": [str(ROOT / "scripts/rolling_upgrade.sh")],
        "blue-green": [str(ROOT / "scripts/blue_green_cutover.sh")],
        "blue-green-finalize": [str(ROOT / "scripts/blue_green_finalize.sh")],
    }
    row = run_step(f"deploy-{args.mode}", mapping[args.mode], dry_run=args.dry_run, capture=not args.stream, env=env)
    rows.append(row)
    return _emit(rows, as_json=args.json, extra={"mode": args.mode, "target_version": APP_VERSION})


def cmd_rollback(args: argparse.Namespace) -> int:
    _require(args.confirm, "ROLLBACK", "rollback")
    if args.mode != "blue-green":
        raise SystemExit("Only guarded blue-green rollback is certified by v6.3.34")
    row = run_step("rollback-blue-green", [str(ROOT / "scripts/blue_green_rollback.sh")], dry_run=args.dry_run, capture=not args.stream)
    return _emit([row], as_json=args.json, extra={"mode": args.mode})


def cmd_backup(args: argparse.Namespace) -> int:
    argv = [str(ROOT / "scripts/backup_core.sh")]
    if args.destination:
        argv.append(args.destination)
    row = run_step("backup", argv, dry_run=args.dry_run, capture=not args.stream)
    return _emit([row], as_json=args.json)


def cmd_restore(args: argparse.Namespace) -> int:
    _require(args.confirm, "RESTORE", "restore")
    backup = Path(args.backup)
    if not args.dry_run and not backup.exists():
        raise SystemExit(f"Backup path does not exist: {backup}")
    row = run_step(
        "restore",
        [str(ROOT / "scripts/restore_core.sh"), str(backup)],
        dry_run=args.dry_run,
        capture=not args.stream,
        env={"MGC_RESTORE_CONFIRM": "RESTORE"},
    )
    return _emit([row], as_json=args.json)


def cmd_certify(args: argparse.Namespace) -> int:
    if args.certify_action == "preflight":
        scopes = {
            "production": ["production-certification"],
            "load": ["load-certification"],
            "release": ["release-acceptance"],
            "integration": ["integration-certification", "integration-runtime-assurance"],
            "target-host": ["target-host-assurance"],
            "resilience": ["resilience-drill", "resilience-certification"],
            "all": ["production-certification", "load-certification", "release-acceptance", "integration-certification", "integration-runtime-assurance", "target-host-assurance", "incident-evidence", "resilience-drill", "resilience-certification"],
        }
        release_map = dict(VERIFY_SCOPES["release"])
        rows = [run_step(name, release_map[name], dry_run=args.dry_run, capture=True) for name in scopes[args.scope]]
        return _emit(rows, as_json=args.json, extra={"scope": args.scope})
    if args.certify_action == "topology":
        row = run_step("topology-certify", [sys.executable, "scripts/topology_certify.py", "--profile", args.profile, "--inventory", args.inventory], dry_run=args.dry_run)
        return _emit([row], as_json=args.json)
    if args.certify_action == "production":
        argv = [sys.executable, "scripts/production_certify.py", "--profile", args.profile, "--topology", args.topology, "--evidence", args.evidence, "--output", args.output]
        if args.load_evidence:
            argv += ["--load-evidence", args.load_evidence, "--load-signature", args.load_signature, "--load-public-key", args.load_public_key]
        if args.require_go:
            argv.append("--require-go")
        row = run_step("production-certify", argv, dry_run=args.dry_run)
        return _emit([row], as_json=args.json)
    if args.certify_action == "load":
        _require(args.confirm, "LOAD", "live load certification")
        argv = [sys.executable, "scripts/production_load_certify.py", "--profile", args.profile, "--base-url", args.base_url, "--project-code", args.project_code, "--part-number", args.part_number, "--output", args.output]
        if args.signing_key:
            argv += ["--signing-key", args.signing_key]
        row = run_step("production-load-certify", argv, dry_run=args.dry_run, env={"MGC_LOAD_CERTIFY_CONFIRM": "YES"})
        return _emit([row], as_json=args.json)
    if args.certify_action == "target-host":
        argv = [sys.executable, "scripts/target_host_certify.py", "--profile", args.profile, "--topology", args.topology, "--output", args.output]
        for evidence in args.evidence:
            argv += ["--evidence", evidence]
        if args.signing_key:
            argv += ["--signing-key", args.signing_key]
        if args.signature_output:
            argv += ["--signature-output", args.signature_output]
        if args.require_pass:
            argv.append("--require-pass")
        row = run_step("target-host-certify", argv, dry_run=args.dry_run)
        return _emit([row], as_json=args.json, extra={"profile": args.profile, "nodes": len(args.evidence)})
    if args.certify_action == "integration":
        argv = [sys.executable, "scripts/integration_certify.py", "--contract", args.contract, "--sample-limit", str(args.sample_limit)]
        if args.live:
            argv.append("--live")
        if args.require_pass:
            argv.append("--require-pass")
        if args.output:
            argv += ["--output", args.output]
        row = run_step("integration-certify", argv, dry_run=args.dry_run)
        return _emit([row], as_json=args.json, extra={"contract": Path(args.contract).name, "live": bool(args.live)})
    if args.certify_action == "resilience":
        argv = [sys.executable, "scripts/resilience_certify.py", "certify", "--evidence", args.evidence, "--signature", args.signature, "--public-key", args.public_key, "--baseline", args.baseline, "--campaign", args.campaign, "--output", args.output]
        if args.require_go:
            argv.append("--require-go")
        row = run_step("resilience-certify", argv, dry_run=args.dry_run)
        return _emit([row], as_json=args.json, extra={"baseline": Path(args.baseline).name, "campaign": Path(args.campaign).name})
    raise SystemExit("Unsupported certification action")


def cmd_provenance(args: argparse.Namespace) -> int:
    forwarded = list(args.provenance_args)
    if forwarded and forwarded[0] == "--":
        forwarded = forwarded[1:]
    if not forwarded:
        raise SystemExit("Provide a provenance action, e.g. verify, summary, governance, audit")
    row = run_step(
        "provenance",
        [sys.executable, "scripts/release_provenance_registry.py", "--registry", args.registry, *forwarded],
        dry_run=args.dry_run,
        capture=True,
    )
    return _emit([row], as_json=args.json)


def cmd_diagnose(args: argparse.Namespace) -> int:
    rows: list[StepResult] = []
    for name, argv in VERIFY_SCOPES["quick"]:
        rows.append(run_step(name, argv, dry_run=args.dry_run, capture=True))
    runtime_service_count = None
    if args.runtime:
        docker = shutil.which("docker")
        if docker:
            row = run_step("compose-ps", [docker, "compose", "ps", "--services", "--status", "running"], dry_run=args.dry_run, capture=True)
            rows.append(row)
            if row.returncode == 0 and row.status != "DRY_RUN":
                runtime_service_count = len([line for line in row.stdout.splitlines() if line.strip()])
        else:
            rows.append(StepResult("compose-ps", ["docker", "compose", "ps"], "FAIL", 2, stderr="docker CLI unavailable"))
    rc = 0 if all(r.returncode == 0 for r in rows) else 2
    report = {
        "schema": CLI_SCHEMA,
        "version": APP_VERSION,
        "schema_version": SCHEMA_VERSION,
        "status": "PASS" if rc == 0 else "FAIL",
        "diagnostic_scope": "quick+runtime" if args.runtime else "quick-static",
        "runtime_service_count": runtime_service_count,
        "contains_command_output": False,
        "steps": [{"name": r.name, "status": r.status, "returncode": r.returncode} for r in rows],
    }
    if args.json:
        print(json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2))
    else:
        for row in report["steps"]:
            print(f"[{row['status']}] {row['name']}")
    if args.output:
        Path(args.output).write_text(json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
        if not args.json:
            print(f"Diagnostic report written: {args.output}")
    return rc



def cmd_drill(args: argparse.Namespace) -> int:
    argv = [sys.executable, "scripts/resilience_drill.py", args.drill_action]
    if args.drill_action == "catalog":
        if args.output: argv += ["--output", args.output]
    elif args.drill_action == "plan":
        for scenario in args.scenario: argv += ["--scenario", scenario]
        argv += ["--tier", args.tier, "--profile", args.profile, "--max-fault-seconds", str(args.max_fault_seconds), "--output", args.output]
        if args.maintenance_window_ref: argv += ["--maintenance-window-ref", args.maintenance_window_ref]
        if args.allow_production_dependency_drill: argv.append("--allow-production-dependency-drill")
    elif args.drill_action == "run":
        argv += ["--plan", args.plan, "--output", args.output]
        if args.confirm: argv += ["--confirm", args.confirm]
        if args.simulate: argv.append("--simulate")
    elif args.drill_action == "bind":
        argv += ["--evidence", args.evidence, "--incident-evidence", args.incident_evidence, "--output", args.output]
    elif args.drill_action == "validate":
        argv += ["--file", args.file, "--kind", args.kind]
    row = run_step(f"resilience-drill-{args.drill_action}", argv, dry_run=args.dry_run, capture=True)
    return _emit([row], as_json=args.json, extra={"action": args.drill_action})

def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(prog="mgcctl", description=f"MGC Engineering AI Local operations CLI v{APP_VERSION}")
    ap.add_argument("--version", action="version", version=f"mgcctl {APP_VERSION} (schema {SCHEMA_VERSION})")
    sub = ap.add_subparsers(dest="command", required=True)

    p = sub.add_parser("status", help="Show source/runtime status without exposing secrets")
    p.add_argument("--offline", action="store_true")
    p.add_argument("--require-runtime", action="store_true")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_status)

    p = sub.add_parser("verify", help="Run consolidated preflight groups")
    p.add_argument("--scope", choices=sorted(VERIFY_SCOPES), default="quick")
    p.add_argument("--fail-fast", action="store_true")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_verify)

    p = sub.add_parser("deploy", help="Run a certified deployment workflow")
    p.add_argument("--mode", choices=["rolling", "blue-green", "blue-green-finalize"], default="rolling")
    p.add_argument("--target-version", default=APP_VERSION)
    p.add_argument("--confirm", default="")
    p.add_argument("--host-assurance", default="")
    p.add_argument("--host-assurance-signature", default="")
    p.add_argument("--host-assurance-public-key", default="")
    p.add_argument("--require-signed-host-assurance", action="store_true")
    p.add_argument("--resilience-certification", default="")
    p.add_argument("--resilience-evidence", default="")
    p.add_argument("--resilience-evidence-signature", default="")
    p.add_argument("--resilience-public-key", default="")
    p.add_argument("--resilience-baseline", default="")
    p.add_argument("--resilience-campaign", default="")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--stream", action="store_true")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_deploy)

    p = sub.add_parser("rollback", help="Run a guarded rollback workflow")
    p.add_argument("--mode", choices=["blue-green"], default="blue-green")
    p.add_argument("--confirm", default="")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--stream", action="store_true")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_rollback)

    p = sub.add_parser("backup", help="Create an authoritative consistency-verified backup")
    p.add_argument("--destination", default="")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--stream", action="store_true")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_backup)

    p = sub.add_parser("restore", help="Restore an authoritative backup")
    p.add_argument("--backup", required=True)
    p.add_argument("--confirm", default="")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--stream", action="store_true")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_restore)

    p = sub.add_parser("certify", help="Run topology/load/production certification workflows")
    cert = p.add_subparsers(dest="certify_action", required=True)
    q = cert.add_parser("preflight")
    q.add_argument("--scope", choices=["production", "load", "release", "integration", "target-host", "resilience", "all"], default="all")
    q.add_argument("--dry-run", action="store_true")
    q.add_argument("--json", action="store_true")
    q.set_defaults(func=cmd_certify)
    q = cert.add_parser("topology")
    q.add_argument("--profile", choices=["15", "30", "100"], required=True)
    q.add_argument("--inventory", required=True)
    q.add_argument("--dry-run", action="store_true")
    q.add_argument("--json", action="store_true")
    q.set_defaults(func=cmd_certify)
    q = cert.add_parser("production")
    q.add_argument("--profile", choices=["15", "30", "100"], required=True)
    q.add_argument("--topology", required=True)
    q.add_argument("--evidence", required=True)
    q.add_argument("--load-evidence", default="")
    q.add_argument("--load-signature", default="")
    q.add_argument("--load-public-key", default="")
    q.add_argument("--output", default="production-certification.json")
    q.add_argument("--require-go", action="store_true")
    q.add_argument("--dry-run", action="store_true")
    q.add_argument("--json", action="store_true")
    q.set_defaults(func=cmd_certify)
    q = cert.add_parser("load")
    q.add_argument("--profile", choices=["15", "30", "100"], required=True)
    q.add_argument("--base-url", required=True)
    q.add_argument("--project-code", required=True)
    q.add_argument("--part-number", required=True)
    q.add_argument("--output", required=True)
    q.add_argument("--signing-key", default="")
    q.add_argument("--confirm", default="")
    q.add_argument("--dry-run", action="store_true")
    q.add_argument("--json", action="store_true")
    q.set_defaults(func=cmd_certify)
    q = cert.add_parser("target-host")
    q.add_argument("--profile", choices=["15", "30", "100"], required=True)
    q.add_argument("--topology", required=True)
    q.add_argument("--evidence", action="append", required=True)
    q.add_argument("--output", required=True)
    q.add_argument("--signing-key", default="")
    q.add_argument("--signature-output", default="")
    q.add_argument("--require-pass", action="store_true")
    q.add_argument("--dry-run", action="store_true")
    q.add_argument("--json", action="store_true")
    q.set_defaults(func=cmd_certify)
    q = cert.add_parser("integration")
    q.add_argument("--contract", required=True)
    q.add_argument("--live", action="store_true")
    q.add_argument("--sample-limit", type=int, default=20)
    q.add_argument("--output", default="")
    q.add_argument("--require-pass", action="store_true")
    q.add_argument("--dry-run", action="store_true")
    q.add_argument("--json", action="store_true")
    q.set_defaults(func=cmd_certify)
    q = cert.add_parser("resilience")
    q.add_argument("--evidence", required=True)
    q.add_argument("--signature", required=True)
    q.add_argument("--public-key", required=True)
    q.add_argument("--baseline", required=True)
    q.add_argument("--campaign", required=True)
    q.add_argument("--output", required=True)
    q.add_argument("--require-go", action="store_true")
    q.add_argument("--dry-run", action="store_true")
    q.add_argument("--json", action="store_true")
    q.set_defaults(func=cmd_certify)

    p = sub.add_parser("provenance", help="Operate the release provenance registry")
    p.add_argument("--registry", required=True)
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--json", action="store_true")
    p.add_argument("provenance_args", nargs=argparse.REMAINDER)
    p.set_defaults(func=cmd_provenance)


    p = sub.add_parser("drill", help="Plan, run or validate bounded resilience drills")
    drill = p.add_subparsers(dest="drill_action", required=True)
    q = drill.add_parser("catalog")
    q.add_argument("--output", default=""); q.add_argument("--dry-run", action="store_true"); q.add_argument("--json", action="store_true"); q.set_defaults(func=cmd_drill)
    q = drill.add_parser("plan")
    q.add_argument("--scenario", action="append", required=True, choices=["api_instance_loss","worker_cpu_loss","redis_brownout","qdrant_brownout","integration_gateway_timeout"])
    q.add_argument("--tier", choices=["staging","production"], default="staging")
    q.add_argument("--profile", choices=["core","ai","advanced"], default="core")
    q.add_argument("--maintenance-window-ref", default=""); q.add_argument("--allow-production-dependency-drill", action="store_true")
    q.add_argument("--max-fault-seconds", type=int, default=30); q.add_argument("--output", required=True); q.add_argument("--dry-run", action="store_true"); q.add_argument("--json", action="store_true"); q.set_defaults(func=cmd_drill)
    q = drill.add_parser("run")
    q.add_argument("--plan", required=True); q.add_argument("--output", required=True); q.add_argument("--confirm", default=""); q.add_argument("--simulate", action="store_true"); q.add_argument("--dry-run", action="store_true"); q.add_argument("--json", action="store_true"); q.set_defaults(func=cmd_drill)
    q = drill.add_parser("bind")
    q.add_argument("--evidence", required=True); q.add_argument("--incident-evidence", required=True); q.add_argument("--output", required=True); q.add_argument("--dry-run", action="store_true"); q.add_argument("--json", action="store_true"); q.set_defaults(func=cmd_drill)
    q = drill.add_parser("validate")
    q.add_argument("--file", required=True); q.add_argument("--kind", choices=["plan","evidence"], required=True); q.add_argument("--dry-run", action="store_true"); q.add_argument("--json", action="store_true"); q.set_defaults(func=cmd_drill)

    p = sub.add_parser("diagnose", help="Create a privacy-safe consolidated diagnostic report")
    p.add_argument("--runtime", action="store_true")
    p.add_argument("--output", default="")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_diagnose)
    return ap


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
