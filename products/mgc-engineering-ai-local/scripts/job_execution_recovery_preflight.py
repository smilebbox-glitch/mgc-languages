#!/usr/bin/env python3
from __future__ import annotations
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
checks=[]
def ck(name, ok, detail=''):
    checks.append((name, bool(ok), detail))

rt=(ROOT/'backend/app/core/runtime_contract.py').read_text()
models=(ROOT/'backend/app/db/models.py').read_text()
mig=(ROOT/'backend/app/db/migrations.py').read_text()
jobs=(ROOT/'backend/app/services/background_jobs.py').read_text()
tasks=(ROOT/'backend/app/workers/tasks.py').read_text()
ops=(ROOT/'backend/app/services/production_support.py').read_text()
api=(ROOT/'backend/app/api/contexts/platform_operations.py').read_text()
cfg=(ROOT/'backend/app/core/config.py').read_text()
env=(ROOT/'.env.example').read_text()

ck('version', 'APP_VERSION = "6.3.34"' in rt and 'SCHEMA_VERSION = "6.3.13"' in rt)
ck('migration', 'def ensure_v6313_schema' in mig and "'6.3.13'" in mig)
ck('recovery_ledger_table', 'class ComputeJobRecoveryEvent' in models and 'compute_job_recovery_events' in mig)
for f in ('dispatch_token','dispatch_generation','last_dispatch_at','lease_expires_at','recovery_count','last_recovery_at','recovery_reason'):
    ck(f'job_{f}', f in models and f in mig)
ck('delivery_fencing', 'class StaleJobDelivery' in jobs and 'def _assert_fence' in jobs and '_fence_old_delivery' in jobs)
ck('dispatch_generation', 'def _prepare_dispatch' in jobs and 'dispatch_generation' in jobs and 'dispatch_token' in jobs)
ck('lease_admission', 'class ActiveJobLease' in jobs and 'lease_expires_at' in jobs and 'acquire_execution_slot' in jobs)
ck('lease_heartbeat_refresh', 'lease_expires_at = _lease_deadline' in jobs and 'heartbeat_at = now' in jobs)
ck('safe_replay_allowlist', '"document_ingest"' in jobs and '"safe_replay"' in jobs)
ck('decision_manual_only', '"design_review": JobPolicy' in jobs and '"manual"' in jobs)
ck('recovery_engine', 'def recover_expired_leases' in jobs and 'manual_orphaned' in jobs and 'auto_requeued' in jobs)
ck('manual_confirmation', 'confirm != "RECOVER_ORPHANED"' in jobs and 'prepare_orphan_recovery' in api)
ck('recovery_audit', '_record_recovery' in jobs and 'list_recovery_events' in jobs)
ck('recovery_api', '/operations/workload/{job_id}/recover' in api and '/operations/workload/recovery-events' in api)
ck('admin_recovery_guard', 'Admin group required' in api and 'RECOVER_ORPHANED' in jobs)
ck('housekeeping_recovers', 'recover_expired_leases' in tasks and 'workload_housekeeping' in tasks)
ck('managed_tasks_receive_fence', 'dispatch_token' in tasks and tasks.count('dispatch_token=dispatch_token') >= 8)
ck('no_worker_sigkill', 'SIGKILL' not in tasks and 'terminate=True' not in api)
ck('orphan_metric', 'mgc_compute_orphaned_jobs' in ops)
ck('expired_lease_metric', 'mgc_compute_expired_running_leases' in ops)
ck('recovery_metric', 'mgc_compute_recovery_events_total' in ops)
ck('recovery_snapshot', 'expired_running_leases' in jobs and 'safe_replay_kinds' in jobs)
for name in ('job_worker_lease_grace_seconds','job_auto_recovery_enabled','job_auto_recovery_max_per_cycle'):
    ck(f'config_{name}', name in cfg)
ck('env_controls', all(x in env for x in ('JOB_WORKER_LEASE_GRACE_SECONDS','JOB_AUTO_RECOVERY_ENABLED','JOB_AUTO_RECOVERY_MAX_PER_CYCLE')))
ck('old_delivery_cannot_write_success', '_assert_fence(job, dispatch_token)' in jobs and 'def mark_success' in jobs)
ck('old_delivery_cannot_write_failure', '_assert_fence(job, dispatch_token)' in jobs and 'def mark_failure' in jobs)
ck('recovery_does_not_self_authorize_engineering_decisions', 'automatic replay is not authorized for this job kind' in jobs)

failed=[x for x in checks if not x[1]]
for name,ok,detail in checks:
    print(f"{'PASS' if ok else 'FAIL'} {name}"+(f' — {detail}' if detail else ''))
print(f"SUMMARY {len(checks)-len(failed)}/{len(checks)} PASS")
if failed: raise SystemExit(1)
