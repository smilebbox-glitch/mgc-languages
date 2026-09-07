#!/usr/bin/env python3
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
checks=[]
def ck(name,ok): checks.append((name,bool(ok)))
def has(path,text):
    p=ROOT/path
    return p.exists() and text in p.read_text(encoding='utf-8')
ck('runtime_6323',has(Path('backend/app/core/runtime_contract.py'),'APP_VERSION = "6.3.34"'))
ck('schema_stable_6313',has(Path('backend/app/core/runtime_contract.py'),'SCHEMA_VERSION = "6.3.13"'))
ck('core_acceptance_schema',has(Path('backend/app/core/release_acceptance.py'),'mgc-release-acceptance-evidence-v1'))
ck('baseline_schema',has(Path('backend/app/core/release_acceptance.py'),'mgc-approved-release-baseline-v1'))
ck('chain_schema',has(Path('backend/app/core/release_acceptance.py'),'mgc-release-acceptance-chain-v1'))
ck('baseline_requires_human_approved',has(Path('backend/app/core/release_acceptance.py'),'BASELINE_HUMAN_APPROVED'))
ck('baseline_requires_signature',has(Path('backend/app/core/release_acceptance.py'),'BASELINE_SIGNATURE'))
ck('baseline_release_order',has(Path('backend/app/core/release_acceptance.py'),'BASELINE_RELEASE_ORDER'))
for code in ['REGRESSION_P95','REGRESSION_P99','REGRESSION_ERROR_RATE','REGRESSION_THROUGHPUT','REGRESSION_DB_POOL','REGRESSION_RTO','REGRESSION_RPO']:
    ck(code.lower(),has(Path('backend/app/core/release_acceptance.py'),code))
ck('pipeline_verifies_load_signature',has(Path('scripts/release_acceptance_pipeline.py'),'load evidence detached signature verification failed'))
ck('pipeline_verifies_baseline_signature',has(Path('scripts/release_acceptance_pipeline.py'),'baseline detached signature verification failed'))
ck('pipeline_optional_signing',has(Path('scripts/release_acceptance_pipeline.py'),'--signing-key'))
ck('baseline_promotion_exact_confirm',has(Path('scripts/promote_acceptance_baseline.py'),'BOOTSTRAP_APPROVED_BASELINE'))
ck('baseline_promotion_approval_reference',has(Path('scripts/promote_acceptance_baseline.py'),'--approval-reference'))
ck('chain_verifier_parent',has(Path('scripts/verify_acceptance_chain.py'),"reasons.append('parent')"))
ck('live_wrapper_explicit_confirm',has(Path('scripts/automated_release_acceptance.sh'),'MGC_RELEASE_ACCEPTANCE_CONFIRM'))
ck('live_wrapper_disruptive_confirm',has(Path('scripts/automated_release_acceptance.sh'),'MGC_RELEASE_ACCEPTANCE_DISRUPTIVE_CONFIRM'))
ck('live_wrapper_does_not_authorize',has(Path('scripts/automated_release_acceptance.sh'),'human change control remains mandatory'))
ck('make_preflight',has(Path('Makefile'),'release-acceptance-preflight:'))
ck('make_pipeline',has(Path('Makefile'),'release-acceptance:'))
failed=[n for n,ok in checks if not ok]
for n,ok in checks: print(('PASS' if ok else 'FAIL')+': '+n)
if failed: raise SystemExit('v6.3.34 release acceptance preflight failed: '+', '.join(failed))
print(f'PASS: v6.3.34 Automated Release Acceptance Pipeline preflight ({len(checks)}/{len(checks)})')
