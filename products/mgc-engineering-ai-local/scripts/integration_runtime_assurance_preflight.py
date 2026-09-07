#!/usr/bin/env python3
from __future__ import annotations
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
checks=[]
def ck(name, ok): checks.append((name,bool(ok)))
def text(rel): return (ROOT/rel).read_text(encoding='utf-8')

rt=text('backend/app/core/runtime_contract.py')
svc=text('backend/app/services/integration_certification.py')
routes=text('backend/app/api/integration_routes.py')
mgc=text('scripts/mgcctl.py')
mk=text('Makefile')

ck('runtime_6328','APP_VERSION = "6.3.34"' in rt and 'SCHEMA_VERSION = "6.3.13"' in rt)
ck('runtime_posture_v2','mgc.integration-runtime-posture.v2' in svc)
ck('bounded_staleness_policy','max_cache_staleness_minutes' in svc and 'BOUNDED_CACHE_STALENESS' in svc)
ck('stale_cache_reason','CACHE_STALE' in svc)
ck('no_cache_reason','NO_CACHED_ENGINEERING_DATA' in svc)
ck('stale_cache_blocks_reads','and not cache_stale' in svc)
ck('recovery_opt_in','recovery_sync_enabled' in svc and 'False' in svc)
ck('recovery_runtime_flag','recovery_sync_allowed' in svc)
ck('recovery_sync_gate','posture["mode"] == "ACTIVE" or posture["recovery_sync_allowed"]' in svc)
ck('ok_status_reliability','{"ok", "completed", "failed", "partial", "success"}' in svc)
ck('privacy_safe_runtime','external_id' not in svc[svc.index('"schema": "mgc.integration-runtime-posture.v2"'):svc.index('def sync_allowed')])
ck('runtime_posture_route','/integrations/{system_id}/runtime-posture' in routes)
ck('no_source_writeback','"authoritative_source_mutation_allowed": False' in svc)
for domain in ['plm','pdm','erp','mes','qms']:
    p=ROOT/f'ops/integrations/contracts/{domain}.example.json'
    payload=json.loads(p.read_text()) if p.exists() else {}
    cert=(((payload.get('system') or {}).get('config') or {}).get('certification') or {})
    ck(f'{domain}_bounded_cache', isinstance(cert.get('max_cache_staleness_minutes'), (int,float)) and 0 < cert['max_cache_staleness_minutes'] <= 10080)
    ck(f'{domain}_recovery_opt_in', cert.get('recovery_sync_enabled') is True)
ck('mgcctl_preflight_registered','integration-runtime-assurance' in mgc)
ck('make_target','integration-runtime-assurance-preflight:' in mk)
ck('new_tests',(ROOT/'backend/tests/test_v6328_integration_runtime_assurance.py').exists())
ck('no_db_migration',not any((ROOT/'backend/app/db/migrations/versions').glob('*6.3.34*')) if (ROOT/'backend/app/db/migrations/versions').exists() else True)
failed=[n for n,ok in checks if not ok]
for n,ok in checks: print(f"{'PASS' if ok else 'FAIL'} {n}")
print(f"SUMMARY {len(checks)-len(failed)}/{len(checks)} PASS")
if failed: raise SystemExit('v6.3.34 integration runtime assurance preflight failed: '+', '.join(failed))
