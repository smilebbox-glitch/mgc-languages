from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB = Path(tempfile.gettempdir()) / "mgc_languages_v592_language_content_router.db"
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
    "MGC_ADMIN_USERNAME": "v592admin",
    "MGC_ADMIN_PASSWORD": "V592AdminPassword!123456",
    "OIDC_STATE_SECRET": "v592-language-content-secret-32-bytes-0001",
    "TTS_ENABLED": "false",
    "TTS_LEGACY_GET_ENABLED": "false",
    "TTS_CACHE_PERSISTENCE": "ephemeral",
    "RLS_ENABLED": "true",
    "METRICS_TOKEN": "v592metrics",
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
assert asgi.SERVICE_BINDING_REPORT.ok
report = asgi.LANGUAGE_CONTENT_ROUTER_BINDING_REPORT
assert report.ok
assert report.route_count == 5
assert report.summary_route_count == 1
assert report.quiz_route_count == 1
assert report.scenario_route_count == 3
assert report.route_names_preserved
assert report.response_classes_preserved
assert report.root_mount_order_preserved
assert report.router_module_owned
assert report.auth_core_bound
assert report.terminology_service_bound

expected = {
    ("GET", "/api/language/{language}/summary"),
    ("GET", "/api/language/{language}/quiz"),
    ("GET", "/api/language/{language}/situations"),
    ("GET", "/api/language/{language}/roleplays"),
    ("GET", "/api/language/{language}/mgc-scenarios"),
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
        assert route.endpoint.__module__ == "mgc.routers.language_content"
assert set(route_indexes) == expected
mount_index = next(
    index for index, route in enumerate(asgi.app.router.routes)
    if isinstance(route, Mount) and getattr(route, "name", None) == "static"
)
assert all(index < mount_index for index in route_indexes.values())

assert app._legacy.current_user.__module__ == "mgc.auth_core"
assert app._legacy.terms_for.__module__ == "mgc.services.terminology"
for name in (
    "language_summary",
    "language_quiz",
    "situations",
    "roleplays",
    "mgc_scenarios",
):
    assert getattr(app._legacy, name).__module__ == "mgc.routers.language_content"

anonymous = TestClient(asgi.app)
assert anonymous.get("/api/language/chinese/summary").status_code == 401

client = TestClient(asgi.app)
register = client.post(
    "/api/register",
    json={
        "username": "v592user",
        "password": "StrongPass123!",
        "display_name": "v592 User",
    },
)
assert register.status_code == 200, register.text

chinese_summary = client.get("/api/language/chinese/summary")
assert chinese_summary.status_code == 200, chinese_summary.text
summary_data = chinese_summary.json()
assert summary_data["language"] == "chinese"
assert summary_data["learning_standard"]["name"] == "Путунхуа (普通话)"
assert summary_data["learning_standard"]["dialects_reference_only"] is True
assert set(summary_data["level_labels"]) == {"A1", "A2", "B1", "B2", "C1"}

english_summary = client.get("/api/language/english/summary")
assert english_summary.status_code == 200, english_summary.text
assert english_summary.json()["learning_standard"] is None

quiz = client.get("/api/language/chinese/quiz?count=5")
assert quiz.status_code == 200, quiz.text
questions = quiz.json()["questions"]
assert 1 <= len(questions) <= 5
for question in questions:
    assert len(question["options"]) == 4
    assert 0 <= question["correct_index"] <= 3
assert client.get("/api/language/chinese/quiz?count=4").status_code == 422
assert client.get("/api/language/chinese/quiz?count=31").status_code == 422

situations = client.get("/api/language/chinese/situations")
assert situations.status_code == 200, situations.text
assert isinstance(situations.json(), list) and situations.json()
assert all("target" in item and "translation" in item for item in situations.json())

roleplays = client.get("/api/language/chinese/roleplays")
assert roleplays.status_code == 200, roleplays.text
assert isinstance(roleplays.json(), list) and roleplays.json()
assert all("options" in item and "question" in item for item in roleplays.json())

scenarios = client.get("/api/language/english/mgc-scenarios")
assert scenarios.status_code == 200, scenarios.text
assert isinstance(scenarios.json(), list) and scenarios.json()
assert all("usage" in item and "target" in item for item in scenarios.json())

assert client.get("/api/language/unknown/summary").status_code == 404

openapi = client.get("/openapi.json")
assert openapi.status_code == 200, openapi.text
for _, path in expected:
    assert path in openapi.json()["paths"]

print("OK: v5.9.2 language content router preserves auth, Putonghua summary, quiz bounds and scenario content")
