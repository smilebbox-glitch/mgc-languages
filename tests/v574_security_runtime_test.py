from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB = Path(tempfile.gettempdir()) / "mgc_languages_v574_security.db"
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
    "OIDC_STATE_SECRET": "v574-security-runtime-secret-32-bytes",
    "TTS_CACHE_PERSISTENCE": "ephemeral",
})
sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient  # noqa: E402
import app  # noqa: E402
import asgi  # noqa: E402
import mgc.security as security  # noqa: E402

assert asgi.app is app.app
assert asgi.CONTRACT_REPORT.ok
assert asgi.SECURITY_BINDING_REPORT.ok
assert asgi.SECURITY_BINDING_REPORT.csrf_policy_preserved
assert app.make_password_hash is security.make_password_hash
assert app.verify_password is security.verify_password
assert app.token_digest is security.token_digest
assert app.CSRF_EXEMPT == set(security.CSRF_EXEMPT_PATHS)

client = TestClient(asgi.app)
register = client.post(
    "/api/register",
    json={"username": "v574user", "password": "SecurityPass123!", "display_name": "Security User"},
)
assert register.status_code == 200, register.text
csrf = register.json()["csrf"]
assert csrf and client.cookies.get("mgc_session") and client.cookies.get("mgc_csrf") == csrf

with app.SessionLocal() as db:
    user = db.scalar(app.select(app.User).where(app.User.username == "v574user"))
    assert user is not None
    assert security.verify_password("SecurityPass123!", user.password_hash)
    assert not security.verify_password("wrong", user.password_hash)

blocked = client.post("/api/me/language", json={"language": "english"})
assert blocked.status_code == 403, blocked.text
assert blocked.json()["detail"] == "CSRF-проверка не пройдена"

allowed = client.post(
    "/api/me/language",
    headers={"X-CSRF-Token": csrf},
    json={"language": "english"},
)
assert allowed.status_code == 200, allowed.text
assert allowed.json()["language"] == "english"
assert allowed.headers["x-frame-options"] == "DENY"
assert allowed.headers["x-content-type-options"] == "nosniff"
assert allowed.headers["cache-control"] == "no-store"
assert "frame-ancestors 'none'" in allowed.headers["content-security-policy"]

logout = client.post("/api/logout", headers={"X-CSRF-Token": csrf})
assert logout.status_code == 200, logout.text
wrong = client.post("/api/login", json={"username": "v574user", "password": "DefinitelyWrong123!"})
assert wrong.status_code == 401, wrong.text
correct = client.post("/api/login", json={"username": "v574user", "password": "SecurityPass123!"})
assert correct.status_code == 200, correct.text

print("OK: v5.7.4 ASGI security binding preserves registration, login, session, CSRF and response-header behavior")
