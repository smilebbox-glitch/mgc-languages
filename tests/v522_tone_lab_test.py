from __future__ import annotations
import os, sys, tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
DB=Path(tempfile.gettempdir())/'mgc_languages_v522_tone_lab.db'
try: DB.unlink()
except FileNotFoundError: pass
os.environ['DATABASE_URL']=f'sqlite:///{DB}'
os.environ['MGC_ADMIN_USERNAME']='admin'
os.environ['MGC_ADMIN_PASSWORD']='AdminPass123'
from fastapi.testclient import TestClient
import app
c=TestClient(app.app)
def csrf():
    t=c.cookies.get('mgc_csrf'); return {'X-CSRF-Token':t} if t else {}
r=c.post('/api/register',json={'username':'tonelab','password':'ToneLabPass123','display_name':'Tone Lab'})
assert r.status_code==200,r.text
r=c.post('/api/practice/result',headers=csrf(),json={'session_id':'tone-lab-test-001','kind':'tone_lab','language':'chinese','topic':'Pinyin · тоны','score':4,'total':5})
assert r.status_code==200,r.text
j=r.json(); assert j['awarded']>=8 and j['profile']['lifetime_xp']==j['awarded']
r2=c.post('/api/practice/result',headers=csrf(),json={'session_id':'tone-lab-test-001','kind':'tone_lab','language':'chinese','topic':'Pinyin · тоны','score':4,'total':5})
assert r2.status_code==200 and r2.json()['duplicate'] is True
js=(ROOT/'static/app.js').read_text(encoding='utf-8')
assert 'function toneLabStart(data)' in js
assert "kind:'tone_lab'" in js
assert 'data-tone-choice' in js
css=(ROOT/'static/styles.css').read_text(encoding='utf-8')
assert '.tone-lab-card' in css and '.tone-choice.correct' in css
print('OK: v5.2.2 Tone Lab practice, XP idempotency and frontend contract')
