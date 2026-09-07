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
    "APP_ENV": "development",
    "AUTH_MODE": "local",
    "REGISTRATION_ENABLED": "true",
    "TRUSTED_HOSTS": "testserver,localhost,127.0.0.1",
    "OIDC_STATE_SECRET": "v579-workflow-runtime-test-state",
    "TTS_LEGACY_GET_ENABLED": "false",
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

bindings = app.MGC_PRACTICE_GAME_WORKFLOW_BINDINGS
service_calls = {
    "/api/practice/result": bindings.save_practice_result,
    "/api/games/{game_type}/start": bindings.start_game,
    "/api/games/{session_id}/finish": bindings.finish_game,
    "/api/learning/question-attempt": bindings.question_attempt,
}
for path, call in service_calls.items():
    assert call.__module__ == "mgc.services.practice_games"
    routes = [
        route for route in asgi.app.routes
        if isinstance(route, APIRoute)
        and route.path == path
        and "POST" in (route.methods or set())
    ]
    assert len(routes) == 1
    if hasattr(asgi, "PRACTICE_GAMES_ROUTER_BINDING_REPORT"):
        assert asgi.PRACTICE_GAMES_ROUTER_BINDING_REPORT.ok
        assert routes[0].endpoint.__module__ == "mgc.routers.practice_games"
    else:
        assert routes[0].dependant.call is call
        assert routes[0].endpoint is call

client = TestClient(asgi.app)
register = client.post(
    "/api/register",
    json={"username": "v579user", "password": "testpass579", "display_name": "Workflow User"},
)
assert register.status_code == 200, register.text
csrf = register.cookies.get("mgc_csrf") or client.cookies.get("mgc_csrf")
headers = {"X-CSRF-Token": csrf}

payload = {
    "session_id": "v579-quiz-perfect-001",
    "kind": "quiz",
    "language": "chinese",
    "topic": "Сварка кузова",
    "score": 5,
    "total": 5,
}
practice = client.post("/api/practice/result", headers=headers, json=payload)
assert practice.status_code == 200, practice.text
assert practice.json()["duplicate"] is False
assert practice.json()["awarded"] == 40

duplicate = client.post("/api/practice/result", headers=headers, json=payload)
assert duplicate.status_code == 200, duplicate.text
assert duplicate.json()["duplicate"] is True
assert duplicate.json()["profile"]["lifetime_xp"] == 40

print("OK: v5.7.9 workflow service retains scoring/idempotency semantics behind current router ownership")
