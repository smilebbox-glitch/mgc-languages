from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB = Path(tempfile.gettempdir()) / "mgc_languages_v584_practice_games_router.db"
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
    "MGC_ADMIN_USERNAME": "v584admin",
    "MGC_ADMIN_PASSWORD": "V584AdminPassword!123456",
    "OIDC_STATE_SECRET": "v584-practice-games-router-secret-32-bytes-001",
    "TTS_LEGACY_GET_ENABLED": "false",
    "RLS_ENABLED": "true",
    "METRICS_TOKEN": "v584metrics",
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
assert asgi.WORKFLOW_BINDING_REPORT.ok
assert asgi.WORKFLOW_BINDING_REPORT.user_scoped_practice_sessions
assert asgi.AUTH_BINDING_REPORT.ok
report = asgi.PRACTICE_GAMES_ROUTER_BINDING_REPORT
assert report.ok
assert report.route_count == 4
assert report.practice_route_count == 1
assert report.game_route_count == 2
assert report.question_attempt_route_count == 1
assert report.route_names_preserved
assert report.response_classes_preserved
assert report.root_mount_order_preserved
assert report.router_module_owned
assert report.auth_core_bound
assert report.workflow_service_bound
assert report.learning_service_captured
assert report.terminology_service_captured
assert report.user_scoped_practice_sessions

expected = {
    ("POST", "/api/practice/result"),
    ("POST", "/api/games/{game_type}/start"),
    ("POST", "/api/games/{session_id}/finish"),
    ("POST", "/api/learning/question-attempt"),
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
        assert route.endpoint.__module__ == "mgc.routers.practice_games"
assert set(route_indexes) == expected
mount_index = next(
    index for index, route in enumerate(asgi.app.router.routes)
    if isinstance(route, Mount) and getattr(route, "name", None) == "static"
)
assert all(index < mount_index for index in route_indexes.values())

bindings = app._legacy.MGC_PRACTICE_GAME_WORKFLOW_BINDINGS
assert bindings.save_practice_result.__module__ == "mgc.services.practice_isolation"
for name in ("start_game", "finish_game", "question_attempt"):
    assert getattr(bindings, name).__module__ == "mgc.services.practice_games"
assert app._legacy.current_user.__module__ == "mgc.auth_core"
assert app._legacy.save_practice_result.__module__ == "mgc.routers.practice_games"
assert app._legacy.start_game.__module__ == "mgc.routers.practice_games"
assert app._legacy.finish_game.__module__ == "mgc.routers.practice_games"
assert app._legacy.question_attempt.__module__ == "mgc.routers.practice_games"

client = TestClient(asgi.app)
register = client.post(
    "/api/register",
    json={
        "username": "v584user",
        "password": "StrongPass123!",
        "display_name": "v584 Router User",
    },
)
assert register.status_code == 200, register.text
csrf = register.cookies.get("mgc_csrf") or client.cookies.get("mgc_csrf")
assert csrf
headers = {"X-CSRF-Token": csrf}

practice_payload = {
    "session_id": "v584-quiz-perfect-001",
    "kind": "quiz",
    "language": "chinese",
    "topic": "Сварка кузова",
    "score": 5,
    "total": 5,
}
practice = client.post("/api/practice/result", headers=headers, json=practice_payload)
assert practice.status_code == 200, practice.text
practice_data = practice.json()
assert practice_data["duplicate"] is False
assert practice_data["awarded"] == 40
assert practice_data["profile"]["lifetime_xp"] == 40

duplicate_practice = client.post(
    "/api/practice/result", headers=headers, json=practice_payload
)
assert duplicate_practice.status_code == 200, duplicate_practice.text
assert duplicate_practice.json()["duplicate"] is True
assert duplicate_practice.json()["profile"]["lifetime_xp"] == 40

terms = client.get("/api/language/chinese/terms", params={"limit": 20})
assert terms.status_code == 200, terms.text
term = terms.json()["items"][0]
attempt_payload = {
    "session_id": "v584-question-session",
    "question_id": "v584-question-001",
    "term_id": term["id"],
    "language": "chinese",
    "topic": term["topic"],
    "kind": "quiz",
    "correct": True,
    "response_ms": 850,
    "selected": term["translation"],
}
attempt = client.post(
    "/api/learning/question-attempt", headers=headers, json=attempt_payload
)
assert attempt.status_code == 200, attempt.text
assert attempt.json() == {"ok": True}

duplicate_attempt = client.post(
    "/api/learning/question-attempt", headers=headers, json=attempt_payload
)
assert duplicate_attempt.status_code == 200, duplicate_attempt.text
assert duplicate_attempt.json() == {"ok": True, "duplicate": True}

with app.SessionLocal() as db:
    card = db.scalar(
        app.select(app.SRSCard).where(
            app.SRSCard.user_id == register.json()["user"]["id"],
            app.SRSCard.language == "chinese",
            app.SRSCard.term_id == term["id"],
        )
    )
    assert card is not None
    assert card.repetitions == 1
    assert card.interval_days == 1
    assert card.last_quality == 5

game = client.post(
    "/api/games/match/start",
    headers=headers,
    params={"language": "chinese", "topic": "Сварка кузова"},
)
assert game.status_code == 200, game.text
game_data = game.json()
assert game_data["game_type"] == "match"
assert game_data["total"] >= 6
answers = [item["id"] for item in game_data["items"]]

finish = client.post(
    f"/api/games/{game_data['session_id']}/finish",
    headers=headers,
    json={"answers": answers},
)
assert finish.status_code == 200, finish.text
finish_data = finish.json()
assert finish_data["score"] == game_data["total"]
assert finish_data["awarded"] == 10 + game_data["total"] * 3 + 10
assert finish_data["profile"]["lifetime_xp"] == 40 + finish_data["awarded"]

duplicate_finish = client.post(
    f"/api/games/{game_data['session_id']}/finish",
    headers=headers,
    json={"answers": answers},
)
assert duplicate_finish.status_code == 200, duplicate_finish.text
assert duplicate_finish.json()["duplicate"] is True
assert duplicate_finish.json()["profile"]["lifetime_xp"] == finish_data["profile"]["lifetime_xp"]

schema = client.get("/openapi.json")
assert schema.status_code == 200
paths = schema.json()["paths"]
for _method, path in expected:
    assert path in paths

print("OK: v5.8.4 router remains stable while v5.9.8 scopes practice idempotency per user")
