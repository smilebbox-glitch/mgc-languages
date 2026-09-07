from __future__ import annotations
import os, sys, tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
DB = Path(tempfile.gettempdir()) / 'mgc_languages_v52_chinese_audio.db'
try: DB.unlink()
except FileNotFoundError: pass
os.environ.update({
    'DATABASE_URL': f'sqlite:///{DB}', 'APP_ENV':'test', 'AUTH_MODE':'local', 'REGISTRATION_ENABLED':'true',
    'MGC_ADMIN_USERNAME':'admin', 'MGC_ADMIN_PASSWORD':'AdminPass123!', 'OIDC_STATE_SECRET':'test-secret-32-bytes-long-enough-0001',
    'TRUSTED_HOSTS':'testserver,localhost,127.0.0.1', 'TTS_ENABLED':'true',
})
from fastapi.testclient import TestClient  # noqa: E402
import app  # noqa: E402


def csrf(c: TestClient):
    return {'X-CSRF-Token': c.cookies.get('mgc_csrf')}

# User learning settings + Chinese foundations.
u = TestClient(app.app)
r = u.post('/api/register', json={'username':'audiolearner','password':'AudioPass123!','display_name':'Audio Learner'})
assert r.status_code == 200, r.text
prefs = u.get('/api/learning/preferences')
assert prefs.status_code == 200 and prefs.json()['show_pinyin'] is True and prefs.json()['show_reading'] is True
r = u.put('/api/learning/preferences', headers=csrf(u), json={'show_pinyin':False,'show_reading':True,'server_audio_enabled':True})
assert r.status_code == 200 and r.json()['show_pinyin'] is False
foundations = u.get('/api/chinese/foundations')
assert foundations.status_code == 200
body = foundations.json()
assert len(body['tones']) == 5 and body['pinyin']['formula'] and body['context']['example']['lesson']
assert any(x['hanzi'] == '质量' for x in body['starter_terms'])

# Both language packs expose a visible reading aid.
zh = u.get('/api/language/chinese/terms?limit=10').json()['items']
en = u.get('/api/language/english/terms?limit=10').json()['items']
assert any(x.get('pronunciation') and x.get('reading') for x in zh), zh[:1]
assert any(x.get('pronunciation') and x.get('reading') for x in en), en[:1]

# Server endpoint must return real WAV when the local engine is available.
status = u.get('/api/pronunciation/status')
assert status.status_code == 200
if status.json()['server_available']:
    wav = u.get('/api/pronunciation/audio', params={'language':'english','text':'assembly line','rate':0.85})
    assert wav.status_code == 200, wav.text
    assert wav.headers['content-type'].startswith('audio/wav')
    assert wav.content[:4] == b'RIFF' and len(wav.content) > 1000
    zh_wav = u.get('/api/pronunciation/audio', params={'language':'chinese','text':'质量','rate':0.72})
    assert zh_wav.status_code == 200 and zh_wav.content[:4] == b'RIFF'

# Admin assigns departments and manager sees only their scope.
admin = TestClient(app.app)
r = admin.post('/api/login', json={'username':'admin','password':'AdminPass123!'})
assert r.status_code == 200, r.text

other = TestClient(app.app)
r = other.post('/api/register', json={'username':'otheruser','password':'OtherPass123!','display_name':'Other User'})
assert r.status_code == 200

# Assign learner -> manager / R&D, other -> Quality.
learner_id = u.get('/api/me').json()['id']
other_id = other.get('/api/me').json()['id']
r = admin.patch(f'/api/admin/users/{learner_id}/role', headers=csrf(admin), json={'role':'manager'})
assert r.status_code == 200, r.text
r = admin.patch(f'/api/admin/users/{learner_id}/department', headers=csrf(admin), json={'department':'R&D'})
assert r.status_code == 200, r.text
r = admin.patch(f'/api/admin/users/{other_id}/department', headers=csrf(admin), json={'department':'Quality'})
assert r.status_code == 200, r.text

manager = TestClient(app.app)
r = manager.post('/api/login', json={'username':'audiolearner','password':'AudioPass123!'})
assert r.status_code == 200 and r.json()['user']['role'] == 'manager'
team = manager.get('/api/manager/team')
assert team.status_code == 200, team.text
assert team.json()['department'] == 'R&D'
ids = {x['id'] for x in team.json()['users']}
assert learner_id in ids and other_id not in ids
forbidden = manager.get(f'/api/manager/team/{other_id}/learning-stats')
assert forbidden.status_code == 403

telemetry = admin.get('/api/admin/pilot-telemetry')
assert telemetry.status_code == 200
assert 'server_tts_available' in telemetry.json() and 'departments' in telemetry.json()
print('OK: v5.2 Pinyin settings, Chinese foundations, real WAV TTS, English/Chinese readings and department-scoped manager RBAC')
