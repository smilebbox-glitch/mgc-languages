from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB = Path(tempfile.gettempdir()) / "mgc_languages_v586_pronunciation_router.db"
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
    "MGC_ADMIN_USERNAME": "v586admin",
    "MGC_ADMIN_PASSWORD": "V586AdminPassword!123456",
    "OIDC_STATE_SECRET": "v586-pronunciation-router-secret-32-bytes-0001",
    "TTS_ENABLED": "false",
    "TTS_MAX_CHARS": "64",
    "TTS_LEGACY_GET_ENABLED": "true",
    "TTS_CACHE_PERSISTENCE": "ephemeral",
    "RLS_ENABLED": "true",
    "METRICS_TOKEN": "v586metrics",
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
report = asgi.PRONUNCIATION_ROUTER_BINDING_REPORT
assert report.ok
assert report.route_count == 3
assert report.status_route_count == 1
assert report.post_audio_route_count == 1
assert report.legacy_get_enabled is True
assert report.legacy_get_route_count == 1
assert report.route_names_preserved
assert report.response_classes_preserved
assert report.legacy_get_deprecated_preserved
assert report.payload_schema_preserved
assert report.tts_max_chars_preserved
assert report.root_mount_order_preserved
assert report.router_module_owned
assert report.auth_core_bound
assert report.legacy_tts_handlers_captured

expected = {
    ("GET", "/api/pronunciation/status"),
    ("POST", "/api/pronunciation/audio"),
    ("GET", "/api/pronunciation/audio"),
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
        assert route.endpoint.__module__ == "mgc.routers.pronunciation"
        if key == ("GET", "/api/pronunciation/audio"):
            assert route.deprecated is True
assert set(route_indexes) == expected
mount_index = next(
    index for index, route in enumerate(asgi.app.router.routes)
    if isinstance(route, Mount) and getattr(route, "name", None) == "static"
)
assert all(index < mount_index for index in route_indexes.values())

assert app._legacy.current_user.__module__ == "mgc.auth_core"
assert app._legacy.pronunciation_status.__module__ == "mgc.routers.pronunciation"
assert app._legacy.pronunciation_audio_post.__module__ == "mgc.routers.pronunciation"
assert app._legacy.pronunciation_audio_legacy.__module__ == "mgc.routers.pronunciation"
legacy_routes = app._legacy.MGC_LEGACY_PRONUNCIATION_ROUTES
assert legacy_routes[("GET", "/api/pronunciation/status")].endpoint.__module__ == "mgc.legacy_app"
assert legacy_routes[("POST", "/api/pronunciation/audio")].endpoint.__module__ == "mgc.legacy_app"
assert legacy_routes[("GET", "/api/pronunciation/audio")].endpoint.__module__ == "mgc.legacy_app"

anonymous = TestClient(asgi.app)
assert anonymous.get("/api/pronunciation/status").status_code == 401

client = TestClient(asgi.app)
register = client.post(
    "/api/register",
    json={
        "username": "v586user",
        "password": "StrongPass123!",
        "display_name": "v586 Pronunciation User",
    },
)
assert register.status_code == 200, register.text
csrf = register.cookies.get("mgc_csrf") or client.cookies.get("mgc_csrf")
assert csrf
headers = {"X-CSRF-Token": csrf}

status = client.get("/api/pronunciation/status")
assert status.status_code == 200, status.text
status_data = status.json()
assert status_data["server_available"] is False
assert status_data["offline"] is False
assert status_data["circuit_open"] is False

valid_post = client.post(
    "/api/pronunciation/audio",
    headers=headers,
    json={"language": "chinese", "text": "你好", "rate": 0.9},
)
assert valid_post.status_code == 503, valid_post.text
assert "browser fallback" in valid_post.json()["detail"]

oversized_post = client.post(
    "/api/pronunciation/audio",
    headers=headers,
    json={"language": "english", "text": "x" * 65, "rate": 0.9},
)
assert oversized_post.status_code == 422, oversized_post.text
invalid_rate = client.post(
    "/api/pronunciation/audio",
    headers=headers,
    json={"language": "english", "text": "hello", "rate": 1.3},
)
assert invalid_rate.status_code == 422, invalid_rate.text

legacy = client.get(
    "/api/pronunciation/audio",
    params={"language": "english", "text": "hello", "rate": 0.9},
)
assert legacy.status_code == 503, legacy.text
oversized_legacy = client.get(
    "/api/pronunciation/audio",
    params={"language": "english", "text": "x" * 65, "rate": 0.9},
)
assert oversized_legacy.status_code == 422, oversized_legacy.text

schema = client.get("/openapi.json")
assert schema.status_code == 200
openapi = schema.json()
paths = openapi["paths"]
assert "/api/pronunciation/status" in paths
assert "/api/pronunciation/audio" in paths
assert paths["/api/pronunciation/audio"]["get"]["deprecated"] is True
body_schema = paths["/api/pronunciation/audio"]["post"]["requestBody"]["content"]["application/json"]["schema"]
ref_name = body_schema["$ref"].rsplit("/", 1)[-1]
payload_schema = openapi["components"]["schemas"][ref_name]
assert payload_schema["properties"]["text"]["maxLength"] == 64
assert payload_schema["properties"]["text"]["minLength"] == 1

print("OK: v5.8.6 pronunciation routes execute from mgc.routers.pronunciation with auth, validation and safe fallback preserved")
