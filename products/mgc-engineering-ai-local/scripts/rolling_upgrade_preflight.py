#!/usr/bin/env python3
"""Static fail-closed verification for v6.3.34 Rolling Upgrade & Deployment Safety."""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
checks: list[tuple[str, bool, str]] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    checks.append((name, bool(ok), detail))


def text(path: str) -> str:
    return (ROOT / path).read_text()

runtime = text("backend/app/core/runtime_contract.py")
config = text("backend/app/core/config.py")
deploy = text("backend/app/core/deployment_safety.py")
celery = text("backend/app/workers/celery_app.py")
guard = text("backend/app/workers/version_guard.py")
beat = text("backend/app/workers/singleton_beat.py")
drain = text("backend/app/workers/drain_cli.py")
health = text("backend/app/core/operational_health.py")
ops = text("backend/app/api/operations_routes.py")
compose = text("docker-compose.yml")
rolling = text("scripts/rolling_upgrade.sh") if (ROOT / "scripts/rolling_upgrade.sh").exists() else ""

check("app_version_6316", 'APP_VERSION = "6.3.34"' in runtime)
check("schema_unchanged_6313", 'SCHEMA_VERSION = "6.3.13"' in runtime)
check("max_patch_skew_one", "rolling_upgrade_max_patch_skew: int = 1" in config)
check("same_schema_required", 'if peer_schema != SCHEMA_VERSION' in deploy)
check("major_minor_match_required", 'peer[:2] != current[:2]' in deploy)
check("patch_skew_bounded", 'abs(peer[2] - current[2]) > max_patch' in deploy)
check("legacy_transition_explicit", "rolling_upgrade_allow_legacy_task_envelopes" in deploy and "legacy_envelope_transition" in deploy)
check("task_headers_have_app", '"mgc_app_version": APP_VERSION' in deploy)
check("task_headers_have_schema", '"mgc_schema_version": SCHEMA_VERSION' in deploy)
check("task_guard_before_body", "validate_task_headers" in guard and "super().__call__" in guard and guard.index("validate_task_headers") < guard.index("super().__call__"))
check("celery_uses_guarded_task", 'task_cls="app.workers.version_guard:VersionGuardedTask"' in celery)
check("publish_hook_injects_headers", "before_task_publish.connect" in celery and "task_publish_headers()" in celery)
check("worker_heartbeat", "worker_ready.connect" in celery and 'record_component_heartbeat("worker"' in celery)
check("worker_draining_signal", "worker_shutting_down.connect" in celery and 'state="draining"' in celery)
check("scheduler_pg_leader_lock", "pg_try_advisory_lock" in beat and "pg_advisory_unlock" in beat)
check("scheduler_lock_session_monitored", "_assert_lock_session(conn)" in beat and "return 75" in beat)
check("scheduler_standby_state", 'state="standby"' in beat)
check("compose_singleton_beat", "command: python -m app.workers.singleton_beat" in compose)
check("compose_worker_stop_grace", "stop_grace_period: ${WORKER_STOP_GRACE_PERIOD:-10m}" in compose)
for prefix in ("interactive", "cpu", "io", "cad", "ai"):
    check(f"worker_hostname_{prefix}", f"--hostname={prefix}@%h" in compose)
check("drain_stops_consumers", "cancel_consumer" in drain)
check("drain_waits_active_zero", ".active()" in drain and '"status": "drained"' in drain)
healthcheck = text("backend/app/workers/healthcheck.py")
check("worker_healthcheck_role_prefix", "endswith(f\"@{hostname}\")" in healthcheck)
check("known_skew_blocks_readiness", '"deployment_version_skew", True' in health and "incompatible_runtime_detected" in health)
check("registry_outage_non_gating", '"deployment_version_skew", False, True' in health)
check("operations_endpoint", '@router.get("/deployment-safety")' in ops)
check("operations_endpoint_admin", "def deployment_safety" in ops and "_admin(identity)" in ops[ops.index("def deployment_safety"):ops.index("def deployment_safety")+250])
check("rolling_script_exists", bool(rolling))
if rolling:
    worker_pos = rolling.find("drain_and_recreate worker")
    beat_pos = rolling.find("recreate_service beat")
    api_pos = rolling.find("recreate_service api")
    check("safe_rollout_order", -1 not in (worker_pos, beat_pos, api_pos) and worker_pos < beat_pos < api_pos, f"worker={worker_pos} beat={beat_pos} api={api_pos}")
    check("rolling_health_gate", "/api/v1/health/ready" in rolling)
    check("resilience_release_gate", "MGC_RESILIENCE_CERTIFICATION_REPORT" in rolling and "resilience_release_guard.py" in rolling)
    check("resilience_source_bundle_gate", all(name in rolling for name in ("MGC_RESILIENCE_EVIDENCE", "MGC_RESILIENCE_EVIDENCE_SIGNATURE", "MGC_RESILIENCE_PUBLIC_KEY", "MGC_RESILIENCE_BASELINE", "MGC_RESILIENCE_CAMPAIGN")))
    check("no_forced_kill_default", "docker compose kill" not in rolling and "SIGKILL" not in rolling)
check("compose_default_version_6316", "MGC_VERSION:-6.3.34" in compose)
check("no_v6316_db_migration", "ensure_v6316_schema" not in text("backend/app/db/migrations.py"))

failed = [x for x in checks if not x[1]]
for name, ok, detail in checks:
    print(f"{'PASS' if ok else 'FAIL'} {name}" + (f" — {detail}" if detail else ""))
print(f"SUMMARY {len(checks)-len(failed)}/{len(checks)} PASS")
if failed:
    raise SystemExit(1)
