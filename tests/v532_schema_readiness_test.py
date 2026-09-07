from __future__ import annotations
import os, sqlite3, subprocess, sys, tempfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
DB=Path(tempfile.gettempdir())/'mgc_languages_v532_schema.db'
try: DB.unlink()
except FileNotFoundError: pass

env=os.environ.copy()
env.update({
    'DATABASE_URL':f'sqlite:///{DB}',
    'AUTO_CREATE_SCHEMA':'false',
    'APP_ENV':'pilot',
    'AUTH_MODE':'local',
    'REGISTRATION_ENABLED':'false',
    'OIDC_STATE_SECRET':'pilot-state-secret-32-bytes-long-0000001',
    'TRUSTED_HOSTS':'testserver,localhost,127.0.0.1',
    'METRICS_ENABLED':'true',
    'METRICS_TOKEN':'metrics-secret-32-bytes-long-0000001',
    'READY_REQUIRE_SCHEMA_HEAD':'true',
    'READY_REQUIRE_REGISTRATION_DISABLED':'true',
    'READY_REQUIRE_METRICS_TOKEN':'true',
    'READY_REQUIRE_OIDC':'false',
    'READY_REQUIRE_SECURE_COOKIE':'false',
    'EXPECTED_ALEMBIC_HEAD':'c57d0a31f570',
    'TTS_LEGACY_GET_ENABLED':'false',
    'TTS_CACHE_PERSISTENCE':'ephemeral',
    'TTS_CACHE_DIR':str(Path(tempfile.gettempdir())/'mgc-v532-tts'),
})
subprocess.run([sys.executable,'-m','alembic','upgrade','head'],cwd=ROOT,env=env,check=True,stdout=subprocess.DEVNULL)
os.environ.update({k:v for k,v in env.items() if k in {
    'DATABASE_URL','AUTO_CREATE_SCHEMA','APP_ENV','AUTH_MODE','REGISTRATION_ENABLED','OIDC_STATE_SECRET','TRUSTED_HOSTS',
    'METRICS_ENABLED','METRICS_TOKEN','READY_REQUIRE_SCHEMA_HEAD','READY_REQUIRE_REGISTRATION_DISABLED',
    'READY_REQUIRE_METRICS_TOKEN','READY_REQUIRE_OIDC','READY_REQUIRE_SECURE_COOKIE','EXPECTED_ALEMBIC_HEAD',
    'TTS_LEGACY_GET_ENABLED','TTS_CACHE_PERSISTENCE','TTS_CACHE_DIR'}})
sys.path.insert(0,str(ROOT))
from fastapi.testclient import TestClient  # noqa
import app  # noqa
c=TestClient(app.app)
r=c.get('/health/ready')
assert r.status_code==200,r.text
checks=r.json()['checks']
assert checks['schema_head']['status']=='ok' and checks['schema_head']['current']=='c57d0a31f570',checks
assert checks['self_registration']=='disabled',checks
assert checks['metrics_protection']=='token',checks
assert checks['trusted_hosts']=='ok' and checks['cors_policy']=='ok',checks
assert c.get('/api/meta').json()['version']=='5.7.1'

# Simulate drift / forgotten migration: readiness must fail rather than serving as healthy.
with sqlite3.connect(DB) as db:
    db.execute("UPDATE alembic_version SET version_num='78068b70afbf'")
    db.commit()
r=c.get('/health/ready')
assert r.status_code==503,r.text
bad=r.json()['checks']['schema_head']
assert bad['status']=='failed' and bad['current']=='78068b70afbf',bad
print('OK: v5.3.2 schema drift blocks readiness; pilot policy gates validated')
