#!/usr/bin/env python3
from __future__ import annotations
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
checks=[]
def ck(name, ok):
    checks.append((name,bool(ok)))
def text(rel):
    return (ROOT/rel).read_text(encoding='utf-8')

rt=text('backend/app/core/runtime_contract.py')
svc=text('backend/app/services/integration_certification.py')
routes=text('backend/app/api/integration_routes.py')
cli=text('scripts/integration_certify.py')
mgc=text('scripts/mgcctl.py')
mk=text('Makefile')

ck('runtime_6327','APP_VERSION = "6.3.34"' in rt and 'SCHEMA_VERSION = "6.3.13"' in rt)
ck('certification_schema','mgc.integration-certification.v1' in svc)
for domain in ['plm','pdm','erp','mes','qms']:
    ck(f'domain_{domain}',f'"{domain}"' in svc)
    p=ROOT/f'ops/integrations/contracts/{domain}.example.json'
    ck(f'contract_file_{domain}',p.exists())
    if p.exists():
        payload=json.loads(p.read_text())
        ck(f'contract_schema_{domain}',payload.get('schema')=='mgc.integration-adapter-contract.v1')
        sys=payload.get('system') or {}; cfg=sys.get('config') or {}; cert=cfg.get('certification') or {}
        ck(f'contract_domain_{domain}',sys.get('source_domain')==domain)
        ck(f'contract_no_writeback_{domain}',cert.get('writeback_enabled') is False)
        ck(f'contract_degraded_{domain}',cert.get('degraded_mode')=='cached_read_only')
ck('env_secret_refs','SECRET_REFERENCES_ONLY' in svc and 'NO_RAW_SECRETS_IN_CONFIG' in svc)
ck('tls_or_local_simulator','TLS_OR_EXPLICIT_LOCAL_SIMULATOR' in svc)
ck('deterministic_probe','DETERMINISTIC_FIRST_PAGE' in svc)
ck('idempotent_replay','IDEMPOTENT_REPLAY_KEYS' in svc)
ck('checkpoint_modes','SOURCE_CHECKPOINT' in svc and 'FINGERPRINT_CHECKPOINT' in svc)
ck('privacy_safe_samples','external_id_sha256' in svc and 'snapshot_sha256' in svc)
ck('runtime_modes','DEGRADED_READ_ONLY' in svc and 'cached_engineering_reads_allowed' in svc)
ck('no_source_mutation','authoritative_source_mutation_allowed' in svc and 'False' in svc)
ck('sync_guard','INTEGRATION_DEGRADED_READ_ONLY' in routes and 'sync_allowed' in routes)
ck('admin_certify_route','/integrations/{system_id}/certify' in routes and 'INTEGRATION_CERTIFICATION' in routes)
ck('runtime_posture_route','/integrations/{system_id}/runtime-posture' in routes)
ck('cli_shell_free','subprocess' not in cli or 'shell=True' not in cli)
ck('mgcctl_integration_action','certify_action == "integration"' in mgc and 'integration-certify' in mgc)
ck('mgcctl_integration_scope','"integration": ["integration-certification", "integration-runtime-assurance"]' in mgc)
ck('make_target','integration-certification-preflight:' in mk and 'integration-certify:' in mk)
ck('suite_exists',(ROOT/'scripts/integration_contract_suite.py').exists())
ck('no_db_migration',not any((ROOT/'backend/app/db/migrations/versions').glob('*6.3.34*')) if (ROOT/'backend/app/db/migrations/versions').exists() else True)
failed=[n for n,ok in checks if not ok]
if failed:
    raise SystemExit('v6.3.34 integration certification preflight failed: '+', '.join(failed))
print(f'PASS: v6.3.34 Real Integration Certification preflight ({len(checks)}/{len(checks)})')
