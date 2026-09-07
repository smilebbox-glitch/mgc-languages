from __future__ import annotations

import os
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB = Path(tempfile.gettempdir()) / "mgc_languages_v598_session_user_isolation.db"
try:
    DB.unlink()
except FileNotFoundError:
    pass

os.environ.update(
    {
        "DATABASE_URL": f"sqlite:///{DB}",
        "AUTO_CREATE_SCHEMA": "true",
        "APP_ENV": "development",
        "AUTH_MODE": "local",
        "REGISTRATION_ENABLED": "true",
        "TRUSTED_HOSTS": "testserver,localhost,127.0.0.1",
        "OIDC_STATE_SECRET": "v598-session-user-isolation-secret-32-bytes",
        "TTS_LEGACY_GET_ENABLED": "false",
        "TTS_CACHE_PERSISTENCE": "ephemeral",
    }
)
sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import select  # noqa: E402
import app  # noqa: E402
import asgi  # noqa: E402
from mgc.services.practice_isolation import practice_storage_session_id  # noqa: E402

assert asgi.WORKFLOW_BINDING_REPORT.ok
assert asgi.WORKFLOW_BINDING_REPORT.user_scoped_practice_sessions
assert asgi.PRACTICE_GAMES_ROUTER_BINDING_REPORT.ok
assert asgi.PRACTICE_GAMES_ROUTER_BINDING_REPORT.user_scoped_practice_sessions

alice = TestClient(asgi.app)
bob = TestClient(asgi.app)

alice_register = alice.post(
    "/api/register",
    json={
        "username": "alice.v598",
        "password": "AliceStrong123!",
        "display_name": "Alice R&D",
        "department": "R&D",
    },
)
assert alice_register.status_code == 200, alice_register.text
alice_user = alice_register.json()["user"]
alice_csrf = alice.cookies.get("mgc_csrf")
assert alice_csrf

bob_register = bob.post(
    "/api/register",
    json={
        "username": "bob.v598",
        "password": "BobStrong123!",
        "display_name": "Bob IT",
        "department": "IT",
    },
)
assert bob_register.status_code == 200, bob_register.text
bob_user = bob_register.json()["user"]
bob_csrf = bob.cookies.get("mgc_csrf")
assert bob_csrf

shared_session_id = "same-browser-session-id"
alice_payload = {
    "session_id": shared_session_id,
    "kind": "quiz",
    "language": "chinese",
    "topic": "Сварка кузова",
    "score": 5,
    "total": 5,
}
bob_payload = {
    **alice_payload,
    "score": 3,
}

alice_practice = alice.post(
    "/api/practice/result",
    headers={"X-CSRF-Token": alice_csrf},
    json=alice_payload,
)
assert alice_practice.status_code == 200, alice_practice.text
assert alice_practice.json()["duplicate"] is False
assert alice_practice.json()["awarded"] == 40

bob_practice = bob.post(
    "/api/practice/result",
    headers={"X-CSRF-Token": bob_csrf},
    json=bob_payload,
)
assert bob_practice.status_code == 200, bob_practice.text
assert bob_practice.json()["duplicate"] is False
assert bob_practice.json()["awarded"] == 20

alice_duplicate = alice.post(
    "/api/practice/result",
    headers={"X-CSRF-Token": alice_csrf},
    json=alice_payload,
)
bob_duplicate = bob.post(
    "/api/practice/result",
    headers={"X-CSRF-Token": bob_csrf},
    json=bob_payload,
)
assert alice_duplicate.status_code == 200 and alice_duplicate.json()["duplicate"] is True
assert bob_duplicate.status_code == 200 and bob_duplicate.json()["duplicate"] is True
assert alice_duplicate.json()["profile"]["lifetime_xp"] == 40
assert bob_duplicate.json()["profile"]["lifetime_xp"] == 20

with app.SessionLocal() as db:
    rows = db.scalars(select(app.PracticeResult).order_by(app.PracticeResult.user_id)).all()
    assert len(rows) == 2
    by_user = {row.user_id: row for row in rows}
    assert by_user[alice_user["id"]].session_id == practice_storage_session_id(
        alice_user["id"], shared_session_id
    )
    assert by_user[bob_user["id"]].session_id == practice_storage_session_id(
        bob_user["id"], shared_session_id
    )
    assert by_user[alice_user["id"]].session_id != by_user[bob_user["id"]].session_id

    alice_profile = db.get(app.GamificationProfile, alice_user["id"])
    bob_profile = db.get(app.GamificationProfile, bob_user["id"])
    assert alice_profile is not None and alice_profile.lifetime_xp == 40
    assert bob_profile is not None and bob_profile.lifetime_xp == 20

# A second browser/device session for Alice must not invalidate the first one.
alice_second = TestClient(asgi.app)
alice_second_login = alice_second.post(
    "/api/login",
    json={
        "username": "alice.v598",
        "password": "AliceStrong123!",
        "department": "R&D",
    },
)
assert alice_second_login.status_code == 200, alice_second_login.text
assert alice.get("/api/me").status_code == 200
assert alice_second.get("/api/me").status_code == 200
assert bob.get("/api/me").status_code == 200

# Logout deletes only the current token; Alice's second browser and Bob remain signed in.
alice_logout = alice.post(
    "/api/logout",
    headers={"X-CSRF-Token": alice.cookies.get("mgc_csrf")},
)
assert alice_logout.status_code == 200, alice_logout.text
assert alice.get("/api/me").status_code == 401
assert alice_second.get("/api/me").status_code == 200
assert bob.get("/api/me").status_code == 200

# Expire Alice's second token directly; Bob's independent session must remain valid.
alice_second_raw = alice_second.cookies.get("mgc_session")
assert alice_second_raw
with app.SessionLocal() as db:
    session = db.scalar(
        select(app.LoginSession).where(
            app.LoginSession.token_hash == app.token_digest(alice_second_raw)
        )
    )
    assert session is not None
    session.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
    db.commit()

expired = alice_second.get("/api/me")
assert expired.status_code == 401, expired.text
assert "истекла" in expired.json()["detail"].lower()
assert bob.get("/api/me").status_code == 200
assert bob.get("/api/gamification/me").json()["lifetime_xp"] == 20

print("PASS: v5.9.8 sessions, logout/expiry and practice idempotency are isolated per user")
