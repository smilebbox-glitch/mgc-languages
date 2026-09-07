from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB = Path(tempfile.gettempdir()) / "mgc_languages_v588_user_manager_router.db"
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
    "MGC_ADMIN_USERNAME": "v588admin",
    "MGC_ADMIN_PASSWORD": "V588AdminPassword!123456",
    "MGC_ADMIN_DISPLAY_NAME": "v588 Admin",
    "OIDC_STATE_SECRET": "v588-user-manager-router-secret-32-bytes-001",
    "TTS_ENABLED": "false",
    "TTS_LEGACY_GET_ENABLED": "false",
    "TTS_CACHE_PERSISTENCE": "ephemeral",
    "RLS_ENABLED": "true",
    "METRICS_TOKEN": "v588metrics",
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
assert asgi.GOVERNANCE_BINDING_REPORT.ok
report = asgi.USER_MANAGER_ROUTER_BINDING_REPORT
assert report.ok
assert report.route_count == 6
assert report.admin_route_count == 4
assert report.manager_route_count == 2
assert report.mutation_route_count == 2
assert report.route_names_preserved
assert report.response_classes_preserved
assert report.payload_schema_preserved
assert report.root_mount_order_preserved
assert report.router_module_owned
assert report.auth_core_bound
assert report.user_service_bound
assert report.manager_policy_bound
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

users_service = app._legacy.MGC_USER_SERVICE_BINDINGS
assert app._legacy.user_view is users_service.user_view
assert app._legacy.user_admin_stats is users_service.user_admin_stats
assert app._legacy._manager_target_allowed is users_service.manager_target_allowed
assert app._legacy.user_admin_stats.__module__ == "mgc.services.users"
assert app._legacy._manager_target_allowed.__module__ == "mgc.services.users"
assert app._legacy.current_user.__module__ == "mgc.auth_core"
assert app._legacy.audit_event.__module__ == "mgc.governance_core"
for name in (
    "admin_users",
    "admin_user_learning_stats",
    "admin_set_role",
    "admin_set_department",
    "manager_team",
    "manager_user_learning_stats",
):
    assert getattr(app._legacy, name).__module__ == "mgc.routers.users_manager"

admin = TestClient(asgi.app)
login = admin.post(
    "/api/login",
    json={"username": "v588admin", "password": "V588AdminPassword!123456"},
)
assert login.status_code == 200, login.text
admin_id = login.json()["user"]["id"]
admin_csrf = admin.cookies.get("mgc_csrf")
assert admin_csrf
admin_h = {"X-CSRF-Token": admin_csrf}


def register(username: str, display_name: str):
    client = TestClient(asgi.app)
    response = client.post(
        "/api/register",
        json={
            "username": username,
            "password": "StrongPass123!",
            "display_name": display_name,
        },
    )
    assert response.status_code == 200, response.text
    return client, response.json()["user"]["id"]


rnd_user, rnd_id = register("v588_rnd_user", "v588 R&D User")
quality_user, quality_id = register("v588_quality_user", "v588 Quality User")
manager_client, manager_id = register("v588_manager", "v588 Manager")

for user_id, department in (
    (rnd_id, "R&D"),
    (quality_id, "Quality"),
    (manager_id, "R&D"),
):
    response = admin.patch(
        f"/api/admin/users/{user_id}/department",
        headers=admin_h,
        json={"department": department},
    )
    assert response.status_code == 200, response.text
    assert response.json()["user"]["department"] == department

promote = admin.patch(
    f"/api/admin/users/{manager_id}/role",
    headers=admin_h,
    json={"role": "manager"},
)
assert promote.status_code == 200, promote.text
assert promote.json()["user"]["role"] == "manager"

invalid_role = admin.patch(
    f"/api/admin/users/{rnd_id}/role",
    headers=admin_h,
    json={"role": "owner"},
)
assert invalid_role.status_code == 422, invalid_role.text

self_demote = admin.patch(
    f"/api/admin/users/{admin_id}/role",
    headers=admin_h,
    json={"role": "user"},
)
assert self_demote.status_code == 400, self_demote.text
assert "Нельзя снять роль admin" in self_demote.json()["detail"]

normal_user_admin = rnd_user.get("/api/admin/users")
assert normal_user_admin.status_code == 403, normal_user_admin.text

manager = TestClient(asgi.app)
manager_login = manager.post(
    "/api/login",
    json={"username": "v588_manager", "password": "StrongPass123!"},
)
assert manager_login.status_code == 200, manager_login.text
assert manager_login.json()["user"]["role"] == "manager"

team = manager.get("/api/manager/team")
assert team.status_code == 200, team.text
team_data = team.json()
assert team_data["department"] == "R&D"
team_ids = {row["id"] for row in team_data["users"]}
assert manager_id in team_ids
assert rnd_id in team_ids
assert quality_id not in team_ids

own_department_stats = manager.get(f"/api/manager/team/{rnd_id}/learning-stats")
assert own_department_stats.status_code == 200, own_department_stats.text
assert own_department_stats.json()["id"] == rnd_id

other_department_stats = manager.get(f"/api/manager/team/{quality_id}/learning-stats")
assert other_department_stats.status_code == 403, other_department_stats.text
assert "своего подразделения" in other_department_stats.json()["detail"]

admin_other_stats = admin.get(f"/api/admin/users/{quality_id}/learning-stats")
assert admin_other_stats.status_code == 200, admin_other_stats.text
assert admin_other_stats.json()["id"] == quality_id

users = admin.get("/api/admin/users")
assert users.status_code == 200, users.text
listed_ids = {row["id"] for row in users.json()}
assert {admin_id, rnd_id, quality_id, manager_id} <= listed_ids

with app.SessionLocal() as db:
    audit_rows = db.scalars(
        app.select(app.AuditLog).where(
            app.AuditLog.event_type.in_(["user.role.change", "user.department.change"])
        )
    ).all()
    event_types = [row.event_type for row in audit_rows]
    assert "user.role.change" in event_types
    assert event_types.count("user.department.change") >= 3

schema = admin.get("/openapi.json")
assert schema.status_code == 200
paths = schema.json()["paths"]
for _method, path in expected:
    assert path in paths

print("OK: v5.8.8 user/manager router preserves RBAC, department boundary, mutations, audit and user-service contracts")
