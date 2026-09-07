from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB = Path(tempfile.gettempdir()) / "mgc_languages_v589_pilot_admin_router.db"
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
    "MGC_ADMIN_USERNAME": "v589admin",
    "MGC_ADMIN_PASSWORD": "V589AdminPassword!123456",
    "MGC_ADMIN_DISPLAY_NAME": "v589 Admin",
    "OIDC_STATE_SECRET": "v589-pilot-admin-router-secret-32-bytes-001",
    "TTS_ENABLED": "false",
    "TTS_LEGACY_GET_ENABLED": "false",
    "TTS_CACHE_PERSISTENCE": "ephemeral",
    "RLS_ENABLED": "true",
    "METRICS_TOKEN": "v589metrics",
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
report = asgi.PILOT_ADMIN_ROUTER_BINDING_REPORT
assert report.ok
assert report.route_count == 13
assert report.group_route_count == 9
assert report.feature_route_count == 2
assert report.assignment_route_count == 2
assert report.export_route_count == 1
assert report.governance_route_count == 1
assert report.mutation_route_count == 9
assert report.route_names_preserved
assert report.response_classes_preserved
assert report.payload_schemas_preserved
assert report.root_mount_order_preserved
assert report.router_module_owned
assert report.auth_core_bound
assert report.user_service_bound
assert report.governance_core_bound

