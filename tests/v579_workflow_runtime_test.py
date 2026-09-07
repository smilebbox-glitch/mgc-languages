from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB = Path(tempfile.gettempdir()) / "mgc_languages_v579_workflows.db"
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
    "MGC_ADMIN_USERNAME": "v579admin",
    "MGC_ADMIN_PASSWORD": "V579AdminPassword!123456",
    "OIDC_STATE_SECRET": "v579-workflow-runtime-secret-32-bytes-001",
    "TTS_LEGACY_GET_ENABLED": "false",
    "RLS_ENABLED": "true",
    "METRICS_TOKEN": "v579metrics",
    "TTS_CACHE_PERSISTENCE": "ephemeral",
})
sys.path.insert(0, str(ROOT))

from fastapi.routing import APIRoute  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
import app  # noqa: E402
import asgi  # noqa: E402

assert asgi.app is app.app
report = asgi.WORKFLOW_BINDING_REPORT
assert report.ok
assert report.practice_route_bound
assert report.game_start_route_bound
assert report.game_finish_route_bound
assert report.question_attempt_route_bound
assert report.route_contract_preserved
assert report.model_contract_preserved
assert report.learning_service_captured
assert report.terminology_service_captured

expected = {
    ("/api/practice/result", "POST"): app.MGC_PRACTICE_GAME_WORKFLOW_BINDINGS.save_practice_result,
    ("/api/games/{game_type}/start", "POST"): app.MGC_PRACTICE_GAME_WORKFLOW_BINDINGS.start_game,
    ("/api/games/{session_id}/finish", "POST"): app.MGC_PRACTICE_GAME_WORKFLOW_BINDINGS.finish_game,
    ("/api/learning/question-attempt", "POST"): app.MGC_PRACTICE_GAME_WORKFLOW_BINDINGS.question_attempt,
}
for (path, method), call in expected.items():
    routes = [
        route for route in asgi.app.routes
        if isinstance(route, APIRoute)
        and route.path == path
        and method in (route.methods or set())
    ]
    assert len(routes) == 1
    assert routes[0].dependant.call is call
    assert routes[0].endpoint is call
    assert call.__module__ == "mgc.services.practice_games"

client = TestClient(asgi.app)
register = client.post(
    "/api/register",
    json={
        "username": "v579user",
        "password": "StrongPass123!",
        "display_name": "Workflow User",
    },
)
assert register.status_code == 200, register.text
headers = {"X-CSRF-Token": client.cookies.get("mgc_csrf")}

practice_payload = {
    "session_id": "v579-quiz-perfect-001",
    "kind": "quiz",
    "language": "chinese",
    "topic": "Сварка кузова",
    "score": 5,
    "total": 5,
}
practice = client.post("/api/practice/result", headers=headers, json=practice_payload)
assert practice.status_code == 200, practice.text
assert practice.json()["duplicate"] is False
assert practice.json()["awarded"] == 40
assert practice.json()["profile"]["lifetime_xp"] == 40

duplicate_practice = client.post("/api/practice/result", headers=headers, json=practice_payload)
assert duplicate_practice.status_code == 200, duplicate_practice.text
assert duplicate_practice.json()["duplicate"] is True
assert duplicate_practice.json()["profile"]["lifetime_xp"] == 40

terms = client.get("/api/language/chinese/terms", params={"limit": 20})
assert terms.status_code == 200, terms.text
term = terms.json()["items"][0]
attempt_payload = {
    "session_id": "v579-question-session",
    "question_id": "v579-question-001",
    "term_id": term["id"],
    "language": "chinese",
    "topic": term["topic"],
    "kind": "quiz",
    "correct": True,
    "response_ms": 850,
    "selected": term["translation"],
}
attempt = client.post("/api/learning/question-attempt", headers=headers, json=attempt_payload)
assert attempt.status_code == 200, attempt.text
assert attempt.json() == {"ok": True}

duplicate_attempt = client.post("/api/learning/question-attempt", headers=headers, json=attempt_payload)
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

levels = client.get("/api/gamification/levels")
assert levels.status_code == 200
assert len(levels.json()) == 100

print("OK: v5.7.9 ASGI workflows execute practice, question-attempt and game lifecycle with duplicate protection")
