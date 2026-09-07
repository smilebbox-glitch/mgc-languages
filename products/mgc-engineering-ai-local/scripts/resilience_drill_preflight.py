#!/usr/bin/env python3
from pathlib import Path
import json, sys, tempfile
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'backend'))
from app.core.resilience_drill import bind_incident_evidence, build_evidence, build_plan, catalog, validate_evidence, validate_plan
from app.core.runtime_contract import APP_VERSION, SCHEMA_VERSION
checks=[]
def ck(n,v): checks.append((n,bool(v)))
ck('runtime_v6331', APP_VERSION=='6.3.34' and SCHEMA_VERSION=='6.3.13')
cat=catalog(); ck('five_bounded_scenarios', set(cat['scenarios'])=={'api_instance_loss','worker_cpu_loss','redis_brownout','qdrant_brownout','integration_gateway_timeout'})
ck('no_arbitrary_shell', cat['governance']['arbitrary_shell_injection_allowed'] is False)
p=build_plan(['api_instance_loss','worker_cpu_loss'],tier='production',profile='core')
ck('production_safe_plan', validate_plan(p)==(True,[]))
try: build_plan(['redis_brownout'],tier='production',profile='core'); blocked=False
except ValueError: blocked=True
ck('production_dependency_default_blocked', blocked)
p2=build_plan(['redis_brownout'],tier='production',profile='core',maintenance_window_ref='CHG-DRILL-1',allow_production_dependency_drill=True)
ck('production_dependency_override_bounded', validate_plan(p2)==(True,[]))
e=build_evidence(p,[{'scenario':'api_instance_loss','fault_injected':True,'continuity_passed':True,'recovery_attempted':True,'recovery_passed':True},{'scenario':'worker_cpu_loss','fault_injected':True,'continuity_passed':True,'recovery_attempted':True,'recovery_passed':True}],live_execution=True)
ck('canonical_live_evidence', e['decision']=='PASS' and validate_evidence(e)==(True,[]))
sim=build_evidence(p,[{'scenario':'api_instance_loss','fault_injected':True,'continuity_passed':True,'recovery_attempted':True,'recovery_passed':True},{'scenario':'worker_cpu_loss','fault_injected':True,'continuity_passed':True,'recovery_attempted':True,'recovery_passed':True}],live_execution=False)
ck('simulation_not_pass', sim['decision']=='SIMULATED')
incident={"schema":"mgc.production-incident-evidence.v1","release":APP_VERSION,"database_schema":SCHEMA_VERSION,"generated_at":"2026-09-06T00:00:00+00:00","status":"INCIDENT_SIGNALS","signal_count":1,"highest_severity":"high","severity_counts":{"low":0,"medium":0,"high":1,"critical":0},"signals":[{"code":"APPLICATION_HA_UNSAFE","severity":"high","component":"application-ha","summary":"bounded","signal_fingerprint":"a","evidence":{}}],"governance":{"contains_raw_logs":False,"contains_document_content":False,"contains_queries":False,"contains_credentials":False,"bounded_cardinality":True,"automatic_destructive_recovery":False,"automatic_incident_resolution":False,"production_authorized":False,"human_operator_required":True}}
import hashlib
raw=json.dumps(incident,ensure_ascii=False,sort_keys=True,separators=(",", ":")).encode(); incident["integrity"]={"algorithm":"sha256","payload_sha256":hashlib.sha256(raw).hexdigest()}
bound=bind_incident_evidence(e,incident)
ck('privacy_safe_incident_binding', bound['incident_evidence_binding']['correlation_status']=='OBSERVED' and bound['incident_evidence_binding']['raw_signal_payloads_copied'] is False and validate_evidence(bound)==(True,[]))
script=(ROOT/'scripts/resilience_drill.py').read_text()
ck('explicit_live_confirmation', 'confirm != "DRILL"' in script)
ck('known_compose_actions_only', '"stop", "-t", "10", service' in script and 'bash -lc' not in script and 'shell=True' not in script)
ck('finally_recovery', 'finally:' in script and 'compose_argv(files, "start", service)' in script)
ck('no_db_migration', not any((ROOT/'backend/app/db/migrations/versions').glob('*6.3.34*')) if (ROOT/'backend/app/db/migrations/versions').exists() else True)
failed=[n for n,v in checks if not v]
for n,v in checks: print(('PASS' if v else 'FAIL'), n)
print(f"\nResilience drill orchestration preflight: {len(checks)-len(failed)}/{len(checks)} PASS")
if failed: raise SystemExit('failed: '+', '.join(failed))
