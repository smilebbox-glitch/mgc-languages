from __future__ import annotations

import os
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB = Path(tempfile.gettempdir()) / 'mgc_languages_v54_reliability.db'
try:
    DB.unlink()
except FileNotFoundError:
    pass

os.environ.update({
    'DATABASE_URL': f'sqlite:///{DB}',
    'AUTO_CREATE_SCHEMA': 'true',
    'APP_ENV': 'development',
    'AUTH_MODE': 'local',
    'REGISTRATION_ENABLED': 'false',
    'OIDC_STATE_SECRET': 'v54-test-state-secret-32-bytes-long-0001',
    'MGC_ADMIN_USERNAME': 'v54admin',
    'MGC_ADMIN_PASSWORD': 'V54AdminPassword!123456',
    'MGC_ADMIN_DISPLAY_NAME': 'V54 Admin',
    'TTS_LEGACY_GET_ENABLED': 'false',
    'TTS_CACHE_PERSISTENCE': 'ephemeral',
    'AUDIT_RETENTION_DAYS': '30',
    'OPERATIONAL_EVENT_RETENTION_DAYS': '7',
    'NUDGE_RETENTION_DAYS': '14',
})

sys.path.insert(0, str(ROOT))
from fastapi.testclient import TestClient  # noqa: E402
import app  # noqa: E402

c = TestClient(app.app)
meta = c.get('/api/meta').json()
assert meta['version'] == '5.7.1'
assert meta['voice_recording_enabled'] is False
assert meta['reliability_profile'] == 'pilot-v5.7.1'
foundations = c.get('/api/chinese/foundations')
assert foundations.status_code == 401  # auth remains required

login = c.post('/api/login', json={'username':'v54admin','password':'V54AdminPassword!123456'})
assert login.status_code == 200, login.text
csrf = c.cookies.get('mgc_csrf')
headers = {'X-CSRF-Token': csrf}

foundations = c.get('/api/chinese/foundations')
assert foundations.status_code == 200
assert foundations.json()['title'] == 'Информация о китайском'
assert len(foundations.json().get('putonghua',{}).get('groups',[])) == 10

# Readiness now reports DB latency as a first-class signal.
ready = c.get('/health/ready')
assert ready.status_code == 200, ready.text
assert 'database_latency_ms' in ready.json()['checks']

# Persistent operational event telemetry.
app.operational_event('test.failure', severity='error', component='test', status_code=503, path='/test', detail='synthetic')
events = c.get('/api/admin/operational-events')
assert events.status_code == 200
assert any(x['event_type'] == 'test.failure' and x['component'] == 'test' for x in events.json())

dash = c.get('/api/admin/it-dashboard')
assert dash.status_code == 200, dash.text
data = dash.json()
assert 'readiness' in data and 'database' in data and 'tts' in data and 'maintenance' in data
assert data['events_24h']['total'] >= 1

# Retention cleanup: create deliberately expired/old rows and verify dry-run then delete.
with app.SessionLocal() as db:
    admin = db.scalar(app.select(app.User).where(app.User.username == 'v54admin'))
    old = datetime.now(timezone.utc) - timedelta(days=45)
    db.add(app.LoginSession(token_hash='0'*64, user_id=admin.id, expires_at=old))
    db.add(app.AuditLog(event_type='old.audit', actor_user_id=admin.id, created_at=old))
    db.add(app.OperationalEvent(event_type='old.event', severity='warning', component='test', created_at=old))
    db.add(app.LearningNudge(user_id=admin.id, title='old', body='old', created_at=old))
    db.commit()

preview = c.post('/api/admin/maintenance/cleanup?dry_run=true', headers=headers)
assert preview.status_code == 200, preview.text
counts = preview.json()['counts']
assert counts['expired_sessions'] >= 1 and counts['old_audit'] >= 1 and counts['old_operational_events'] >= 1 and counts['old_nudges'] >= 1
run = c.post('/api/admin/maintenance/cleanup?dry_run=false', headers=headers)
assert run.status_code == 200, run.text
with app.SessionLocal() as db:
    assert db.scalar(app.select(app.func.count()).select_from(app.LoginSession).where(app.LoginSession.token_hash == '0'*64)) == 0
    assert db.scalar(app.select(app.func.count()).select_from(app.AuditLog).where(app.AuditLog.event_type == 'old.audit')) == 0
    assert db.scalar(app.select(app.func.count()).select_from(app.OperationalEvent).where(app.OperationalEvent.event_type == 'old.event')) == 0

js = (ROOT/'static/app.js').read_text(encoding='utf-8')
css = (ROOT/'static/styles.css').read_text(encoding='utf-8')
compose = (ROOT/'docker-compose.pilot.yml').read_text(encoding='utf-8')
assert '/api/admin/it-dashboard' in js and 'serviceStatus' in js and 'maintenanceRun' in js
assert '.service-status' in css and '.it-dashboard' in css
assert '  maintenance:' in compose and 'maintenance_cleanup.py' in compose
assert 'DB_CONNECT_TIMEOUT_SECONDS:' in compose and 'DB_STATEMENT_TIMEOUT_MS:' in compose
assert 'EXPECTED_ALEMBIC_HEAD: c57d0a31f570' in compose

print('OK: v5.4 reliability, retention, IT dashboard and Chinese information rename')
