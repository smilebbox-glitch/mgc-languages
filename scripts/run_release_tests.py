from __future__ import annotations
import argparse, os, signal, subprocess, sys, tempfile, time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
SHARDS={
 'base':['tests/smoke_test.py','tests/v5_gamification_test.py','tests/v51_security_test.py','tests/v52_chinese_audio_department_test.py'],
 'pronunciation':['tests/v52_frontend_contract_test.py','tests/v521_pronunciation_quality_test.py','tests/v522_tone_lab_test.py','tests/v52_compose_policy_test.py'],
 'putonghua':['tests/v53_putonghua_pilot_test.py','tests/v531_privacy_readiness_test.py','tests/v532_schema_readiness_test.py','tests/v532_migration_lock_contract_test.py'],
 'reliability':['tests/v54_reliability_test.py','tests/v54_failure_modes_test.py'],
 'ops':['tests/v55_operations_test.py','tests/v56_governance_putonghua_clarity_test.py'],
 'v57':['tests/v57_security_data_integrity_test.py','tests/v57_authorization_matrix_test.py'],
 'v571':['tests/v571_observability_recovery_test.py'],
 'v572':['tests/v572_architecture_contract_test.py','tests/v572_content_integrity_test.py'],
 'v573':['tests/v573_runtime_contract_test.py','tests/v573_modular_entrypoint_test.py','tests/v573_config_extraction_test.py'],
 'v574':['tests/v574_security_primitives_test.py','tests/v574_security_runtime_test.py'],
 'v575':['tests/v575_auth_core_test.py','tests/v575_auth_runtime_test.py'],
 'v576':['tests/v576_governance_core_test.py','tests/v576_governance_runtime_test.py'],
 'v577':['tests/v577_service_core_test.py','tests/v577_service_runtime_test.py'],
 'v578':['tests/v578_learning_core_test.py','tests/v578_learning_runtime_test.py'],
 'v579':['tests/v579_workflow_core_test.py','tests/v579_workflow_runtime_test.py'],
 'v580':['tests/v580_router_core_test.py','tests/v580_router_runtime_test.py'],
 'v581':['tests/v581_observability_core_test.py','tests/v581_observability_runtime_test.py'],
 'v582':['tests/v582_auth_router_core_test.py','tests/v582_auth_router_runtime_test.py'],
 'v583':['tests/v583_learning_router_core_test.py','tests/v583_learning_router_runtime_test.py'],
 'v584':['tests/v584_practice_games_router_core_test.py','tests/v584_practice_games_router_runtime_test.py'],
 'v585':['tests/v585_terminology_admin_router_core_test.py','tests/v585_terminology_admin_router_runtime_test.py'],
 'v586':['tests/v586_pronunciation_router_core_test.py','tests/v586_pronunciation_router_runtime_test.py'],
 'v587':['tests/v587_tts_core_test.py','tests/v587_tts_runtime_test.py'],
}
def tail(path:Path,limit:int=5000)->str:
 try:return path.read_text(encoding='utf-8',errors='replace')[-limit:]
 except Exception:return ''
def main()->int:
 ap=argparse.ArgumentParser(description='Isolated MGC Languages release regression runner')
 ap.add_argument('--timeout',type=int,default=45); ap.add_argument('--shard',choices=SHARDS,required=True); a=ap.parse_args()
 tests=SHARDS[a.shard]; started=time.monotonic(); passed=0
 for rel in tests:
  t0=time.monotonic()
  with tempfile.TemporaryDirectory(prefix='mgc-release-test-') as td:
   outp=Path(td)/'stdout.txt'; errp=Path(td)/'stderr.txt'
   with outp.open('wb') as out,errp.open('wb') as err:
    proc=subprocess.Popen([sys.executable,rel],cwd=ROOT,stdout=out,stderr=err,start_new_session=True)
    try: rc=proc.wait(timeout=a.timeout)
    except subprocess.TimeoutExpired:
     try:os.killpg(proc.pid,signal.SIGKILL)
     except ProcessLookupError:pass
     try:proc.wait(timeout=5)
     except Exception:pass
     print(f'FAIL {rel}: TIMEOUT after {a.timeout}s'); print(tail(outp,3000)); print(tail(errp,3000)); return 2
   elapsed=time.monotonic()-t0
   if rc!=0:
    print(f'FAIL {rel}: exit={rc} ({elapsed:.2f}s)'); print(tail(outp)); print(tail(errp)); return rc or 1
   lines=[x for x in tail(outp,3000).splitlines() if x.strip()]
   print(f"PASS {rel} ({elapsed:.2f}s) :: {(lines[-1] if lines else 'PASS')}",flush=True); passed+=1
 print(f'PASS: {a.shard} shard {passed}/{len(tests)} in {time.monotonic()-started:.2f}s'); return 0
if __name__=='__main__':raise SystemExit(main())