expected = {
    ("GET", "/api/admin/pilot/groups"),
    ("POST", "/api/admin/pilot/groups"),
    ("PATCH", "/api/admin/pilot/groups/{group_id}/status"),
    ("PATCH", "/api/admin/pilot/groups/{group_id}"),
    ("POST", "/api/admin/pilot/groups/{group_id}/members/{user_id}"),
    ("DELETE", "/api/admin/pilot/groups/{group_id}/members/{user_id}"),
    ("GET", "/api/admin/pilot/features"),
    ("POST", "/api/admin/pilot/features"),
    ("PUT", "/api/admin/pilot/groups/{group_id}/features/{flag_key}"),
    ("POST", "/api/admin/pilot/groups/{group_id}/assignments"),
    ("DELETE", "/api/admin/pilot/groups/{group_id}/assignments/{assignment_id}"),
    ("GET", "/api/admin/pilot/export.csv"),
    ("GET", "/api/admin/pilot/governance-summary"),
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
        assert route.endpoint.__module__ == "mgc.routers.pilot_admin"
assert set(route_indexes) == expected
mount_index = next(
    index for index, route in enumerate(asgi.app.router.routes)
    if isinstance(route, Mount) and getattr(route, "name", None) == "static"
)
assert all(index < mount_index for index in route_indexes.values())

assert app._legacy.require_roles.__module__ == "mgc.auth_core"
assert app._legacy.user_admin_stats.__module__ == "mgc.services.users"
assert app._legacy.audit_event.__module__ == "mgc.governance_core"
for name in (
    "admin_pilot_groups",
    "admin_create_pilot_group",
    "admin_pilot_group_status",
    "admin_update_pilot_group",
    "admin_pilot_add_member",
    "admin_pilot_remove_member",
    "admin_pilot_features",
    "admin_create_feature",
    "admin_group_feature",
    "admin_group_assignment",
    "admin_delete_group_assignment",
    "admin_pilot_export_csv",
    "admin_governance_summary",
):
    assert getattr(app._legacy, name).__module__ == "mgc.routers.pilot_admin"

admin = TestClient(asgi.app)
login = admin.post(
    "/api/login",
    json={"username": "v589admin", "password": "V589AdminPassword!123456"},
)
assert login.status_code == 200, login.text
admin_csrf = admin.cookies.get("mgc_csrf")
assert admin_csrf
admin_h = {"X-CSRF-Token": admin_csrf}

user = TestClient(asgi.app)
registered = user.post(
    "/api/register",
    json={
        "username": "v589user",
        "password": "StrongPass123!",
        "display_name": "v589 Pilot User",
    },
)
assert registered.status_code == 200, registered.text
user_id = registered.json()["user"]["id"]

assert user.get("/api/admin/pilot/groups").status_code == 403
assert user.get("/api/admin/pilot/features").status_code == 403
assert user.get("/api/admin/pilot/governance-summary").status_code == 403

payload = {
    "name": "v589 R&D Wave",
    "department": "R&D",
    "description": "v5.8.9 pilot router regression",
    "status": "draft",
    "wave": 9,
    "starts_at": None,
    "ends_at": None,
}
created = admin.post("/api/admin/pilot/groups", headers=admin_h, json=payload)
assert created.status_code == 200, created.text
group = created.json()
group_id = group["id"]
assert group["name"] == "v589 R&D Wave"
assert group["department"] == "R&D"
assert group["wave"] == 9
assert group["members"] == []

duplicate = admin.post("/api/admin/pilot/groups", headers=admin_h, json=payload)
assert duplicate.status_code == 409, duplicate.text

bad_dates = admin.post(
    "/api/admin/pilot/groups",
    headers=admin_h,
    json={
        **payload,
        "name": "v589 Bad Dates",
        "starts_at": "2026-09-10T12:00:00Z",
        "ends_at": "2026-09-09T12:00:00Z",
    },
)
assert bad_dates.status_code == 400, bad_dates.text

added = admin.post(
    f"/api/admin/pilot/groups/{group_id}/members/{user_id}",
    headers=admin_h,
)
assert added.status_code == 200, added.text
assert {row["id"] for row in added.json()["members"]} == {user_id}

feature = admin.post(
    "/api/admin/pilot/features",
    headers=admin_h,
    json={
        "flag_key": "v589_feature",
        "title": "v589 Feature",
        "description": "router regression",
        "default_enabled": True,
    },
)
assert feature.status_code == 200, feature.text
assert feature.json() == {"ok": True, "flag_key": "v589_feature"}

features = admin.get("/api/admin/pilot/features")
assert features.status_code == 200, features.text
catalog = {row["flag_key"]: row for row in features.json()}
assert "v589_feature" in catalog
assert catalog["v589_feature"]["default_enabled"] is True

override = admin.put(
    f"/api/admin/pilot/groups/{group_id}/features/v589_feature",
    headers=admin_h,
    json={"enabled": False},
)
assert override.status_code == 200, override.text
assert override.json()["enabled"] is False

assignment = admin.post(
    f"/api/admin/pilot/groups/{group_id}/assignments",
    headers=admin_h,
    json={
        "language": "chinese",
        "track_name": "Putonghua R&D",
        "topic": "R&D и инженерия",
        "target_level": "A2",
        "due_date": "2026-10-01",
    },
)
assert assignment.status_code == 200, assignment.text
assignment_id = assignment.json()["id"]

activated = admin.patch(
    f"/api/admin/pilot/groups/{group_id}/status",
    headers=admin_h,
    json={"status": "active"},
)
assert activated.status_code == 200, activated.text
assert activated.json()["status"] == "active"

updated = admin.patch(
    f"/api/admin/pilot/groups/{group_id}",
    headers=admin_h,
    json={"description": "updated", "wave": 10},
)
assert updated.status_code == 200, updated.text
assert updated.json()["description"] == "updated"
assert updated.json()["wave"] == 10
assert updated.json()["features"]["v589_feature"] is False
assert {row["id"] for row in updated.json()["assignments"]} == {assignment_id}

listing = admin.get("/api/admin/pilot/groups")
assert listing.status_code == 200, listing.text
assert group_id in {row["id"] for row in listing.json()}

export = admin.get("/api/admin/pilot/export.csv", params={"group_id": group_id})
assert export.status_code == 200, export.text
assert export.headers["content-type"].startswith("text/csv")
assert f"mgc_pilot_results_group_{group_id}.csv" in export.headers["content-disposition"]
assert "chinese_putonghua_known" in export.text
assert "v589user" in export.text

governance = admin.get("/api/admin/pilot/governance-summary")
assert governance.status_code == 200, governance.text
gov = governance.json()
assert gov["groups_total"] >= 1
assert gov["groups_active"] >= 1
assert 10 in gov["waves"]
assert gov["memberships"] >= 1
assert gov["assignments"] >= 1
assert "Путунхуа (普通话)" in gov["chinese_standard"]

removed_assignment = admin.delete(
    f"/api/admin/pilot/groups/{group_id}/assignments/{assignment_id}",
    headers=admin_h,
)
assert removed_assignment.status_code == 200, removed_assignment.text
assert removed_assignment.json() == {"ok": True, "id": assignment_id}

removed_member = admin.delete(
    f"/api/admin/pilot/groups/{group_id}/members/{user_id}",
    headers=admin_h,
)
assert removed_member.status_code == 200, removed_member.text
assert removed_member.json() == {"ok": True}

with app.SessionLocal() as db:
    rows = db.scalars(app.select(app.AuditLog).where(app.AuditLog.event_type.like("pilot.%"))).all()
    event_types = {row.event_type for row in rows}
    assert {
        "pilot.group.create",
        "pilot.group.member.add",
        "pilot.feature.upsert",
        "pilot.feature.group_override",
        "pilot.assignment.create",
        "pilot.group.status",
        "pilot.group.update",
        "pilot.assignment.delete",
        "pilot.group.member.remove",
    } <= event_types

schema = admin.get("/openapi.json")
assert schema.status_code == 200
paths = schema.json()["paths"]
for _method, path in expected:
    assert path in paths

print("OK: v5.8.9 pilot admin router preserves rollout groups, flags, assignments, export, governance, RBAC and audit")
