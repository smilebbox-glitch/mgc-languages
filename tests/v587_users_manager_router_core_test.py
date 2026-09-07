from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from fastapi.routing import APIRoute  # noqa: E402
from pydantic import ValidationError  # noqa: E402
from mgc.routers.users_manager import (  # noqa: E402
    UserDepartmentPayload,
    UserRolePayload,
    build_users_manager_router,
)

assert "mgc.legacy_app" not in sys.modules
assert "app" not in sys.modules


def db_session():
    yield object()


role_calls: list[tuple[str, ...]] = []


def require_roles(*roles: str):
    role_calls.append(tuple(roles))

    def dependency():
        return object()

    return dependency


def handler(**kwargs):
    return {"ok": True}


router = build_users_manager_router(
    db_session=db_session,
    require_roles=require_roles,
    handlers={
        "admin_users": handler,
        "admin_user_learning_stats": handler,
        "admin_set_role": handler,
        "admin_set_department": handler,
        "manager_team": handler,
        "manager_user_learning_stats": handler,
    },
)

expected = {
    ("GET", "/api/admin/users"),
    ("GET", "/api/admin/users/{user_id}/learning-stats"),
    ("PATCH", "/api/admin/users/{user_id}/role"),
    ("PATCH", "/api/admin/users/{user_id}/department"),
    ("GET", "/api/manager/team"),
    ("GET", "/api/manager/team/{user_id}/learning-stats"),
}
actual = set()
for route in router.routes:
    if not isinstance(route, APIRoute):
        continue
    methods = (route.methods or set()) - {"HEAD", "OPTIONS"}
    assert len(methods) == 1
    actual.add((next(iter(methods)), route.path))
    assert route.endpoint.__module__ == "mgc.routers.users_manager"
assert actual == expected
assert role_calls.count(("admin",)) == 4
assert role_calls.count(("manager", "admin")) == 2

assert UserDepartmentPayload(department="R&D").department == "R&D"
for bad_department in ("", "x" * 161):
    try:
        UserDepartmentPayload(department=bad_department)
        raise AssertionError("invalid department accepted")
    except ValidationError:
        pass
for role in ("user", "manager", "editor", "admin"):
    assert UserRolePayload(role=role).role == role
try:
    UserRolePayload(role="owner")
    raise AssertionError("invalid role accepted")
except ValidationError:
    pass

assert "mgc.legacy_app" not in sys.modules
assert "app" not in sys.modules
print("OK: v5.8.7 users/manager router builds independently with exact six-route RBAC contract")
