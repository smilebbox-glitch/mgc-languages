from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB = Path(tempfile.gettempdir()) / "mgc_languages_v583_learning_router.db"
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
    "OIDC_STATE_SECRET": "v583-learning-router-secret-32-bytes-001",
    "TTS_LEGACY_GET_ENABLED": "false",
    "TTS_CACHE_PERSISTENCE": "ephemeral",
})
sys.path.insert(0, str(ROOT))

from fastapi.routing import APIRoute  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from starlette.routing import Mount  # noqa: E402
import app  # noqa: E402
import asgi  # noqa: E402

assert asgi.app is app.app
assert asgi.CONTRACT_REPORT.ok
assert asgi.AUTH_BINDING_REPORT.ok
assert asgi.LEARNING_BINDING_REPORT.ok
assert asgi.SERVICE_BINDING_REPORT.ok
report = asgi.LEARNING_ROUTER_BINDING_REPORT
assert report.ok
assert report.learning_route_count == 12
assert report.progress_route_count == 2
assert report.course_route_count == 2
assert report.review_route_count == 2
assert report.gamification_route_count == 4
assert report.preferences_route_count == 2
assert report.route_names_preserved
assert report.response_classes_preserved
assert report.root_mount_order_preserved
assert report.router_module_owned
assert report.auth_core_bound
assert report.learning_core_bound
assert report.terminology_service_bound

expected = {
    ("GET", "/api/language/{language}/progress"),
    ("POST", "/api/language/{language}/progress"),
    ("GET", "/api/language/{language}/course30"),
    ("POST", "/api/course-day/result"),
    ("GET", "/api/review/queue"),
    ("POST", "/api/review/result"),
    ("GET", "/api/gamification/me"),
    ("GET", "/api/gamification/levels"),
    ("GET", "/api/gamification/rewards"),
    ("POST", "/api/gamification/spend"),
    ("GET", "/api/learning/preferences"),
    ("PUT", "/api/learning/preferences"),
}
route_indexes = {}
for index, route in enumerate(asgi.app.router.routes):
    if not isinstance(route, APIRoute):
        continue
    methods = (route.methods or set()) - {"HEAD", "OPTIONS"}
    if len(methods) != 1:
        continue
    key = (next(iter(methods)), route.path)
    if key in expected:
        route_indexes[key] = index
        assert route.endpoint.__module__ == "mgc.routers.learning"
assert set(route_indexes) == expected
mount_index = next(
    index for index, route in enumerate(asgi.app.router.routes)
    if isinstance(route, Mount) and getattr(route, "name", None) == "static"
)
assert all(index < mount_index for index in route_indexes.values())

# Router delegates retain the previously extracted auth, XP/SRS and terminology cores.
assert app._legacy.current_user.__module__ == "mgc.auth_core"
assert app.gamification_view is app.MGC_LEARNING_SERVICE_BINDINGS.gamification_view
assert app.schedule_srs is app.MGC_LEARNING_SERVICE_BINDINGS.schedule_srs
assert app.terms_for is app.MGC_TERMINOLOGY_SERVICE_BINDINGS.terms_for
assert app.term_by_id is app.MGC_TERMINOLOGY_SERVICE_BINDINGS.term_by_id
for name in (
    "get_progress", "set_progress", "course30", "save_course_day",
    "review_queue", "review_result", "gamification_me", "gamification_levels",
    "gamification_rewards", "gamification_spend", "get_learning_preferences",
    "set_learning_preferences",
):
    assert getattr(app._legacy, name).__module__ == "mgc.routers.learning"

client = TestClient(asgi.app)
registered = client.post(
    "/api/register",
    json={"username": "v583user", "password": "StrongPass123!", "display_name": "Learning Router User"},
)
assert registered.status_code == 200, registered.text
csrf_token = client.cookies.get("mgc_csrf")
assert csrf_token
csrf = {"X-CSRF-Token": csrf_token}

profile = client.get("/api/gamification/me")
assert profile.status_code == 200, profile.text
assert profile.json()["level"] == 1 and profile.json()["lifetime_xp"] == 0

levels = client.get("/api/gamification/levels")
assert levels.status_code == 200, levels.text
assert len(levels.json()) == 100
assert levels.json()[0]["required_xp"] == 0

rewards = client.get("/api/gamification/rewards")
assert rewards.status_code == 200, rewards.text
assert rewards.json()["balance"] == 0
assert rewards.json()["items"]

prefs = client.get("/api/learning/preferences")
assert prefs.status_code == 200, prefs.text
assert prefs.json()["show_pinyin"] is True
updated = client.put(
    "/api/learning/preferences",
    headers=csrf,
    json={"show_pinyin": False, "show_reading": True, "server_audio_enabled": True},
)
assert updated.status_code == 200, updated.text
assert updated.json()["show_pinyin"] is False

course = client.get("/api/language/chinese/course30")
assert course.status_code == 200, course.text
course_payload = course.json()
assert course_payload["language"] == "chinese"
assert len(course_payload["days"]) == 30
term_id = course_payload["days"][0]["terms"][0]["id"]

progress = client.get("/api/language/chinese/progress")
assert progress.status_code == 200, progress.text
set_progress = client.post(
    "/api/language/chinese/progress",
    headers=csrf,
    json={"term_id": term_id, "status": "known"},
)
assert set_progress.status_code == 200, set_progress.text
assert client.get("/api/language/chinese/progress").json()[term_id] == "known"

not_passed = client.post(
    "/api/course-day/result",
    headers=csrf,
    json={"language": "chinese", "day": 1, "score": 3, "total": 5},
)
assert not_passed.status_code == 200, not_passed.text
assert not_passed.json()["completed"] is False

review_queue = client.get("/api/review/queue", params={"language": "chinese", "limit": 10})
assert review_queue.status_code == 200, review_queue.text
assert review_queue.json()["algorithm"] == "SM2-inspired adaptive SRS"

review = client.post(
    "/api/review/result",
    headers=csrf,
    json={"language": "chinese", "term_id": term_id, "quality": 5},
)
assert review.status_code == 200, review.text
assert "interval_days" in review.json()

# Earn XP through the already-extracted practice workflow, then spend it through the new router.
practice = client.post(
    "/api/practice/result",
    headers=csrf,
    json={
        "session_id": "v583-quiz-001",
        "kind": "quiz",
        "language": "chinese",
        "topic": course_payload["days"][0]["topic"],
        "score": 5,
        "total": 5,
    },
)
assert practice.status_code == 200, practice.text
assert practice.json()["awarded"] == 40
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

schema = client.get("/openapi.json")
assert schema.status_code == 200
paths = schema.json()["paths"]
for _method, path in expected:
    assert path in paths

print("OK: v5.8.3 twelve active learning routes execute from mgc.routers.learning over extracted auth/XP-SRS/terminology cores")
