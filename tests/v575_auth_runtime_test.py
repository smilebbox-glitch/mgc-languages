from __future__ import annotations

import os
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB = Path(tempfile.gettempdir()) / "mgc_languages_v575_auth_runtime.db"
try:
    DB.unlink()
except FileNotFoundError:
    pass

os.environ.update({
    "DATABASE_URL": f"sqlite:///{DB}",
    "AUTO_CREATE_SCHEMA": "true",
    "APP_ENV": "development",
    "AUTH_MODE": "local",
    "REGISTRATION_ENABLED": "true",
    "MGC_ADMIN_USERNAME": "v575admin",
    "MGC_ADMIN_PASSWORD": "V575AdminPassword!123",
    "MGC_ADMIN_DISPLAY_NAME": "v575 Admin",
    "OIDC_STATE_SECRET": "v575-auth-runtime-secret-32-bytes",
    "TTS_CACHE_PERSISTENCE": "ephemeral",
})
sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient  # noqa: E402
import app  # noqa: E402

legacy_current_user = app.current_user
legacy_require_roles = app.require_roles
legacy_create_login_session = app.create_login_session

import asgi  # noqa: E402

assert asgi.app is app.app
assert asgi.CONTRACT_REPORT.ok
assert asgi.SECURITY_BINDING_REPORT.ok
assert asgi.AUTH_BINDING_REPORT.ok
assert asgi.AUTH_BINDING_REPORT.current_user_dependency_occurrences > 0
assert asgi.AUTH_BINDING_REPORT.role_dependency_occurrences > 0
assert asgi.AUTH_BINDING_REPORT.role_dependency_overrides > 0
assert asgi.AUTH_BINDING_REPORT.session_factory_bound
assert app.current_user is not legacy_current_user
assert app.require_roles is not legacy_require_roles
assert app.create_login_session is not legacy_create_login_session
assert asgi.app.dependency_overrides[legacy_current_user] is app.current_user

user = TestClient(asgi.app)
register = user.post(
    "/api/register",
    json={"username": "v575user", "password": "V575UserPassword!123", "display_name": "v575 User"},
)
assert register.status_code == 200, register.text
csrf = register.json()["csrf"]
raw_session = user.cookies.get("mgc_session")
assert csrf and raw_session and user.cookies.get("mgc_csrf") == csrf
assert user.get("/api/me").status_code == 200
assert user.get("/api/admin/users").status_code == 403

with app.SessionLocal() as db:
    stored = db.scalar(app.select(app.LoginSession).where(app.LoginSession.token_hash == app.token_digest(raw_session)))
    assert stored is not None
    stored.expires_at = datetime.now(timezone.utc) - timedelta(minutes=1)
    db.commit()

expired = user.get("/api/me")
assert expired.status_code == 401, expired.text
assert expired.json()["detail"] == "Сессия истекла"
with app.SessionLocal() as db:
    assert db.scalar(app.select(app.LoginSession).where(app.LoginSession.token_hash == app.token_digest(raw_session))) is None

admin = TestClient(asgi.app)
login = admin.post("/api/login", json={"username": "v575admin", "password": "V575AdminPassword!123"})
assert login.status_code == 200, login.text
admin_users = admin.get("/api/admin/users")
assert admin_users.status_code == 200, admin_users.text

print(
    "OK: v5.7.5 ASGI auth bridge rebinds captured current_user/role dependencies and preserves register, expiry and Admin authorization"
)
