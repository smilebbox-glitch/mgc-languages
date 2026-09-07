#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from app.core.resilience_drill import bind_incident_evidence, build_evidence, build_plan, catalog, validate_evidence, validate_plan  # noqa: E402


def dump(path: str, doc: dict) -> None:
    Path(path).write_text(json.dumps(doc, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")


def load(path: str) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def compose_argv(files: list[str], *args: str) -> list[str]:
    out = ["docker", "compose"]
    for f in files: out += ["-f", f]
    return [*out, *args]


def run(cmd: list[str], timeout: int = 30) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True, timeout=timeout, check=False)


def gateway_alive(files: list[str]) -> bool:
    cmd = compose_argv(files, "exec", "-T", "gateway", "wget", "-q", "-O", "-", "http://127.0.0.1:8080/api/v1/health/live")
    p = run(cmd, timeout=15)
    body = (p.stdout or "").replace(" ", "")
    return p.returncode == 0 and '"status":"alive"' in body


def service_running(files: list[str], service: str) -> bool:
    p = run(compose_argv(files, "ps", "--services", "--status", "running"), timeout=20)
    return p.returncode == 0 and service in {x.strip() for x in p.stdout.splitlines() if x.strip()}


def execute(plan: dict, *, confirm: str, simulate: bool = False) -> dict:
    ok, errors = validate_plan(plan)
    if not ok: raise SystemExit("Invalid drill plan: " + ", ".join(errors))
    if simulate:
        observations = [{"scenario": r["scenario"], "fault_injected": True, "continuity_passed": True, "recovery_attempted": True, "recovery_passed": True, "recovery_seconds": 0.0, "notes_code": "SIMULATED_ONLY"} for r in plan["scenarios"]]
        return build_evidence(plan, observations, live_execution=False)
    if confirm != "DRILL": raise SystemExit("Refusing live resilience drill: pass --confirm DRILL")
    if shutil.which("docker") is None: raise SystemExit("docker CLI required for live resilience drill")
    observations = []
    for row in plan["scenarios"]:
        files = list(row["compose_files"]); service = row["service"]
        if not service_running(files, service):
            observations.append({"scenario": row["scenario"], "notes_code": "BASELINE_SERVICE_NOT_RUNNING"})
            continue
        injected = False; recovery_attempted = False; continuity = False; recovered = False; recovery_seconds = None
        try:
            p = run(compose_argv(files, "stop", "-t", "10", service), timeout=30)
            injected = p.returncode == 0
            if injected:
                time.sleep(min(int(plan["max_fault_seconds"]), 5))
                continuity = gateway_alive(files)
        finally:
            recovery_attempted = True
            started = time.monotonic()
            p = run(compose_argv(files, "start", service), timeout=45)
            if p.returncode == 0:
                deadline = time.monotonic() + min(max(int(plan["max_fault_seconds"]), 10), 120)
                while time.monotonic() < deadline:
                    if service_running(files, service) and gateway_alive(files):
                        recovered = True; break
                    time.sleep(1)
            recovery_seconds = time.monotonic() - started
        observations.append({
            "scenario": row["scenario"], "fault_injected": injected, "continuity_passed": continuity,
            "recovery_attempted": recovery_attempted, "recovery_passed": recovered,
            "recovery_seconds": recovery_seconds, "notes_code": "LIVE_BOUNDED_COMPOSE_DRILL",
        })
    return build_evidence(plan, observations, live_execution=True)


def main() -> int:
    ap = argparse.ArgumentParser(description="MGC bounded resilience drill orchestration")
    sub = ap.add_subparsers(dest="action", required=True)
    p = sub.add_parser("catalog"); p.add_argument("--output", default="")
    p = sub.add_parser("plan")
    p.add_argument("--scenario", action="append", required=True, choices=sorted(catalog()["scenarios"]))
    p.add_argument("--tier", choices=["staging", "production"], default="staging")
    p.add_argument("--profile", choices=["core", "ai", "advanced"], default="core")
    p.add_argument("--maintenance-window-ref", default="")
    p.add_argument("--allow-production-dependency-drill", action="store_true")
    p.add_argument("--max-fault-seconds", type=int, default=30)
    p.add_argument("--output", required=True)
    p = sub.add_parser("run")
    p.add_argument("--plan", required=True); p.add_argument("--output", required=True)
    p.add_argument("--confirm", default=""); p.add_argument("--simulate", action="store_true")
    p = sub.add_parser("bind")
    p.add_argument("--evidence", required=True); p.add_argument("--incident-evidence", required=True); p.add_argument("--output", required=True)
    p = sub.add_parser("validate")
    p.add_argument("--file", required=True); p.add_argument("--kind", choices=["plan", "evidence"], required=True)
    args = ap.parse_args()
    if args.action == "catalog":
        doc = catalog(); print(json.dumps(doc, ensure_ascii=False, sort_keys=True, indent=2)) if not args.output else dump(args.output, doc); return 0
    if args.action == "plan":
        try:
            doc = build_plan(args.scenario, tier=args.tier, profile=args.profile, maintenance_window_ref=args.maintenance_window_ref, allow_production_dependency_drill=args.allow_production_dependency_drill, max_fault_seconds=args.max_fault_seconds)
        except ValueError as exc: raise SystemExit(str(exc))
        dump(args.output, doc); print(f"PASS: drill plan written to {args.output}"); return 0
    if args.action == "run":
        report = execute(load(args.plan), confirm=args.confirm, simulate=args.simulate); dump(args.output, report)
        print(f"{report['decision']}: resilience drill evidence written to {args.output}")
        return 0 if report["decision"] in {"PASS", "SIMULATED"} else 2
    if args.action == "bind":
        report = bind_incident_evidence(load(args.evidence), load(args.incident_evidence)); dump(args.output, report)
        print(f"PASS: incident evidence binding written to {args.output}"); return 0
    doc = load(args.file); valid, errors = (validate_plan(doc) if args.kind == "plan" else validate_evidence(doc))
    print(json.dumps({"valid": valid, "errors": errors}, sort_keys=True))
    return 0 if valid else 2

if __name__ == "__main__": raise SystemExit(main())
