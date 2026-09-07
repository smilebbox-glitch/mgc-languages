from __future__ import annotations

import inspect
import os
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
DB = Path(tempfile.gettempdir()) / "mgc_languages_v577_services.db"
try:
    DB.unlink()
except FileNotFoundError:
    pass

os.environ.update({
    "DATABASE_URL": f"sqlite:///{DB}",
    "AUTO_CREATE_SCHEMA": "true",
    "APP_ENV": "pilot",
    "AUTH_MODE": "local",
    "REGISTRATION_ENABLED": "true",
    "TRUSTED_HOSTS": "testserver,localhost,127.0.0.1",
    "MGC_ADMIN_USERNAME": "v577admin",
    "MGC_ADMIN_PASSWORD": "V577AdminPassword!123456",
    "MGC_ADMIN_DISPLAY_NAME": "V577 Admin",
    "OIDC_STATE_SECRET": "v577-service-layer-secret-32-bytes-001",
    "TTS_LEGACY_GET_ENABLED": "false",
    "TERM_APPROVAL_REQUIRED": "true",
    "RLS_ENABLED": "true",
    "METRICS_TOKEN": "v577metrics",
    "TTS_CACHE_PERSISTENCE": "ephemeral",
})
sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient  # noqa: E402
import app  # noqa: E402
import asgi  # noqa: E402

assert asgi.app is app.app
assert asgi.SERVICE_BINDING_REPORT.ok
assert asgi.SERVICE_BINDING_REPORT.user_view_bound
assert asgi.SERVICE_BINDING_REPORT.user_stats_bound
assert asgi.SERVICE_BINDING_REPORT.manager_policy_bound
assert asgi.SERVICE_BINDING_REPORT.terminology_view_bound
assert asgi.SERVICE_BINDING_REPORT.terms_query_bound
assert asgi.SERVICE_BINDING_REPORT.revision_bound
assert asgi.SERVICE_BINDING_REPORT.model_contract_preserved
assert app.user_view is app.MGC_USER_SERVICE_BINDINGS.user_view
assert app.user_admin_stats is app.MGC_USER_SERVICE_BINDINGS.user_admin_stats
assert app.terms_for is app.MGC_TERMINOLOGY_SERVICE_BINDINGS.terms_for
assert app.record_term_revision is app.MGC_TERMINOLOGY_SERVICE_BINDINGS.record_term_revision
assert app.user_view.__module__ == "mgc.services.users"
assert app.terms_for.__module__ == "mgc.services.terminology"

# Runtime ordering contract: auth session responses captured the extracted service user_view.
session_closure = inspect.getclosurevars(app.create_login_session)
assert session_closure.nonlocals.get("user_view") is app.user_view

admin = TestClient(asgi.app)
login = admin.post("/api/login", json={"username": "v577admin", "password": "V577AdminPassword!123456"})
assert login.status_code == 200, login.text
admin_headers = {"X-CSRF-Token": admin.cookies.get("mgc_csrf")}

user = TestClient(asgi.app)
register = user.post(
    "/api/register",
    json={"username": "v577user", "password": "StrongPass123!", "display_name": "Service User"},
)
assert register.status_code == 200, register.text
registered = register.json()["user"]
assert set(registered) == {"id", "username", "display_name", "role", "department", "preferred_language"}

users = admin.get("/api/admin/users")
assert users.status_code == 200, users.text
row = next(item for item in users.json() if item["id"] == registered["id"])
assert row["username"] == "v577user"
assert "terms_known" in row and "best_exam" in row and "notification_mode" in row

payload = {
    "language": "english",
    "topic": "Service Layer v5.7.7",
    "term": "service boundary torque check",
    "translation": "проверка момента на границе сервиса",
    "status": "published",
}
created = admin.post("/api/admin/terms", headers=admin_headers, json=payload)
assert created.status_code == 200, created.text
term = created.json()
term_db_id = term["db_id"]
term_public_id = term["id"]
assert term["topic"] == "Service Layer v5.7.7"

listed = user.get(
    "/api/language/english/terms",
    params={"topic": "Service Layer v5.7.7", "limit": 50},
)
assert listed.status_code == 200, listed.text
assert listed.json()["total"] == 1
assert listed.json()["items"][0]["id"] == term_public_id

updated_payload = {
    **payload,
    "translation": "контроль момента через сервисный слой",
}
updated = admin.patch(
    f"/api/admin/terms/{term_db_id}",
    headers=admin_headers,
    json=updated_payload,
)
assert updated.status_code == 200, updated.text
assert updated.json()["translation"] == "контроль момента через сервисный слой"

revisions = admin.get(f"/api/admin/terms/{term_db_id}/revisions")
assert revisions.status_code == 200, revisions.text
assert len(revisions.json()["revisions"]) >= 3
assert revisions.json()["term"]["id"] == term_public_id

assert app._manager_target_allowed(
    SimpleNamespace(role="manager", department="R&D"),
    SimpleNamespace(department="R&D"),
)
assert not app._manager_target_allowed(
    SimpleNamespace(role="manager", department="R&D"),
    SimpleNamespace(department="Quality"),
)

print("OK: v5.7.7 ASGI service layer executes user/admin and terminology helpers while preserving auth and API contracts")
