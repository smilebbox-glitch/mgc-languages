from __future__ import annotations
import os, sys, tempfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
DB=Path(tempfile.gettempdir())/'mgc_languages_v56_governance.db'
try: DB.unlink()
except FileNotFoundError: pass
os.environ.update({
    'DATABASE_URL':f'sqlite:///{DB}','AUTO_CREATE_SCHEMA':'true','APP_ENV':'test','AUTH_MODE':'local','REGISTRATION_ENABLED':'true',
    'TRUSTED_HOSTS':'testserver,localhost,127.0.0.1','MGC_ADMIN_USERNAME':'v56admin','MGC_ADMIN_PASSWORD':'V56AdminPassword!123456',
    'MGC_ADMIN_DISPLAY_NAME':'V56 Admin','OIDC_STATE_SECRET':'v56-test-secret-32-bytes-long-0000001','TTS_LEGACY_GET_ENABLED':'false',
    'PILOT_DAILY_GAME_START_CAP':'10','PILOT_DAILY_XP_CAP':'100','PILOT_DAILY_TTS_CAP':'20','PILOT_DAILY_PRACTICE_CAP':'20',
})
sys.path.insert(0,str(ROOT))
from fastapi.testclient import TestClient  # noqa
import app  # noqa

# Content contract: nobody should be able to confuse dialect reference with the learning target.
found=app.CHINESE_FOUNDATIONS
std=found['learning_standard']
assert std['name']=='Путунхуа (普通话)'
assert 'Весь основной китайский курс' in std['primary_message']
assert 'только справка' in std['reference_message']
assert len(found['putonghua']['groups'])==10

c=TestClient(app.app)
assert c.get('/api/meta').json()['version']=='5.7.1'
admin=c.post('/api/login',json={'username':'v56admin','password':'V56AdminPassword!123456'})
assert admin.status_code==200,admin.text
admin_csrf=c.cookies.get('mgc_csrf'); ah={'X-CSRF-Token':admin_csrf}

# Create pilot user in a separate client.
u=TestClient(app.app)
r=u.post('/api/register',json={'username':'pilotuser','password':'PilotUserPass123!','display_name':'Pilot User'})
assert r.status_code==200,r.text
user_id=r.json()['user']['id']
summary=u.get('/api/language/chinese/summary').json()
assert summary['learning_standard']['name']=='Путунхуа (普通话)'
pilot0=u.get('/api/pilot/me').json()
assert pilot0['chinese_standard']['primary_learning_track'] is True
assert pilot0['chinese_standard']['dialects_reference_only'] is True

# Governance: group/wave, membership, feature override and learning assignment.
g=c.post('/api/admin/pilot/groups',headers=ah,json={'name':'R&D Wave 2','department':'R&D','description':'controlled pilot','status':'active','wave':2})
assert g.status_code==200,g.text
gid=g.json()['id']
assert c.post(f'/api/admin/pilot/groups/{gid}/members/{user_id}',headers=ah).status_code==200
assert c.put(f'/api/admin/pilot/groups/{gid}/features/games',headers=ah,json={'enabled':False}).status_code==200
assign=c.post(f'/api/admin/pilot/groups/{gid}/assignments',headers=ah,json={'language':'chinese','track_name':'R&D Putonghua','topic':'R&D / Engineering','target_level':'A2','due_date':'2026-10-31'})
assert assign.status_code==200,assign.text
assignment_id=assign.json()['id']

p=u.get('/api/pilot/me').json()
assert p['wave']==2 and p['features']['games'] is False,p
assert p['assignments'][0]['track_name']=='R&D Putonghua'
blocked=u.post('/api/games/match/start?language=chinese')
assert blocked.status_code==403,blocked.text

# Overlapping active groups use conservative deny-wins semantics.
g2=c.post('/api/admin/pilot/groups',headers=ah,json={'name':'Cross-functional Wave 3','department':'General','description':'overlap safety','status':'active','wave':3})
assert g2.status_code==200,g2.text
gid2=g2.json()['id']
assert c.post(f'/api/admin/pilot/groups/{gid2}/members/{user_id}',headers=ah).status_code==200
assert c.put(f'/api/admin/pilot/groups/{gid2}/features/games',headers=ah,json={'enabled':True}).status_code==200
p_overlap=u.get('/api/pilot/me').json()
assert p_overlap['features']['games'] is False,p_overlap

# Scheduling a wave into the future removes its overrides/assignments from the active rollout.
future_start='2030-01-01T09:00:00+00:00'; future_end='2030-02-01T09:00:00+00:00'
updated=c.patch(f'/api/admin/pilot/groups/{gid2}',headers=ah,json={'starts_at':future_start,'ends_at':future_end})
assert updated.status_code==200 and updated.json()['active'] is False,updated.text
assert u.get('/api/pilot/me').json()['features']['games'] is False

# Reference page does not award XP.
before=u.get('/api/gamification/me').json()['lifetime_xp']
ref=u.get('/api/chinese/foundations')
assert ref.status_code==200
assert u.get('/api/gamification/me').json()['lifetime_xp']==before

# Pilot export and governance summary are usable by Admin.
gov=c.get('/api/admin/pilot/governance-summary').json()
assert gov['groups_active']==1 and gov['groups_total']==2 and gov['memberships']==2 and gov['assignments']==1,gov
assert 'Путунхуа' in gov['chinese_standard']
export=c.get(f'/api/admin/pilot/export.csv?group_id={gid}')
assert export.status_code==200 and 'text/csv' in export.headers['content-type']
text=export.content.decode('utf-8-sig')
assert 'Pilot User' in text and 'R&D Wave 2' in text and 'chinese_putonghua_known' in text.splitlines()[0]

# Admin can reverse an accidental learning-track assignment; the action is audited.
removed=c.delete(f'/api/admin/pilot/groups/{gid}/assignments/{assignment_id}',headers=ah)
assert removed.status_code==200,removed.text
assert c.get('/api/admin/pilot/governance-summary').json()['assignments']==0
audit=c.get('/api/admin/audit?limit=100').json()
assert any(x.get('event_type')=='pilot.assignment.delete' for x in audit),audit

# Direct quota helper is deterministic and returns 429 after cap.
with app.SessionLocal() as db:
    for _ in range(app.PILOT_DAILY_GAME_START_CAP): app._consume_daily_quota(db,user_id,'game_starts',app.PILOT_DAILY_GAME_START_CAP)
    try:
        app._consume_daily_quota(db,user_id,'game_starts',app.PILOT_DAILY_GAME_START_CAP)
        raise AssertionError('quota was not enforced')
    except Exception as exc:
        assert getattr(exc,'status_code',None)==429

js=(ROOT/'static/app.js').read_text(encoding='utf-8')
html=(ROOT/'static/index.html').read_text(encoding='utf-8')
css=(ROOT/'static/styles.css').read_text(encoding='utf-8')
assert 'Вы изучаете Путунхуа (普通话)' in js
assert 'Диалекты в разделе «Информация о китайском» — только справка' in js
assert 'Информация о китайском' in html and '中文 · Путунхуа' in html
assert 'pilotGovernanceHTML' in js and '/api/admin/pilot/export.csv' in js and 'data-pilot-remove-assignment' in js
assert 'data-assign-topic' in js and 'data-assign-due' in js
assert '.putonghua-learning-banner' in css and '.pilot-cohort-strip' in css
print('OK: v5.6 Putonghua clarity, pilot groups/waves, feature flags, assignments, quotas and CSV export')
