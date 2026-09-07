from __future__ import annotations
import json, os, subprocess, sys
from pathlib import Path
import py_compile

ROOT=Path(__file__).resolve().parents[1]

def run(cmd:list[str], *, timeout:int=90, env:dict[str,str]|None=None) -> None:
    p=subprocess.run(cmd,cwd=ROOT,env=env,timeout=timeout,text=True,capture_output=True)
    if p.stdout.strip(): print(p.stdout.rstrip())
    if p.stderr.strip(): print(p.stderr.rstrip(),file=sys.stderr)
    if p.returncode:
        raise SystemExit(p.returncode)

def main()->int:
    py_compile.compile(str(ROOT/'app.py'),doraise=True)
    py_compile.compile(str(ROOT/'asgi.py'),doraise=True)
    for package in ('mgc_core','mgc'):
        for p in (ROOT/package).rglob('*.py'): py_compile.compile(str(p),doraise=True)
    for p in (ROOT/'scripts').glob('*.py'): py_compile.compile(str(p),doraise=True)
    for p in (ROOT/'tests').glob('*.py'): py_compile.compile(str(p),doraise=True)
    data=json.loads((ROOT/'data/chinese_foundations.json').read_text(encoding='utf-8'))
    assert len(data.get('tones',[]))==5
    assert data.get('pinyin',{}).get('formula')
    assert data.get('context',{}).get('clues')
    assert len(data.get('putonghua',{}).get('groups',[]))==10
    assert (data.get('learning_standard') or {}).get('name')=='Путунхуа (普通话)'
    print('PASS: Python compile + modular routers/cores + Putonghua scope')
    run([sys.executable,'scripts/api_contract_guard.py'],timeout=30)
    run([sys.executable,'scripts/content_integrity_guard.py'],timeout=60)
    print('PASS: API architecture + language content integrity guards')
    run([sys.executable,'tests/v593_multi_user_deployment_test.py'],timeout=20)
    print('PASS: multi-user LAN deployment contract')
    run([sys.executable,'scripts/capacity_preflight.py'],timeout=10)
    run([sys.executable,'tests/v594_capacity_hardening_test.py'],timeout=20)
    run([sys.executable,'tests/v594_capacity_runtime_test.py'],timeout=30)
    print('PASS: v5.9.4 capacity budget + load-probe contracts')
    run([sys.executable,'tests/v595_authenticated_load_test.py'],timeout=30)
    print('PASS: v5.9.5 authenticated load-tool contract')
    run([sys.executable,'tests/v596_learning_concurrency_test.py'],timeout=20)
    run([sys.executable,'tests/v596_concurrent_write_load_test.py'],timeout=30)
    print('PASS: v5.9.6 concurrent write locking + CSRF/idempotency/isolation contracts')
    run([sys.executable,'tests/v597_user_login_department_test.py'],timeout=40)
    print('PASS: v5.9.7 department-aware user/admin login contract')
    run(['node','--check','static/app.js'],timeout=20)
    run(['node','--check','static/auth_department.js'],timeout=20)
    print('PASS: JavaScript syntax')
    json.loads((ROOT/'deploy/observability/grafana-dashboard-v5.7.json').read_text(encoding='utf-8'))
    print('PASS: Grafana dashboard JSON')
    for rel in ['scripts/backup_postgres.sh','scripts/restore_postgres.sh','scripts/restore_rehearsal.sh','scripts/pitr_preflight.sh','scripts/pitr_basebackup.sh','scripts/postgres_failure_drill.sh','scripts/entrypoint.sh']:
        run(['bash','-n',rel],timeout=10)
    print('PASS: operational shell syntax')
    db=Path('/tmp/mgc_languages_v57_ci.db')
    try: db.unlink()
    except FileNotFoundError: pass
    env=os.environ.copy(); env.update({'AUTO_CREATE_SCHEMA':'false','DATABASE_URL':f'sqlite:///{db}'})
    run(['alembic','upgrade','head'],timeout=90,env=env)
    p=subprocess.run(['alembic','current'],cwd=ROOT,env=env,timeout=30,text=True,capture_output=True)
    out=(p.stdout+p.stderr)
    if p.returncode or 'c57d0a31f570' not in out:
        print(out,file=sys.stderr); raise SystemExit(p.returncode or 2)
    print('PASS: Alembic clean upgrade -> c57d0a31f570')
    print('PASS: v5.9.7 test-ready user login + department + admin preflight')
    return 0

if __name__=='__main__': raise SystemExit(main())
