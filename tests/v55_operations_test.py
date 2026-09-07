from __future__ import annotations
import os, sys, tempfile, time
from datetime import datetime, timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
DB=Path(tempfile.gettempdir())/'mgc_languages_v55_operations.db'
try: DB.unlink()
except FileNotFoundError: pass
os.environ.update({
    'DATABASE_URL':f'sqlite:///{DB}', 'AUTO_CREATE_SCHEMA':'true', 'APP_ENV':'test', 'AUTH_MODE':'local',
    'REGISTRATION_ENABLED':'false', 'OIDC_STATE_SECRET':'v55-test-secret-32-bytes-long-0000001',
    'TRUSTED_HOSTS':'testserver,localhost,127.0.0.1', 'MGC_ADMIN_USERNAME':'v55admin',
    'MGC_ADMIN_PASSWORD':'V55AdminPassword!123456', 'MGC_ADMIN_DISPLAY_NAME':'V55 Admin',
    'TTS_LEGACY_GET_ENABLED':'false', 'SLO_WINDOW_MINUTES':'60', 'SLO_AVAILABILITY_TARGET_PERCENT':'99.0',
    'SLO_ERROR_RATE_TARGET_PERCENT':'1.0', 'SLO_P95_TARGET_MS':'2000', 'ALERT_ERROR_RATE_PERCENT':'2.0',
    'ALERT_P95_MS':'3000', 'RECOVERY_STABLE_SECONDS':'5',
})
sys.path.insert(0,str(ROOT))
from fastapi.testclient import TestClient  # noqa
import app  # noqa

c=TestClient(app.app)
assert c.get('/api/meta').json()['version']=='5.7.1'
login=c.post('/api/login',json={'username':'v55admin','password':'V55AdminPassword!123456'})
assert login.status_code==200,login.text
csrf=c.cookies.get('mgc_csrf'); headers={'X-CSRF-Token':csrf}

# Chinese regional comparison is orientation-only and contains validated-style romanization examples.
found=c.get('/api/chinese/foundations').json(); pt=found['putonghua']
assert len(pt['groups'])==10
assert len(pt['comparison_examples'])>=3
hello=next(x for x in pt['comparison_examples'] if x['id']=='hello')
assert hello['standard']['romanization']=='nǐ hǎo'
assert any(v['romanization']=='nei5 hou2' for v in hello['variants'])
assert any(v['text']=='侬好' for v in hello['variants'])
eat=next(x for x in pt['comparison_examples'] if x['id']=='eat')
assert any(v['romanization']=='ci2 fan4' for v in eat['variants'])
assert 'Mandarin-голосом' in pt['comparison_intro']['audio_note']

# Aggregate learning-error telemetry from real rows.
with app.SessionLocal() as db:
    admin=db.scalar(app.select(app.User).where(app.User.username=='v55admin'))
    db.add_all([
        app.PracticeResult(user_id=admin.id,session_id='v55-pr-1',kind='word_match',language='chinese',topic='Качество и APQP',score=4,total=10,created_at=datetime.now(timezone.utc)),
        app.PracticeResult(user_id=admin.id,session_id='v55-pr-2',kind='tone_lab',language='chinese',topic='Pinyin · тоны',score=4,total=5,created_at=datetime.now(timezone.utc)),
    ])
    db.commit()
tele=c.get('/api/admin/learning-error-telemetry').json()
assert tele['sessions']==2 and tele['errors']==7,tele
assert tele['weak_topics'][0]['name']=='Качество и APQP',tele
assert 'not an HR performance rating' in tele['note']

# Synthetic rolling SLI: force error-rate and latency misses without generating stack traces.
now=time.time()
with app._SLO_LOCK:
    app._HTTP_WINDOW.clear()
    for i in range(30):
        app._HTTP_WINDOW.append((now-i, 4200.0 if i<3 else 120.0, 500 if i==0 else 200, '/api/test'))
slo=c.get('/api/admin/slo').json()['slo']
assert slo['samples']==30 and slo['status']=='missed',slo
assert slo['error_rate_percent']>2.0 and slo['p95_ms']>3000,slo

alerts=c.get('/api/admin/alerts').json()
open_rows=[x for x in alerts['alerts'] if x['status']=='open']
keys={x['alert_key'] for x in open_rows}
assert 'slo.error_rate' in keys and 'slo.p95_latency' in keys,(keys,alerts)
ack_target=next(x for x in open_rows if x['alert_key']=='slo.error_rate')
ack=c.patch(f"/api/admin/alerts/{ack_target['id']}/ack",headers=headers,json={'note':'test ack'})
assert ack.status_code==200 and ack.json()['status']=='acknowledged',ack.text

# Recovery state machine: DB/readiness failure -> unavailable -> stability window recovering.
state=app.update_recovery_state(ready_ok=False,checks={'database':'failed'},tts_health={'server_available':True})
assert state['state']=='unavailable',state
state=app.update_recovery_state(ready_ok=True,checks={'database':'ok'},tts_health={'server_available':True})
assert state['state']=='recovering',state

# Dashboard exposes SLO/recovery/alerts and frontend contracts exist.
dash=c.get('/api/admin/it-dashboard')
assert dash.status_code==200,dash.text
d=dash.json(); assert 'slo' in d and 'recovery' in d and 'alerts' in d and d['sla']['contractual'] is False,d
metrics=c.get('/metrics')
assert metrics.status_code==200
for key in ('mgc_slo_availability_percent','mgc_slo_error_rate_percent','mgc_slo_p95_ms','mgc_recovery_state','mgc_pilot_alerts_open'):
    assert key in metrics.text,key
js=(ROOT/'static/app.js').read_text(encoding='utf-8')
assert '/api/admin/learning-error-telemetry' in js and 'data-alert-ack' in js and 'Как один смысл звучит по-разному' in js
css=(ROOT/'static/styles.css').read_text(encoding='utf-8')
assert '.slo-grid' in css and '.dialect-comparisons' in css
print('OK: v5.5 SLO/recovery/alerts/learning-error telemetry and dialect comparison examples')
