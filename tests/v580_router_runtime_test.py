from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB = Path(tempfile.gettempdir()) / "mgc_languages_v580_router.db"
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
    "OIDC_STATE_SECRET": "v580-router-runtime-secret-32-bytes-001",
    "TTS_LEGACY_GET_ENABLED": "false",
    "TTS_CACHE_PERSISTENCE": "ephemeral",
})
sys.path.insert(0, str(ROOT))

from fastapi.routing import APIRoute  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from starlette.routing import Mount  # noqa: E402
import app  # noqa: E402

facade = Path(app.__file__)
assert facade.name == "app.py"
assert facade.stat().st_size < 4_000
assert Path(app._legacy.__file__).name == "legacy_app.py"
assert "@app." not in facade.read_text(encoding="utf-8")

import asgi  # noqa: E402

assert asgi.app is app.app
assert asgi.CONTRACT_REPORT.ok
report = asgi.ROUTER_BINDING_REPORT
assert report.ok
assert report.system_route_count == 5
assert report.health_routes_bound == 2
assert report.readiness_routes_bound == 2
assert report.meta_route_bound
assert report.route_names_preserved
assert report.root_mount_order_preserved
assert report.router_module_owned

expected = {
    ("GET", "/health"),
    ("GET", "/health/live"),
    ("GET", "/ready"),
    ("GET", "/health/ready"),
    ("GET", "/api/meta"),
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
        assert route.endpoint.__module__ == "mgc.routers.system"
assert set(route_indexes) == expected
mount_index = next(
    index for index, route in enumerate(asgi.app.router.routes)
    if isinstance(route, Mount) and getattr(route, "name", None) == "static"
)
assert all(index < mount_index for index in route_indexes.values())

# The facade remains dynamically compatible with post-import modular bindings.
assert app.award_xp is app._legacy.award_xp
assert app.terms_for is app._legacy.terms_for
assert app.current_user is app._legacy.current_user

client = TestClient(asgi.app)
for path in ("/health", "/health/live"):
    response = client.get(path)
    assert response.status_code == 200, response.text
    assert response.json()["service"] == "mgc-languages"
ready = client.get("/ready")
assert ready.status_code == 200, ready.text
meta = client.get("/api/meta")
assert meta.status_code == 200, meta.text
assert meta.json()["chinese_learning_standard"] == "Путунхуа (普通话) — стандартный китайский"
assert meta.json()["pronunciation_transport"] == "POST"

schema = client.get("/openapi.json")
assert schema.status_code == 200
paths = schema.json()["paths"]
for _method, path in expected:
    assert path in paths

print("OK: v5.8.0 facade is thin and five active system routes execute from mgc.routers.system before the root static mount")
