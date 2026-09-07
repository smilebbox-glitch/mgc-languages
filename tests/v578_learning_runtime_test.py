from __future__ import annotations

import inspect
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB = Path(tempfile.gettempdir()) / "mgc_languages_v578_learning.db"
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
    "MGC_ADMIN_USERNAME": "v578admin",
    "MGC_ADMIN_PASSWORD": "V578AdminPassword!123456",
    "MGC_ADMIN_DISPLAY_NAME": "V578 Admin",
    "OIDC_STATE_SECRET": "v578-learning-layer-secret-32-bytes-001",
    "TTS_LEGACY_GET_ENABLED": "false",
    "TERM_APPROVAL_REQUIRED": "true",
    "RLS_ENABLED": "true",
    "METRICS_TOKEN": "v578metrics",
    "TTS_CACHE_PERSISTENCE": "ephemeral",
})
sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient  # noqa: E402
import app  # noqa: E402
import asgi  # noqa: E402

assert asgi.app is app.app
assert asgi.LEARNING_BINDING_REPORT.ok
assert asgi.LEARNING_BINDING_REPORT.xp_profile_bound
assert asgi.LEARNING_BINDING_REPORT.xp_award_bound
assert asgi.LEARNING_BINDING_REPORT.xp_spend_bound
assert asgi.LEARNING_BINDING_REPORT.srs_card_bound
assert asgi.LEARNING_BINDING_REPORT.srs_schedule_bound
assert asgi.LEARNING_BINDING_REPORT.model_contract_preserved
assert asgi.LEARNING_BINDING_REPORT.reward_contract_preserved
assert app.gamification_view is app.MGC_LEARNING_SERVICE_BINDINGS.gamification_view
assert app.award_xp is app.MGC_LEARNING_SERVICE_BINDINGS.award_xp
assert app.spend_xp is app.MGC_LEARNING_SERVICE_BINDINGS.spend_xp
assert app.schedule_srs is app.MGC_LEARNING_SERVICE_BINDINGS.schedule_srs
assert app.gamification_view.__module__ == "mgc.services.learning"
assert app.schedule_srs.__module__ == "mgc.services.learning"

# Runtime ordering contract: v5.7.7 user stats must capture v5.7.8 gamification_view.
user_stats_closure = inspect.getclosurevars(app.user_admin_stats)
assert user_stats_closure.nonlocals.get("gamification_view") is app.gamification_view

client = TestClient(asgi.app)
registered = client.post(
    "/api/register",
    json={"username": "v578user", "password": "StrongPass123!", "display_name": "Learning User"},
)
assert registered.status_code == 200, registered.text
user_id = registered.json()["user"]["id"]
csrf = {"X-CSRF-Token": client.cookies.get("mgc_csrf")}

profile = client.get("/api/gamification/me")
assert profile.status_code == 200
assert profile.json()["level"] == 1 and profile.json()["lifetime_xp"] == 0

practice = client.post(
    "/api/practice/result",
    headers=csrf,
    json={
        "session_id": "v578-quiz-001",
        "kind": "quiz",
        "language": "chinese",
        "topic": "Сварка кузова",
        "score": 5,
        "total": 5,
    },
)
assert practice.status_code == 200, practice.text
assert practice.json()["awarded"] == 40
assert practice.json()["profile"]["lifetime_xp"] == 40

duplicate = client.post(
    "/api/practice/result",
    headers=csrf,
    json={
        "session_id": "v578-quiz-001",
        "kind": "quiz",
        "language": "chinese",
        "topic": "Сварка кузова",
        "score": 5,
        "total": 5,
    },
)
assert duplicate.status_code == 200 and duplicate.json()["duplicate"] is True
assert duplicate.json()["profile"]["lifetime_xp"] == 40

quiz = client.get(
    "/api/language/chinese/quiz",
    params={"topic": "Сварка кузова", "level": "A1", "count": 5},
)
assert quiz.status_code == 200, quiz.text
question = quiz.json()["questions"][0]

spend = client.post(
    "/api/gamification/spend",
    headers=csrf,
    json={
        "reward_id": "hint_small",
        "language": "chinese",
        "context": {"term_id": question["id"], "options": question["options"]},
    },
)
assert spend.status_code == 200, spend.text
assert spend.json()["spent"] == 10
assert spend.json()["profile"]["lifetime_xp"] == 40
assert spend.json()["profile"]["spendable_xp"] == 30

review1 = client.post(
    "/api/review/result",
    headers=csrf,
    json={"language": "chinese", "term_id": question["id"], "quality": 5},
)
assert review1.status_code == 200, review1.text
assert review1.json()["interval_days"] == 1 and review1.json()["xp"] == 5
review2 = client.post(
    "/api/review/result",
    headers=csrf,
    json={"language": "chinese", "term_id": question["id"], "quality": 5},
)
assert review2.status_code == 200, review2.text
assert review2.json()["interval_days"] == 3 and review2.json()["xp"] == 5

profile_after = client.get("/api/gamification/me").json()
assert profile_after["lifetime_xp"] == 50
assert profile_after["spendable_xp"] == 40

levels = client.get("/api/gamification/levels")
assert levels.status_code == 200
assert len(levels.json()) == 100
assert levels.json()[0]["required_xp"] == 0
assert levels.json()[-1]["level"] == 100 and levels.json()[-1]["title"] == "Легенда"

admin = TestClient(asgi.app)
login = admin.post("/api/login", json={"username": "v578admin", "password": "V578AdminPassword!123456"})
assert login.status_code == 200, login.text
users = admin.get("/api/admin/users")
assert users.status_code == 200, users.text
admin_row = next(row for row in users.json() if row["id"] == user_id)
assert admin_row["lifetime_xp"] == 50 and admin_row["spendable_xp"] == 40

print("OK: v5.7.8 ASGI learning service executes XP/spending/SRS and feeds extracted user-service statistics without API drift")
