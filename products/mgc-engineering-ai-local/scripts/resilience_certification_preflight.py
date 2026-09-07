#!/usr/bin/env python3
from pathlib import Path
import hashlib,json,sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'backend'))
from app.core.runtime_contract import APP_VERSION,SCHEMA_VERSION
from app.core.resilience_certification import build_baseline,build_campaign,certify_recovery,validate_baseline,validate_campaign,validate_certification
checks=[]
def ck(n,v): checks.append((n,bool(v)))
def ev(release,api=10.0,worker=12.0):
    b={'schema':'mgc.resilience-drill-evidence.v1','release':release,'database_schema':SCHEMA_VERSION,'generated_at':'2026-09-06T00:00:00+00:00','tier':'production','profile':'core','plan_sha256':'p','live_execution':True,'decision':'PASS','results':[{'scenario':'api_instance_loss','service':'api','fault_injected':True,'continuity_passed':True,'recovery_attempted':True,'recovery_passed':True,'recovery_seconds':api,'expected_signal_codes':['APPLICATION_HA_UNSAFE'],'notes_code':'PREFLIGHT','status':'PASS'},{'scenario':'worker_cpu_loss','service':'worker-cpu','fault_injected':True,'continuity_passed':True,'recovery_attempted':True,'recovery_passed':True,'recovery_seconds':worker,'expected_signal_codes':['WORKLOAD_RECOVERY_REQUIRED'],'notes_code':'PREFLIGHT','status':'PASS'}],'governance':{'contains_raw_logs':False,'contains_credentials':False,'contains_engineering_document_content':False,'arbitrary_shell_injection_used':False,'automatic_production_authorization':False,'automatic_root_cause_claimed':False,'human_operator_required':True}}
    raw=json.dumps(b,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode(); b['integrity']={'algorithm':'sha256','payload_sha256':hashlib.sha256(raw).hexdigest()}; return b
sig={'verified':True,'algorithm':'openssl-sha256','public_key_sha256':'f'*64}
ck('runtime_v6332',APP_VERSION=='6.3.34' and SCHEMA_VERSION=='6.3.13')
b=build_baseline(ev('6.3.33'),signature_verification=sig,approval_reference='CAB-633',approved_at='2026-09-06T01:00:00Z',approved_by_role='release-manager')
ck('approved_signed_baseline',validate_baseline(b)==(True,[]) and b['source_signature']['verified'] is True)
c=build_campaign(campaign_id='RC-6333',baseline=b,scenarios=['api_instance_loss','worker_cpu_loss'],profile='core',tier='production',approval_reference='CAB-633',approved_at='2026-09-06T02:00:00Z',approved_by_role='change-manager')
ck('approved_campaign',validate_campaign(c,b)==(True,[]) and c['approval']['human_approved'] is True)
go=certify_recovery(current_evidence=ev('6.3.34',8,10),signature_verification=sig,baseline=b,campaign=c)
ck('improvement_go',go['decision']=='GO' and validate_certification(go,require_go=True)==(True,[]))
reg=certify_recovery(current_evidence=ev('6.3.34',13,10),signature_verification=sig,baseline=b,campaign=c)
ck('automatic_rto_regression_no_go',reg['decision']=='NO_GO' and 'RTO_REGRESSION_GATE' in reg['failed_checks'])
ck('per_scenario_comparison',len(go['scenario_comparisons'])==2 and all('absolute_delta_seconds' in x and 'ratio' in x for x in go['scenario_comparisons']))
ck('aggregate_rto_comparison',go['aggregate_rto']['baseline_seconds']==12.0 and go['aggregate_rto']['current_seconds']==10.0)
ck('no_auto_production_auth',go['production_authorized'] is False and go['governance']['automatic_production_authorization'] is False)
ck('human_release_approval',go['human_release_approval_required'] is True)
script=(ROOT/'scripts/resilience_certify.py').read_text()
ck('openssl_detached_signature','dgst", "-sha256", "-sign"' in script and 'dgst", "-sha256", "-verify"' in script)
ck('explicit_baseline_approval','APPROVE-BASELINE' in script)
ck('explicit_campaign_approval','APPROVE-CAMPAIGN' in script)
guard=(ROOT/'scripts/resilience_release_guard.py').read_text()
ck('release_guard_recomputes_source_bundle','validate_release_bundle' in guard and '--evidence' in guard and '--baseline' in guard and '--campaign' in guard)
ck('release_guard_verifies_detached_signature','dgst", "-sha256", "-verify"' in guard and '--signature' in guard and '--public-key' in guard)
ck('adjacent_baseline_only','_is_adjacent_previous_release' in (ROOT/'backend/app/core/resilience_certification.py').read_text())
ck('profile_tier_match_gate','PROFILE_TIER_MATCH' in (ROOT/'backend/app/core/resilience_certification.py').read_text())
ck('no_arbitrary_shell','shell=True' not in script and 'bash -lc' not in script)
ck('no_db_migration',not any((ROOT/'backend/app/db/migrations/versions').glob('*6.3.34*')) if (ROOT/'backend/app/db/migrations/versions').exists() else True)
failed=[n for n,v in checks if not v]
for n,v in checks: print(('PASS' if v else 'FAIL'),n)
print(f'\nResilience certification & recovery baselines preflight: {len(checks)-len(failed)}/{len(checks)} PASS')
if failed: raise SystemExit('failed: '+', '.join(failed))
