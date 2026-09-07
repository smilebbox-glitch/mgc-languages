from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB = Path(tempfile.gettempdir()) / "mgc_languages_v587_users_manager_router.db"
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
    "MGC_ADMIN_USERNAME": "v587admin",
    "MGC_ADMIN_PASSWORD": "V587AdminPassword!123456",
    "OIDC_STATE_SECRET": "v587-users-manager-router-secret-32-bytes-0001",
    "TTS_ENABLED": "false",
    "TTS_LEGACY_GET_ENABLED": "false",
    "TTS_CACHE_PERSISTENCE": "ephemeral",
    "RLS_ENABLED": "true",
    "METRICS_TOKEN": "v587metrics",
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
report = asgi.USERS_MANAGER_ROUTER_BINDING_REPORT
assert report.ok
assert report.route_count == 6
assert report.admin_route_count == 4
assert report.manager_route_count == 2
assert report.route_names_preserved
assert report.response_classes_preserved
assert report.payload_schemas_preserved
assert report.root_mount_order_preserved
assert report.router_module_owned
assert report.auth_core_bound
assert report.user_service_bound
assert report.terminology_service_bound
assert report.governance_core_bound

expected = {
    ("GET", "/api/admin/users"),
    ("GET", "/api/admin/users/{user_id}/learning-stats"),
    ("PATCH", "/api/admin/users/{user_id}/role"),
    ("PATCH", "/api/admin/users/{user_id}/department"),
    ("GET", "/api/manager/team"),
    ("GET", "/api/manager/team/{user_id}/learning-stats"),
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
        assert route.endpoint.__module__ == "mgc.routers.users_manager"
assert set(route_indexes) == expected
mount_index = next(
    index for index, route in enumerate(asgi.app.router.routes)
    if isinstance(route, Mount) and getattr(route, "name", None) == "static"
)
assert all(index < mount_index for index in route_indexes.values())

legacy_routes = app._legacy.MGC_LEGACY_USERS_MANAGER_ROUTES
assert all(route.endpoint.__module__ == "mgc.legacy_app" for route in legacy_routes.values())
assert app._legacy.require_roles.__module__ == "mgc.auth_core"
assert app._legacy.user_view.__module__ == "mgc.services.users"
assert app._legacy.user_admin_stats.__module__ == "mgc.services.users"
assert app._legacy.terms_for.__module__ == "mgc.services.terminology"
assert app._legacy.audit_event.__module__ == "mgc.governance_core"

admin = TestClient(asgi.app)
login = admin.post(
    "/api/login",
    json={"username": "v587admin", "password": "V587AdminPassword!123456"},
)
assert login.status_code == 200, login.text
admin_h = {"X-CSRF-Token": admin.cookies.get("mgc_csrf")}


def register(username: str, display_name: str):
    client = TestClient(asgi.app)
    response = client.post(
        "/api/register",
        json={"username": username, "password": "StrongPass123!", "display_name": display_name},
    )
    assert response.status_code == 200, response.text
    return client, response.json()["user"]["id"]


manager_client, manager_id = register("v587manager", "v587 Manager")
rd_client, rd_id = register("v587rduser", "v587 R&D User")
quality_client, quality_id = register("v587quality", "v587 Quality User")
ordinary_client, ordinary_id = register("v587ordinary", "v587 Ordinary User")

for user_id, department in (
    (manager_id, "R&D"),
    (rd_id, "R&D"),
    (quality_id, "Quality"),
    (ordinary_id, "General"),
):
    response = admin.patch(
        f"/api/admin/users/{user_id}/department",
        headers=admin_h,
        json={"department": department},
    )
    assert response.status_code == 200, response.text
role = admin.patch(
    f"/api/admin/users/{manager_id}/role",
    headers=admin_h,
    json={"role": "manager"},
)
assert role.status_code == 200, role.text

manager_client = TestClient(asgi.app)
assert manager_client.post(
    "/api/login",
    json={"username": "v587manager", "password": "StrongPass123!"},
).status_code == 200
ordinary_client = TestClient(asgi.app)
assert ordinary_client.post(
    "/api/login",
    json={"username": "v587ordinary", "password": "StrongPass123!"},
).status_code == 200

assert ordinary_client.get("/api/admin/users").status_code == 403
assert ordinary_client.get("/api/manager/team").status_code == 403
assert manager_client.get("/api/admin/users").status_code == 403

team = manager_client.get("/api/manager/team")
assert team.status_code == 200, team.text
team_data = team.json()
assert team_data["department"] == "R&D"
team_ids = {row["id"] for row in team_data["users"]}
assert manager_id in team_ids
assert rd_id in team_ids
assert quality_id not in team_ids
assert ordinary_id not in team_ids

same_department = manager_client.get(f"/api/manager/team/{rd_id}/learning-stats")
assert same_department.status_code == 200, same_department.text
other_department = manager_client.get(f"/api/manager/team/{quality_id}/learning-stats")
assert other_department.status_code == 403, other_department.text
admin_other = admin.get(f"/api/manager/team/{quality_id}/learning-stats")
assert admin_other.status_code == 200, admin_other.text

admin_users = admin.get("/api/admin/users")
assert admin_users.status_code == 200, admin_users.text
admin_ids = {row["id"] for row in admin_users.json()}
assert {manager_id, rd_id, quality_id, ordinary_id} <= admin_ids
admin_stats = admin.get(f"/api/admin/users/{rd_id}/learning-stats")
assert admin_stats.status_code == 200, admin_stats.text
assert admin_stats.json()["id"] == rd_id

assert admin.patch(
    f"/api/admin/users/{rd_id}/role",
    headers=admin_h,
    json={"role": "owner"},
).status_code == 422
assert admin.patch(
    f"/api/admin/users/{rd_id}/department",
    headers=admin_h,
    json={"department": ""},
).status_code == 422

schema = admin.get("/openapi.json")
assert schema.status_code == 200
paths = schema.json()["paths"]
for _, path in expected:
    assert path in paths

print("OK: v5.8.7 users/manager routes execute from mgc.routers.users_manager with RBAC and department boundary preserved")
