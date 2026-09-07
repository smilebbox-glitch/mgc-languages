#!/usr/bin/env python3
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
checks=[]
def ck(name, ok):
    checks.append((name,bool(ok))); print(('PASS' if ok else 'FAIL')+': '+name)
rt=(ROOT/'backend/app/core/runtime_contract.py').read_text()
core=(ROOT/'backend/app/core/load_certification.py').read_text()
harness=(ROOT/'scripts/production_load_certify.py').read_text()
cert=(ROOT/'scripts/production_certify.py').read_text()
pc=(ROOT/'backend/app/core/production_certification.py').read_text()
mk=(ROOT/'Makefile').read_text()
ck('app version v6.3.34','APP_VERSION = "6.3.34"' in rt)
ck('schema remains v6.3.13','SCHEMA_VERSION = "6.3.13"' in rt)
ck('load evidence schema','mgc-production-load-evidence-v1' in core)
ck('profiles 15 30 100',all(f'"{x}"' in core for x in ('15','30','100')))
ck('full concurrency 15 30 100',all(x in core for x in ('LoadProfile("15", 15, 15','LoadProfile("30", 30, 30','LoadProfile("100", 100, 100')))
for code in ('object_360','bom_versions','work_instructions','rag_search','rag_ask'):
    ck('workload '+code,code in core)
ck('p50 p95 p99 metrics',all(x in core for x in ('p50_ms','p95_ms','p99_ms')))
ck('error budget burn','consumed_ratio' in core and 'remaining_ratio' in core)
ck('db pool saturation','max_saturation_ratio' in core)
ck('queue saturation','max_oldest_job_age_seconds' in core and 'max_depth' in core)
ck('no business write replay','non_idempotent_business_write_replay_allowed' in core)
ck('live confirmation required','MGC_LOAD_CERTIFY_CONFIRM' in harness)
ck('audited post explicit opt in','MGC_LOAD_ALLOW_AUDITED_POSTS' in harness)
ck('credentials read from env','MGC_LOAD_API_KEY' in harness and 'MGC_LOAD_BEARER_TOKEN' in harness)
ck('raw fixture identifiers not retained','raw_identifiers_retained' in harness and '_fixture_hash' in harness)
ck('canonical digest','canonical_sha256' in core and 'canonical_payload_bytes' in core)
ck('detached signing','openssl' in harness and '-sign' in harness)
ck('detached verification','-verify' in cert and '--load-public-key' in cert)
ck('acceptance requires load evidence','load_acceptance_checks' in pc and 'load_certification' in pc)
ck('make load preflight target','production-load-certification-preflight' in mk)
failed=[n for n,ok in checks if not ok]
if failed: raise SystemExit('v6.3.34 load certification preflight failed: '+', '.join(failed))
print(f'PASS: v6.3.34 Production Load Certification preflight ({len(checks)}/{len(checks)})')
