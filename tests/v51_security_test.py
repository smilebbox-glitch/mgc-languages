from __future__ import annotations
import os, sys, tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
DB = Path(tempfile.gettempdir()) / "mgc_languages_v51_security.db"
try: DB.unlink()
except FileNotFoundError: pass
os.environ.update({
    "DATABASE_URL": f"sqlite:///{DB}",
    "APP_ENV": "test",
    "AUTH_MODE": "local",
    "REGISTRATION_ENABLED": "true",
    "MGC_ADMIN_USERNAME": "admin",
    "MGC_ADMIN_PASSWORD": "AdminPass123!",
    "OIDC_STATE_SECRET": "test-secret-at-least-32-bytes-long-12345",
    "TRUSTED_HOSTS": "testserver,localhost,127.0.0.1",
})
from fastapi.testclient import TestClient  # noqa: E402
import app  # noqa: E402

c = TestClient(app.app)
r = c.get('/health/live')
assert r.status_code == 200
for header in ('x-request-id','x-content-type-options','x-frame-options','content-security-policy','permissions-policy'):
    assert header in r.headers, (header, r.headers)
assert 'microphone=()' in r.headers['permissions-policy']

r = c.post('/api/register', json={'username':'securityuser','password':'SecurityPass123!','display_name':'Security User'})
assert r.status_code == 200, r.text
csrf = c.cookies.get('mgc_csrf')
assert csrf and c.cookies.get('mgc_session')

# Mutating cookie-authenticated request without CSRF must fail.
r = c.post('/api/me/language', json={'language':'english'})
assert r.status_code == 403, r.text
# Valid CSRF succeeds.
r = c.post('/api/me/language', headers={'X-CSRF-Token': csrf}, json={'language':'english'})
assert r.status_code == 200, r.text

# Admin audit contains privileged/auth actions and is admin-only.
a = TestClient(app.app)
r = a.post('/api/login', json={'username':'admin','password':'AdminPass123!'})
assert r.status_code == 200, r.text
ac = a.cookies.get('mgc_csrf')
r = a.post('/api/admin/terms', headers={'X-CSRF-Token': ac}, json={
    'language':'english','shop':'Quality','topic':'Quality','subtopic':'Pilot','level':'A1',
    'term':'containment','translation':'сдерживающие меры','status':'published'
})
assert r.status_code == 200, r.text
r = a.get('/api/admin/audit')
assert r.status_code == 200, r.text
assert any(x['event_type'] == 'term.create' for x in r.json())
summary = a.get('/api/admin/system/summary')
assert summary.status_code == 200, summary.text
assert summary.json()['csrf_enabled'] is True and summary.json()['version'] == '5.7.1'

# CSV import path: upload, audit and published content.
csv_data = b'language,shop,topic,level,term,translation,status\nenglish,Assembly,Production,A1,fixture,prisposoblenie,published\n'
r = a.post('/api/admin/terms/import?default_language=english', headers={'X-CSRF-Token': ac}, files={'file':('terms.csv', csv_data, 'text/csv')})
assert r.status_code == 200, r.text
assert r.json()['created'] == 1

# Metrics are available and do not require auth by design for internal scraping.
r = c.get('/metrics')
assert r.status_code == 200 and 'mgc_http_requests_total' in r.text

# Local brute-force limiter triggers after repeated failures.
b = TestClient(app.app)
statuses=[]
for _ in range(12):
    statuses.append(b.post('/api/login', json={'username':'missing','password':'wrongpass'}).status_code)
assert 429 in statuses, statuses

print('OK: v5.2 security headers, CSRF, audit, metrics and rate limiting')
