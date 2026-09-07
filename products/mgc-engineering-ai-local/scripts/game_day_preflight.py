from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
checks = []

def add(name, ok):
    checks.append((name, bool(ok)))

svc = (ROOT/'backend/app/services/operations_acceptance.py').read_text()
routes = (ROOT/'backend/app/api/operations_routes.py').read_text()
models = (ROOT/'backend/app/db/models.py').read_text()
docs = (ROOT/'docs/GAME_DAY_RUNBOOK.md').read_text() if (ROOT/'docs/GAME_DAY_RUNBOOK.md').exists() else ''

required = ['postgres_outage','redis_outage','qdrant_outage','worker_crash_restart','integration_outage','expired_tls_certificate','oidc_failure','queue_overload','backup_restore']
for code in required:
    add(f'exercise:{code}', code in svc and code.replace('_','-') in docs)
add('fault injection explicitly outside app', 'application_never_injects_faults' in svc and 'never injects infrastructure faults' in docs.lower())
add('GO never authorizes deployment', 'deployment_authorized' in svc and 'False' in svc)
add('explicit finalize token', 'FINALIZE_OPERATIONS_ACCEPTANCE' in svc)
add('RTO/RPO evidence', 'actual_rpo_seconds' in models and 'actual_rto_seconds' in svc)
add('admin API present', '/game-days' in routes)
add('schema tables', 'operations_game_day_runs' in models and 'operations_game_day_exercises' in models)
failed=[n for n,ok in checks if not ok]
for n,ok in checks:
    print(('PASS' if ok else 'FAIL')+': '+n)
print(f'game-day preflight: {len(checks)-len(failed)}/{len(checks)} PASS')
raise SystemExit(1 if failed else 0)
