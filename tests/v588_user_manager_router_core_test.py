from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from fastapi.routing import APIRoute  # noqa: E402
from mgc.routers.users_manager import (  # noqa: E402
    USER_MANAGER_HANDLER_NAMES,
    UserDepartmentPayload,
    UserRolePayload,
    build_user_manager_router,
)

assert "mgc.legacy_app" not in sys.modules
assert "app" not in sys.modules


def db_session():
    yield object()


def current_user():
    return object()


def require_roles(*roles: str):
    def dependency():
        return {"roles": roles}
    return dependency


def make_handler(name: str):
    def handler(**kwargs):
        return {"handler": name, "keys": sorted(kwargs)}
    return handler


handlers = {name: make_handler(name) for name in USER_MANAGER_HANDLER_NAMES}
router = build_user_manager_router(
    db_session=db_session,
    current_user=current_user,
    require_roles=require_roles,
    handlers=handlers,
)

expected = {
    ("GET", "/api/admin/users", "admin_users"),
    ("GET", "/api/admin/users/{user_id}/learning-stats", "admin_user_learning_stats"),
    ("PATCH", "/api/admin/users/{user_id}/role", "admin_set_role"),
    ("PATCH", "/api/admin/users/{user_id}/department", "admin_set_department"),
    ("GET", "/api/manager/team", "manager_team"),
    ("GET", "/api/manager/team/{user_id}/learning-stats", "manager_user_learning_stats"),
}
actual = set()
for route in router.routes:
    assert isinstance(route, APIRoute)
    methods = (route.methods or set()) - {"HEAD", "OPTIONS"}
    assert len(methods) == 1
    actual.add((next(iter(methods)), route.path, route.name))
    assert route.endpoint.__module__ == "mgc.routers.users_manager"
assert actual == expected

assert UserRolePayload.model_json_schema()["properties"]["role"]["pattern"] == "^(user|manager|editor|admin)$"
department_schema = UserDepartmentPayload.model_json_schema()["properties"]["department"]
assert department_schema["minLength"] == 1
assert department_schema["maxLength"] == 160

try:
    UserRolePayload(role="owner")
    raise AssertionError("invalid role unexpectedly accepted")
except Exception:
    pass
try:
    UserDepartmentPayload(department="")
    raise AssertionError("empty department unexpectedly accepted")
except Exception:
    pass

assert set(USER_MANAGER_HANDLER_NAMES) == {
    "admin_users",
    "admin_user_learning_stats",
    "admin_set_role",
    "admin_set_department",
    "manager_team",
    "manager_user_learning_stats",
}
assert "mgc.legacy_app" not in sys.modules
assert "app" not in sys.modules
print("OK: v5.8.8 dependency-light user/manager router preserves six routes and payload contracts")
