from __future__ import annotations
import os, sys, tempfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
DB=Path(tempfile.gettempdir())/'mgc_languages_v57.db'
try: DB.unlink()
except FileNotFoundError: pass
os.environ.update({
    'DATABASE_URL':f'sqlite:///{DB}','AUTO_CREATE_SCHEMA':'true','APP_ENV':'pilot','AUTH_MODE':'local','REGISTRATION_ENABLED':'true',
    'TRUSTED_HOSTS':'testserver,localhost,127.0.0.1','MGC_ADMIN_USERNAME':'v57admin','MGC_ADMIN_PASSWORD':'V57AdminPassword!123456',
    'MGC_ADMIN_DISPLAY_NAME':'V57 Admin','OIDC_STATE_SECRET':'v57-test-secret-32-bytes-long-0000001','TTS_LEGACY_GET_ENABLED':'false',
    'TERM_APPROVAL_REQUIRED':'true','RLS_ENABLED':'true','QUESTION_QUALITY_MIN_ATTEMPTS':'10','METRICS_TOKEN':'v57metrics',
})
sys.path.insert(0,str(ROOT))
from fastapi.testclient import TestClient  # noqa
import app  # noqa

assert app.APP_VERSION=='5.7.1'
assert app.EXPECTED_ALEMBIC_HEAD=='c57d0a31f570'

# Admin + four role/persona clients.
admin=TestClient(app.app)
r=admin.post('/api/login',json={'username':'v57admin','password':'V57AdminPassword!123456'})
assert r.status_code==200,r.text
ah={'X-CSRF-Token':admin.cookies.get('mgc_csrf')}

def register(username, display):
    c=TestClient(app.app)
    rr=c.post('/api/register',json={'username':username,'password':'StrongPass123!','display_name':display})
    assert rr.status_code==200,rr.text
    return c, rr.json()['user']['id']

u1,u1id=register('worker_rnd','Worker R&D')
u2,u2id=register('worker_quality','Worker Quality')
mgr,mgrid=register('manager_rnd','Manager R&D')
ed,edid=register('language_editor','Language Editor')
for uid,dep in [(u1id,'R&D'),(u2id,'Quality'),(mgrid,'R&D'),(edid,'Language')]:
    rr=admin.patch(f'/api/admin/users/{uid}/department',headers=ah,json={'department':dep}); assert rr.status_code==200,rr.text
for uid,role in [(mgrid,'manager'),(edid,'editor')]:
    rr=admin.patch(f'/api/admin/users/{uid}/role',headers=ah,json={'role':role}); assert rr.status_code==200,rr.text
# Re-login role-bearing users so their subsequent auth context reflects DB role.
mgr=TestClient(app.app); assert mgr.post('/api/login',json={'username':'manager_rnd','password':'StrongPass123!'}).status_code==200
ed=TestClient(app.app); assert ed.post('/api/login',json={'username':'language_editor','password':'StrongPass123!'}).status_code==200
eh={'X-CSRF-Token':ed.cookies.get('mgc_csrf')}

# Authorization matrix at application layer: user cannot see manager/admin; manager is department-scoped.
assert u1.get('/api/admin/users').status_code==403
assert u1.get('/api/manager/team').status_code==403
team=mgr.get('/api/manager/team'); assert team.status_code==200,team.text
names={x['username'] for x in team.json()['users']}
assert 'worker_rnd' in names and 'worker_quality' not in names,names
assert mgr.get(f'/api/manager/team/{u1id}/learning-stats').status_code==200
assert mgr.get(f'/api/manager/team/{u2id}/learning-stats').status_code==403
assert ed.get('/api/admin/users').status_code==403

# RLS is additionally encoded at PostgreSQL schema level.
migration=(ROOT/'alembic/versions/c57d0a31f570_v5_7_security_data_integrity.py').read_text()
assert 'FORCE ROW LEVEL SECURITY' in migration
assert "current_setting('app.department', true)" in migration
assert 'term_progress' in migration and 'question_attempts' in migration and 'srs_cards' in migration

