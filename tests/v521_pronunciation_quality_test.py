from __future__ import annotations
import os, sys, tempfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
DB=Path(tempfile.gettempdir())/'mgc_languages_v521_pronunciation.db'
try: DB.unlink()
except FileNotFoundError: pass
os.environ.update({
    'DATABASE_URL':f'sqlite:///{DB}', 'APP_ENV':'test', 'AUTH_MODE':'local', 'REGISTRATION_ENABLED':'true',
    'OIDC_STATE_SECRET':'test-secret-32-bytes-long-enough-0001', 'TRUSTED_HOSTS':'testserver,localhost,127.0.0.1',
    'TTS_ENABLED':'true',
})
from fastapi.testclient import TestClient  # noqa: E402
import app  # noqa: E402

# Beginner reading aids should be useful for common automotive language.
assert app.pinyin_to_ru_approx('zhìliàng') == 'чжи-лян'
assert app.pinyin_to_ru_approx('hànjiē') == 'хань-цзе'
assert app.pinyin_to_ru_approx('quèrèn') == 'цюэ-жэнь'
assert app.pinyin_to_ru_approx('wèntí') == 'вэнь-ти'
assert app.english_pronunciation('PPAP')['reading'] == 'пи-пи-эй-пи'
assert app.english_pronunciation('CMM')['reading'] == 'си-эм-эм'

found=app.CHINESE_FOUNDATIONS
initials=[x for group in found['initials'] for x in group['items']]
finals=[x for group in found['finals'] for x in group['items']]
assert {'g','k','h','j','q','x','zh','ch','sh','r','z','c','s'} <= {x['pinyin'] for x in initials}
assert all(x.get('example_hanzi') and x.get('example_pinyin') and x.get('example_reading') for x in initials)
assert all(x.get('example_hanzi') and x.get('example_pinyin') and x.get('example_reading') for x in finals)
assert found.get('sound_advice',{}).get('items') and found.get('mini_path')

c=TestClient(app.app)
r=c.post('/api/register',json={'username':'pronquality','password':'PronPass123!','display_name':'Pron Quality'})
assert r.status_code==200,r.text
status=c.get('/api/pronunciation/status')
assert status.status_code==200,status.text
sj=status.json()
assert 'language_checks' in sj and set(sj['language_checks'])=={'chinese','english'}
if sj['server_available']:
    for lang,text in [('chinese','质量'),('english','PPAP')]:
        r=c.post('/api/pronunciation/audio',headers={'X-CSRF-Token':c.cookies.get('mgc_csrf')},json={'language':lang,'text':text,'rate':0.78})
        assert r.status_code==200,r.text
        assert r.content[:4]==b'RIFF' and len(r.content)>512
        assert r.headers.get('x-tts-engine')
        assert r.headers.get('x-tts-voice')
        assert r.headers.get('cache-control','') == 'no-store'

js=(ROOT/'static/app.js').read_text(encoding='utf-8')
assert 'AbortController' in js and "setTimeout(function () { controller.abort(); }, 6000)" in js
assert js.count("esc(item.pronunciation) + '</div>' : '') +") >= 1
# The specific duplicate that existed in v5.2 must not return.
needle="(item.pronunciation ? '<div class=\"' + pronunciationClass + '\">' + esc(item.pronunciation) + '</div>' : '') +"
assert js.count(needle)==1
print('OK: v5.2.1 sound-map examples, technical acronym reading, TTS self-test/cache headers and resilient browser fallback')
