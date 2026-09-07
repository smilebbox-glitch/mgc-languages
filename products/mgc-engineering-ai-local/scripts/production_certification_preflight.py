#!/usr/bin/env python3
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
checks=[]
def ck(name,ok): checks.append((name,bool(ok)))

def has(path,text):
    p=ROOT/path
    return p.exists() and text in p.read_text(encoding='utf-8',errors='ignore')

ck('runtime_version_6_3_22',has(Path('backend/app/core/runtime_contract.py'),'APP_VERSION = "6.3.34"'))
ck('schema_unchanged_6_3_13',has(Path('backend/app/core/runtime_contract.py'),'SCHEMA_VERSION = "6.3.13"'))
ck('certification_service', (ROOT/'backend/app/core/production_certification.py').exists())
ck('profiles_15_30_100', all(has(Path('backend/app/core/production_certification.py'),f'"{x}"') for x in ('15','30','100')))
ck('runtime_go_not_self_authorized',has(Path('backend/app/core/production_certification.py'),'"production_authorized": False'))
ck('live_evidence_required',has(Path('backend/app/core/production_certification.py'),'Target-host load/failover evidence'))
ck('slo_not_lb_readiness',has(Path('backend/app/core/production_certification.py'),'"slo_failure_blocks_existing_lb_readiness": False'))
ck('mutating_pool_backpressure',has(Path('backend/app/core/db_pool_admission.py'),'DB_POOL_SATURATED'))
ck('read_traffic_not_pool_fenced',has(Path('backend/app/core/production_certification.py'),'"read_traffic_fenced_on_saturation": False'))
ck('middleware_registered',has(Path('backend/app/main.py'),'DbPoolAdmissionMiddleware'))
ck('operations_endpoint',has(Path('backend/app/api/operations_routes.py'),'@router.get("/production-certification")'))
ck('support_bundle_evidence',has(Path('backend/app/services/production_support.py'),'production-certification.json'))
ck('certify_cli', (ROOT/'scripts/production_certify.py').exists())
ck('deployment_guard', (ROOT/'scripts/production_deployment_guard.py').exists())
ck('human_change_confirmation',has(Path('scripts/production_deployment_guard.py'),'APPROVED_CHANGE_WINDOW'))
ck('example_evidence_15',(ROOT/'ops/certification/evidence.15.example.json').exists())
ck('example_evidence_30',(ROOT/'ops/certification/evidence.30.example.json').exists())
ck('example_evidence_100',(ROOT/'ops/certification/evidence.100.example.json').exists())

ck('v6322_load_service',(ROOT/'backend/app/core/load_certification.py').exists())
ck('v6322_load_cli',(ROOT/'scripts/production_load_certify.py').exists())
ck('v6322_load_signature_required',has(Path('backend/app/core/production_certification.py'),'v6322_load_evidence_and_verified_detached_signature_required_for_go'))
ck('v6322_load_preflight',(ROOT/'scripts/production_load_certification_preflight.py').exists())
for name,ok in checks: print(('PASS' if ok else 'FAIL')+': '+name)
failed=[n for n,o in checks if not o]
print(f"production certification preflight: {len(checks)-len(failed)}/{len(checks)} PASS")
raise SystemExit(2 if failed else 0)