# Content governance: Editor cannot publish directly in pilot. Admin approves; revisions and rollback are preserved.
create=ed.post('/api/admin/terms',headers=eh,json={
    'language':'chinese','shop':'R&D','topic':'R&D / Engineering','subtopic':'Validation','level':'A2',
    'term':'验证','pronunciation':'yànzhèng','reading':'янь-чжэн','translation':'валидация / проверка',
    'example':'请验证这个方案。','example_translation':'Пожалуйста, проверьте это решение.','tags':'R&D',
    'source_type':'engineering_document','source_ref':'ENG-SPEC-001','status':'published'
})
assert create.status_code==200,create.text
term=create.json(); tid=term['db_id']; assert term['status']=='review',term
approve=admin.post(f'/api/admin/terms/{tid}/approve',headers=ah,json={'note':'Checked by pilot language owner'})
assert approve.status_code==200 and approve.json()['status']=='published',approve.text
revs=admin.get(f'/api/admin/terms/{tid}/revisions'); assert revs.status_code==200,revs.text
assert len(revs.json()['revisions'])>=2 and revs.json()['reviews'][0]['decision']=='approved'
# Editor update sends it back to review.
update=ed.patch(f'/api/admin/terms/{tid}',headers=eh,json={
    'language':'chinese','shop':'R&D','topic':'R&D / Engineering','subtopic':'Validation','level':'A2',
    'term':'验证','pronunciation':'yànzhèng','reading':'янь-чжэн','translation':'проверка / валидация',
    'example':'请验证这个方案。','example_translation':'Пожалуйста, проверьте это решение.','tags':'R&D,validated',
    'source_type':'engineering_document','source_ref':'ENG-SPEC-002','status':'published'
})
assert update.status_code==200 and update.json()['status']=='review',update.text
revs2=admin.get(f'/api/admin/terms/{tid}/revisions').json()['revisions']; assert len(revs2)>len(revs.json()['revisions'])
rollback=admin.post(f'/api/admin/terms/{tid}/rollback/{revs2[-1]["revision_no"]}',headers=ah)
assert rollback.status_code==200 and rollback.json()['status']=='review',rollback.text

# Adaptive SRS: normal user marks a real Putonghua term and receives deterministic scheduling.
terms=u1.get('/api/language/chinese/terms?limit=5').json()['items']
term0=terms[0]; uh={'X-CSRF-Token':u1.cookies.get('mgc_csrf')}
sp=u1.post('/api/language/chinese/progress',headers=uh,json={'term_id':term0['id'],'status':'known'})
assert sp.status_code==200,sp.text
rv=u1.post('/api/review/result',headers=uh,json={'language':'chinese','term_id':term0['id'],'quality':5})
assert rv.status_code==200,rv.text
assert rv.json()['interval_days']>=1 and rv.json()['ease_factor_pct']>=130
with app.SessionLocal() as db:
    card=db.scalar(app.select(app.SRSCard).where(app.SRSCard.user_id==u1id,app.SRSCard.term_id==term0['id']))
    assert card and card.repetitions>=2 and card.due_at

# Question quality telemetry flags repeated low-quality/low-accuracy items without exposing selected answers.
for i in range(12):
    qr=u1.post('/api/learning/question-attempt',headers=uh,json={
        'session_id':f'q-{i}','question_id':'pilot-q-hard-1','term_id':term0['id'],'language':'chinese',
        'topic':term0['topic'],'kind':'quiz','correct':i<2,'response_ms':1200+i*10,'selected':'sensitive answer text'
    })
    assert qr.status_code==200,qr.text
quality=admin.get('/api/admin/learning/question-quality?language=chinese')
assert quality.status_code==200,quality.text
q=next(x for x in quality.json()['items'] if x['question_id']=='pilot-q-hard-1')
assert q['attempts']==12 and q['flag']=='review_low_accuracy',q
with app.SessionLocal() as db:
    a=db.scalar(app.select(app.QuestionAttempt).where(app.QuestionAttempt.question_id=='pilot-q-hard-1'))
    assert a.selected_hash and len(a.selected_hash)==64

# Audit chain is verifiable after privileged actions.
chain=admin.get('/api/admin/audit/verify-chain')
assert chain.status_code==200 and chain.json()['ok'] is True,chain.text

# Retention deletes an old prefix but persists an anchor so the surviving chain remains verifiable.
with app.SessionLocal() as db:
    oldest=db.scalars(app.select(app.AuditLog).order_by(app.AuditLog.id.asc()).limit(2)).all()
    assert len(oldest)==2
    old_at=app.datetime.now(app.timezone.utc)-app.timedelta(days=app.AUDIT_RETENTION_DAYS+5)
    for row in oldest: row.created_at=old_at
    db.commit()
cleanup=admin.post('/api/admin/maintenance/cleanup?dry_run=false',headers=ah)
assert cleanup.status_code==200 and cleanup.json()['counts']['old_audit']>=2,cleanup.text
chain_after=admin.get('/api/admin/audit/verify-chain')
assert chain_after.status_code==200 and chain_after.json()['ok'] is True,chain_after.text
with app.SessionLocal() as db:
    anchor=db.get(app.AuditAnchor,1)
    assert anchor and anchor.last_deleted_id and len(anchor.last_deleted_hash)==64

# Technical summary exposes new pilot controls, but OTel stays optional.
sysinfo=admin.get('/api/admin/system/summary').json()
assert sysinfo['rls_enabled'] is True and sysinfo['term_approval_required'] is True
assert 'otel' in sysinfo

print('OK: v5.7 RLS contract, authorization matrix, term approval/versioning, audit chain, adaptive SRS and question-quality telemetry')
