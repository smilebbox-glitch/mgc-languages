from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB = Path(tempfile.gettempdir()) / "mgc_languages_v582_auth_router.db"
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
    "OIDC_STATE_SECRET": "v582-auth-router-runtime-secret-32-bytes-001",
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
report = asgi.AUTH_ROUTER_BINDING_REPORT
assert report.ok
assert report.auth_route_count == 6
assert report.local_route_count == 4
assert report.oidc_route_count == 2
assert report.route_names_preserved
assert report.root_mount_order_preserved
assert report.router_module_owned
assert report.current_user_dependency_is_extracted
assert report.session_factory_is_extracted

expected = {
    ("POST", "/api/register"),
    ("POST", "/api/login"),
    ("POST", "/api/logout"),
    ("GET", "/api/auth/oidc/login"),
    ("GET", "/api/auth/oidc/callback"),
    ("GET", "/api/me"),
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
        assert route.endpoint.__module__ == "mgc.routers.auth"
assert set(route_indexes) == expected
mount_index = next(
    index for index, route in enumerate(asgi.app.router.routes)
    if isinstance(route, Mount) and getattr(route, "name", None) == "static"
)
assert all(index < mount_index for index in route_indexes.values())

# Production auth routes use the extracted v5.7.5 primitives directly.
assert app._legacy.current_user.__module__ == "mgc.auth_core"
assert app._legacy.create_login_session.__module__ == "mgc.auth_core"
assert app._legacy.login.__module__ == "mgc.routers.auth"
assert app._legacy.logout.__module__ == "mgc.routers.auth"
assert app._legacy.me.__module__ == "mgc.routers.auth"

client = TestClient(asgi.app)
registered = client.post(
    "/api/register",
    json={
        "username": "v582user",
        "password": "StrongPass123!",
        "display_name": "v582 User",
    },
)
assert registered.status_code == 200, registered.text
payload = registered.json()
assert payload["ok"] is True
assert payload["user"]["username"] == "v582user"
csrf = registered.cookies.get("mgc_csrf") or client.cookies.get("mgc_csrf")
assert csrf
assert client.cookies.get("mgc_session")

me = client.get("/api/me")
assert me.status_code == 200, me.text
assert me.json()["username"] == "v582user"

# Login semantics stay unchanged.
bad = TestClient(asgi.app).post(
    "/api/login",
    json={"username": "v582user", "password": "WrongPassword!"},
)
assert bad.status_code == 401, bad.text

# Logout still requires CSRF for an authenticated session and clears both cookies.
logout = client.post("/api/logout", headers={"X-CSRF-Token": csrf})
assert logout.status_code == 200, logout.text
assert logout.json() == {"ok": True}
assert client.get("/api/me").status_code == 401

relogin = client.post(
    "/api/login",
    json={"username": "v582user", "password": "StrongPass123!"},
)
assert relogin.status_code == 200, relogin.text
assert relogin.cookies.get("mgc_session") or client.cookies.get("mgc_session")

# OIDC endpoints remain present but fail closed in local-auth mode before network activity.
assert client.get("/api/auth/oidc/login").status_code == 404
assert client.get("/api/auth/oidc/callback").status_code == 404

schema = client.get("/openapi.json")
assert schema.status_code == 200
paths = schema.json()["paths"]
for _method, path in expected:
    assert path in paths

print("OK: v5.8.2 six active auth routes execute from mgc.routers.auth with extracted auth/session primitives")
