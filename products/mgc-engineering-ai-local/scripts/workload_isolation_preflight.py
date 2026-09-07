#!/usr/bin/env python3
from __future__ import annotations
import ast
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
checks=[]
def ck(name,ok,detail=''):
    checks.append((name,bool(ok),detail))

rt=(ROOT/'backend/app/core/runtime_contract.py').read_text()
models=(ROOT/'backend/app/db/models.py').read_text()
mig=(ROOT/'backend/app/db/migrations.py').read_text()
jobs=(ROOT/'backend/app/services/background_jobs.py').read_text()
tasks=(ROOT/'backend/app/workers/tasks.py').read_text()
celery=(ROOT/'backend/app/workers/celery_app.py').read_text()
compose=(ROOT/'docker-compose.yml').read_text()
ops=(ROOT/'backend/app/services/production_support.py').read_text()
platform=(ROOT/'backend/app/api/contexts/platform_operations.py').read_text()
core=(ROOT/'backend/app/api/contexts/engineering_core.py').read_text()

ck('version','APP_VERSION = "6.3.34"' in rt and 'SCHEMA_VERSION = "6.3.13"' in rt)
ck('schema','def ensure_v6311_schema' in mig and "'6.3.11'" in mig)
for field in ('project_code','resource_class','priority','progress_percent','cancellation_requested','attempt_count','max_attempts','dead_lettered_at'):
    ck(f'compute_job_{field}',field in models)
for resource in ('interactive','cpu','io','cad','ai','maintenance'):
    ck(f'resource_{resource}',f'"{resource}"' in jobs and f'"{resource}"' in celery)
ck('project_concurrency','ProjectConcurrencyBusy' in jobs and 'pg_advisory_xact_lock' in jobs)
ck('safe_cancel','terminate=False' in platform and 'check_cancelled' in tasks)
ck('retry_dlq','dead_letter' in jobs and 'retry_dead_letter' in jobs and 'self.retry' in tasks)
ck('worker_prefetch_one','worker_prefetch_multiplier=1' in celery)
ck('late_ack','task_acks_late=True' in celery and 'task_reject_on_worker_lost=True' in celery)
ck('worker_split',all(x in compose for x in ('worker-cpu:','worker-io:','worker-cad:','worker-ai:')))
ck('ai_profile','profiles: ["ai", "advanced"]' in compose)
ck('ops_metrics','WORKLOAD_JOBS' in ops and 'WORKLOAD_DLQ' in ops)
ck('admin_snapshot','/operations/workload' in platform)
ck('user_cancel','/compute/tasks/{job_id}/cancel' in platform)
ck('async_ingest_managed','kind="document_ingest"' in core and 'dispatch_compute_job' in core)
ck('design_review_managed','kind="design_review"' in core and 'resource_class' in core)
ck('no_hard_kill','terminate=True' not in platform and 'SIGKILL' not in tasks)
failed=[x for x in checks if not x[1]]
for name,ok,detail in checks:
    print(f"{'PASS' if ok else 'FAIL'} {name}"+(f' — {detail}' if detail else ''))
print(f"SUMMARY {len(checks)-len(failed)}/{len(checks)} PASS")
if failed: raise SystemExit(1)
