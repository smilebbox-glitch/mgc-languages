from __future__ import annotations
import os, sys, tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
DB=Path(tempfile.gettempdir())/'mgc_languages_v57_auth_matrix.db'
try: DB.unlink()
except FileNotFoundError: pass
os.environ.update({
    'DATABASE_URL':f'sqlite:///{DB}','AUTO_CREATE_SCHEMA':'true','APP_ENV':'pilot','AUTH_MODE':'local','REGISTRATION_ENABLED':'true',
    'TRUSTED_HOSTS':'testserver,localhost,127.0.0.1','MGC_ADMIN_USERNAME':'matrixadmin','MGC_ADMIN_PASSWORD':'MatrixAdminPassword!123456',
    'MGC_ADMIN_DISPLAY_NAME':'Matrix Admin','OIDC_STATE_SECRET':'matrix-secret-32-bytes-long-000001','TTS_LEGACY_GET_ENABLED':'false',
    'TERM_APPROVAL_REQUIRED':'true','RLS_ENABLED':'true','METRICS_TOKEN':'matrixmetrics',
})
sys.path.insert(0,str(ROOT))
from fastapi.testclient import TestClient  # noqa
import app  # noqa

admin=TestClient(app.app)
assert admin.post('/api/login',json={'username':'matrixadmin','password':'MatrixAdminPassword!123456'}).status_code==200
admin_h={'X-CSRF-Token':admin.cookies.get('mgc_csrf')}

def reg(username:str, display:str):
    c=TestClient(app.app)
    r=c.post('/api/register',json={'username':username,'password':'StrongPass123!','display_name':display})
    assert r.status_code==200,r.text
    return c,r.json()['user']['id']

user,u_id=reg('matrix_user','Matrix User')
other,o_id=reg('matrix_other','Matrix Other')
manager,m_id=reg('matrix_manager','Matrix Manager')
editor,e_id=reg('matrix_editor','Matrix Editor')
for uid,dep in [(u_id,'R&D'),(o_id,'Quality'),(m_id,'R&D'),(e_id,'Language')]:
    r=admin.patch(f'/api/admin/users/{uid}/department',headers=admin_h,json={'department':dep}); assert r.status_code==200,r.text
for uid,role in [(m_id,'manager'),(e_id,'editor')]:
    r=admin.patch(f'/api/admin/users/{uid}/role',headers=admin_h,json={'role':role}); assert r.status_code==200,r.text
manager=TestClient(app.app); assert manager.post('/api/login',json={'username':'matrix_manager','password':'StrongPass123!'}).status_code==200
editor=TestClient(app.app); assert editor.post('/api/login',json={'username':'matrix_editor','password':'StrongPass123!'}).status_code==200
user=TestClient(app.app); assert user.post('/api/login',json={'username':'matrix_user','password':'StrongPass123!'}).status_code==200
clients={'user':user,'manager':manager,'editor':editor,'admin':admin}
csrf={name:{'X-CSRF-Token':c.cookies.get('mgc_csrf')} for name,c in clients.items()}

checks=0
def expect(role:str, method:str, path:str, expected:int, **kwargs):
    global checks
    c=clients[role]
    headers=dict(kwargs.pop('headers',{}))
    if method in {'POST','PATCH','PUT','DELETE'}: headers.update(csrf[role])
    r=c.request(method,path,headers=headers,**kwargs)
    assert r.status_code==expected,(role,method,path,expected,r.status_code,r.text[:500])
    checks+=1
    return r

# Administrative visibility.
for role,code in {'user':403,'manager':403,'editor':403,'admin':200}.items(): expect(role,'GET','/api/admin/users',code)
for role,code in {'user':403,'manager':200,'editor':403,'admin':200}.items(): expect(role,'GET','/api/manager/team',code)
for role,code in {'user':403,'manager':403,'editor':403,'admin':200}.items(): expect(role,'GET','/api/admin/pilot/groups',code)
for role,code in {'user':403,'manager':403,'editor':200,'admin':200}.items(): expect(role,'GET','/api/admin/learning/question-quality',code)

# Department boundary: Manager sees own R&D employee, never Quality employee.
expect('manager','GET',f'/api/manager/team/{u_id}/learning-stats',200)
expect('manager','GET',f'/api/manager/team/{o_id}/learning-stats',403)
expect('admin','GET',f'/api/manager/team/{o_id}/learning-stats',200)

# Role/department mutation is Admin-only.
for role in ('user','manager','editor'):
    expect(role,'PATCH',f'/api/admin/users/{u_id}/department',403,json={'department':'Quality'})
    expect(role,'PATCH',f'/api/admin/users/{u_id}/role',403,json={'role':'manager'})

# Terminology governance: Editor can author/review, but cannot approve/delete; Admin can approve/delete.
payload={
    'language':'chinese','shop':'R&D','topic':'R&D / Engineering','subtopic':'Validation','level':'A2',
    'term':'矩阵验证','pronunciation':'jǔzhèn yànzhèng','reading':'цзюй-чжэнь янь-чжэн','translation':'матричная проверка',
    'example':'请进行矩阵验证。','example_translation':'Проведите матричную проверку.','tags':'matrix',
    'source_type':'engineering_document','source_ref':'AUTH-MATRIX-001','status':'published'
}
for role in ('user','manager'):
    expect(role,'POST','/api/admin/terms',403,json=payload)
created=expect('editor','POST','/api/admin/terms',200,json=payload).json(); tid=created['db_id']
assert created['status']=='review'
expect('editor','POST',f'/api/admin/terms/{tid}/approve',403,json={'note':'should fail'})
expect('manager','POST',f'/api/admin/terms/{tid}/approve',403,json={'note':'should fail'})
expect('admin','POST',f'/api/admin/terms/{tid}/approve',200,json={'note':'approved by Admin'})
expect('editor','DELETE',f'/api/admin/terms/{tid}',403)

# Pilot rollout mutations are Admin-only.
group_payload={'name':'Matrix Wave','wave':7,'department':'R&D','status':'draft','description':'auth matrix','starts_at':None,'ends_at':None}
for role in ('user','manager','editor'):
    expect(role,'POST','/api/admin/pilot/groups',403,json=group_payload)
g=expect('admin','POST','/api/admin/pilot/groups',200,json=group_payload).json(); gid=g['id']
for role in ('user','manager','editor'):
    expect(role,'POST',f'/api/admin/pilot/groups/{gid}/members/{u_id}',403,json={})
expect('admin','POST',f'/api/admin/pilot/groups/{gid}/members/{u_id}',200,json={})

# IT/operations endpoints are Admin-only.
for path in ('/api/admin/it-dashboard','/api/admin/system/summary','/api/admin/alerts','/api/admin/audit/verify-chain'):
    for role in ('user','manager','editor'):
        expect(role,'GET',path,403)
    expect('admin','GET',path,200)

assert checks >= 40, checks
print(f'OK: v5.7 authorization matrix {checks} role/endpoint/department checks')
