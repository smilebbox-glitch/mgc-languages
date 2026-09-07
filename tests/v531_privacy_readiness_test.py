from __future__ import annotations
import os, sys, tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
DB = Path(tempfile.gettempdir()) / 'mgc_languages_v531_privacy.db'
try: DB.unlink()
except FileNotFoundError: pass
CACHE = Path(tempfile.gettempdir()) / 'mgc-languages-v531-cache'
os.environ.update({
    'DATABASE_URL': f'sqlite:///{DB}',
    'APP_ENV': 'pilot',
    'AUTH_MODE': 'local',
    'REGISTRATION_ENABLED': 'true',
    'OIDC_STATE_SECRET': 'pilot-secret-32-bytes-long-enough-0001',
    'TRUSTED_HOSTS': 'testserver,localhost,127.0.0.1',
    'TTS_LEGACY_GET_ENABLED': 'false',
    'TTS_CACHE_PERSISTENCE': 'ephemeral',
    'TTS_CACHE_DIR': str(CACHE),
    'TTS_DISK_CACHE_ENABLED': 'true',
    'READY_REQUIRE_SCHEMA_HEAD': 'false',
})
from fastapi.testclient import TestClient  # noqa: E402
import app  # noqa: E402

c = TestClient(app.app)
live = c.get('/health/live')
assert live.status_code == 200 and live.json()['version'] == '5.7.1'
ready = c.get('/health/ready')
assert ready.status_code == 200, ready.text
checks = ready.json()['checks']
assert checks['tts_legacy_get'] == 'disabled', checks
assert checks['tts_cache'] == 'ok', checks
assert checks['tts_cache_persistence'] == 'ephemeral', checks

reg = c.post('/api/register', json={'username':'privacy531','password':'PrivacyPass123!','display_name':'Privacy Test'})
assert reg.status_code == 200, reg.text
meta = c.get('/api/meta').json()
assert meta['version'] == '5.7.1'
assert meta['voice_recording_enabled'] is False
assert meta['pronunciation_transport'] == 'POST'
assert meta['legacy_tts_get_enabled'] is False
assert meta['tts_cache_persistence'] == 'ephemeral'

openapi = c.get('/openapi.json').json()
ops = openapi['paths']['/api/pronunciation/audio']
assert 'post' in ops and 'get' not in ops, ops
legacy = c.get('/api/pronunciation/audio', params={'language':'chinese','text':'普通话'})
assert legacy.status_code == 404, legacy.text

status = c.get('/api/pronunciation/status').json()
assert status['cache_writable'] is True, status
assert status['cache_persistence'] == 'ephemeral', status
metrics = c.get('/metrics')
assert metrics.status_code == 200 and 'mgc_tts_cache_writable' in metrics.text
print('OK: v5.3.1 pilot privacy gate, POST-only pronunciation, ephemeral cache and readiness contract')
