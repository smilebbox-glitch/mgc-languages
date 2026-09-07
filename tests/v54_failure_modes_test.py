from __future__ import annotations
import asyncio, json, os, sys, tempfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
DB=Path(tempfile.gettempdir())/'mgc_languages_v54_failure.db'
try: DB.unlink()
except FileNotFoundError: pass
os.environ.update({
    'DATABASE_URL':f'sqlite:///{DB}','AUTO_CREATE_SCHEMA':'true','APP_ENV':'development','AUTH_MODE':'local',
    'REGISTRATION_ENABLED':'true','OIDC_STATE_SECRET':'v54-failure-state-secret-32-bytes-001','TTS_LEGACY_GET_ENABLED':'false',
    'TTS_CACHE_PERSISTENCE':'ephemeral','METRICS_ENABLED':'true','METRICS_TOKEN':'',
})
sys.path.insert(0,str(ROOT))
from fastapi.testclient import TestClient  # noqa
from starlette.requests import Request  # noqa
from sqlalchemy.exc import SQLAlchemyError  # noqa
import app  # noqa

c=TestClient(app.app)
r=c.post('/api/register',json={'username':'failuser','password':'FailurePass123!','display_name':'Failure User'})
assert r.status_code==200,r.text
csrf=c.cookies.get('mgc_csrf')

# Simulate server TTS outage: API returns a controlled 503 so frontend can use browser fallback.
original_health=app._tts_health
app._tts_health=lambda force=False:{'server_available':False,'language_checks':{'chinese':False,'english':False},'cache_writable':True,'engine':'browser-fallback'}
try:
    r=c.post('/api/pronunciation/audio',headers={'X-CSRF-Token':csrf},json={'language':'chinese','text':'普通话','rate':1.0})
    assert r.status_code==503,r.text
    assert 'browser fallback' in r.json()['detail']
finally:
    app._tts_health=original_health
with app.SessionLocal() as db:
    assert db.scalar(app.select(app.func.count()).select_from(app.OperationalEvent).where(app.OperationalEvent.event_type=='tts.fallback')) >= 1

# DB exception handler is deterministic, retryable and does not expose internals.
scope={'type':'http','method':'GET','path':'/api/me','headers':[], 'query_string':b'', 'scheme':'http','server':('testserver',80),'client':('127.0.0.1',1),'root_path':''}
req=Request(scope); req.state.request_id='db-failure-test'
resp=asyncio.run(app.sqlalchemy_unavailable_handler(req, SQLAlchemyError('synthetic secret DB detail')))
assert resp.status_code==503
payload=json.loads(resp.body)
assert payload['code']=='database_unavailable' and payload['retryable'] is True
assert 'synthetic secret' not in resp.body.decode()

metrics=c.get('/metrics')
assert metrics.status_code==200
assert 'mgc_operational_events_24h' in metrics.text and 'mgc_database_metrics_available' in metrics.text
print('OK: v5.4 controlled TTS/DB failure degradation and operational metrics')
