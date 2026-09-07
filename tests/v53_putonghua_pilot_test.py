from __future__ import annotations
import os, sys, tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
DB = Path(tempfile.gettempdir()) / 'mgc_languages_v53_putonghua.db'
CACHE = Path(tempfile.gettempdir()) / 'mgc_languages_v53_tts_cache'
try: DB.unlink()
except FileNotFoundError: pass
if CACHE.exists():
    for x in CACHE.glob('*'): x.unlink()
os.environ.update({
    'DATABASE_URL': f'sqlite:///{DB}', 'APP_ENV':'test', 'AUTH_MODE':'local', 'REGISTRATION_ENABLED':'true',
    'OIDC_STATE_SECRET':'test-secret-32-bytes-long-enough-0001', 'TRUSTED_HOSTS':'testserver,localhost,127.0.0.1',
    'TTS_ENABLED':'true', 'TTS_DISK_CACHE_ENABLED':'true', 'TTS_CACHE_DIR':str(CACHE), 'TTS_CONCURRENCY':'2',
    'TTS_FAILURE_THRESHOLD':'3', 'TTS_CIRCUIT_COOLDOWN_SECONDS':'5',
})
from fastapi.testclient import TestClient  # noqa: E402
import app  # noqa: E402

found = app.CHINESE_FOUNDATIONS
pt = found['putonghua']
assert '普通话' in pt['title']
assert len(pt['groups']) == 10
assert {x['zh'] for x in pt['groups']} == {'官话','晋语','吴语','闽语','客家话','粤语','湘语','赣语','徽语','平话土话'}
mandarin = next(x for x in pt['groups'] if x['zh'] == '官话')
assert '四川话' in mandarin['friendly'] and '西南官话' in mandarin['friendly']
assert 'Точного единственного числа нет' in pt['how_many']['simple']
assert '请说普通话' in ''.join(x['a'] for x in pt['mini_facts'])

c = TestClient(app.app)
r = c.get('/health/live')
assert r.status_code == 200 and r.json()['version'] == '5.7.1'
assert 'microphone=()' in r.headers.get('permissions-policy','')
r = c.post('/api/register', json={'username':'putonghua','password':'PutonghuaPass123!','display_name':'Putonghua Learner'})
assert r.status_code == 200, r.text
csrf = c.cookies.get('mgc_csrf')

api_found = c.get('/api/chinese/foundations').json()
assert len(api_found['putonghua']['groups']) == 10
status = c.get('/api/pronunciation/status')
assert status.status_code == 200
sj = status.json()
for key in ('circuit_open','timeout_seconds','concurrency','disk_cache_enabled','runtime'):
    assert key in sj, (key, sj)

if sj['server_available']:
    payload = {'language':'chinese','text':'请说普通话，可以吗？','rate':0.78}
    wav = c.post('/api/pronunciation/audio', headers={'X-CSRF-Token':csrf}, json=payload)
    assert wav.status_code == 200, wav.text
    assert wav.content[:4] == b'RIFF' and len(wav.content) > 512
    assert wav.headers.get('cache-control','') == 'no-store'
    # Clear memory cache so the second request proves the bounded disk cache is usable across process-level cache misses.
    app._synthesize_wav.cache_clear()
    before = app._tts_health(force=True)['runtime']['disk_cache_hits']
    wav2 = c.post('/api/pronunciation/audio', headers={'X-CSRF-Token':csrf}, json=payload)
    assert wav2.status_code == 200 and wav2.content[:4] == b'RIFF'
    after = app._tts_health(force=True)['runtime']['disk_cache_hits']
    assert after >= before + 1, (before, after)
    legacy = c.get('/api/pronunciation/audio', params={'language':'chinese','text':'普通话','rate':0.8})
    assert legacy.status_code == 200 and legacy.headers.get('deprecation') == 'true'

metrics = c.get('/metrics')
assert metrics.status_code == 200
assert 'mgc_tts_success_total' in metrics.text and 'mgc_tts_circuit_open' in metrics.text

js = (ROOT/'static/app.js').read_text(encoding='utf-8')
assert "fetch('/api/pronunciation/audio', {method:'POST'" in js
assert "'/api/pronunciation/audio?language='" not in js
assert 'getUserMedia' not in js and 'SpeechRecognition' not in js
assert 'Путунхуа и диалекты' in js and '10 ОТДЕЛЬНЫХ' in js
compose = (ROOT/'docker-compose.pilot.yml').read_text(encoding='utf-8')
assert 'TTS_CACHE_DIR: /tmp/mgc-tts-cache' in compose and 'TTS_LEGACY_GET_ENABLED:' in compose
assert 'TTS_FAILURE_THRESHOLD' in compose and 'TTS_CONCURRENCY' in compose
print('OK: v5.3 Putonghua/dialect content, no microphone capture, POST TTS privacy, disk cache, circuit telemetry and pilot Compose')
