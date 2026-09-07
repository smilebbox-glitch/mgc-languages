from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from fastapi.routing import APIRoute  # noqa: E402
from pydantic import ValidationError  # noqa: E402
from mgc.routers.pilot_admin import (  # noqa: E402
    FeatureFlagPayload,
    PILOT_ADMIN_HANDLER_NAMES,
    PilotFeaturePayload,
    PilotGroupPayload,
    PilotGroupStatusPayload,
    PilotGroupUpdatePayload,
    TrackAssignmentPayload,
    build_pilot_admin_router,
)

assert "mgc.legacy_app" not in sys.modules
assert "app" not in sys.modules


def db_session():
    yield object()


def require_roles(*roles: str):
    def dependency():
        return {"roles": roles}
    return dependency


def make_handler(name: str):
    def handler(**kwargs):
        return {"handler": name, "keys": sorted(kwargs)}
    return handler


handlers = {name: make_handler(name) for name in PILOT_ADMIN_HANDLER_NAMES}
router = build_pilot_admin_router(
    db_session=db_session,
    require_roles=require_roles,
    handlers=handlers,
)

expected = {
    ("GET", "/api/admin/pilot/groups", "admin_pilot_groups"),
    ("POST", "/api/admin/pilot/groups", "admin_create_pilot_group"),
    ("PATCH", "/api/admin/pilot/groups/{group_id}/status", "admin_pilot_group_status"),
    ("PATCH", "/api/admin/pilot/groups/{group_id}", "admin_update_pilot_group"),
    ("POST", "/api/admin/pilot/groups/{group_id}/members/{user_id}", "admin_pilot_add_member"),
    ("DELETE", "/api/admin/pilot/groups/{group_id}/members/{user_id}", "admin_pilot_remove_member"),
    ("GET", "/api/admin/pilot/features", "admin_pilot_features"),
    ("POST", "/api/admin/pilot/features", "admin_create_feature"),
    ("PUT", "/api/admin/pilot/groups/{group_id}/features/{flag_key}", "admin_group_feature"),
    ("POST", "/api/admin/pilot/groups/{group_id}/assignments", "admin_group_assignment"),
    ("DELETE", "/api/admin/pilot/groups/{group_id}/assignments/{assignment_id}", "admin_delete_group_assignment"),
    ("GET", "/api/admin/pilot/export.csv", "admin_pilot_export_csv"),
    ("GET", "/api/admin/pilot/governance-summary", "admin_governance_summary"),
}
actual = set()
for route in router.routes:
    assert isinstance(route, APIRoute)
    methods = (route.methods or set()) - {"HEAD", "OPTIONS"}
    assert len(methods) == 1
    actual.add((next(iter(methods)), route.path, route.name))
    assert route.endpoint.__module__ == "mgc.routers.pilot_admin"
assert actual == expected
assert len(actual) == 13

assert PilotGroupPayload.model_json_schema()["properties"]["wave"]["maximum"] == 100
assert PilotGroupStatusPayload.model_json_schema()["properties"]["status"]["pattern"] == "^(draft|active|paused|completed)$"
assert FeatureFlagPayload.model_json_schema()["properties"]["flag_key"]["pattern"] == r"^[a-z0-9_\-]{2,80}$"
assert TrackAssignmentPayload.model_json_schema()["properties"]["target_level"]["pattern"] == "^(A1|A2|B1|B2|C1)$"
assert TrackAssignmentPayload.model_json_schema()["properties"]["due_date"]["pattern"] == r"^$|^\d{4}-\d{2}-\d{2}$"
assert PilotFeaturePayload(enabled=True).enabled is True
assert PilotGroupUpdatePayload().model_dump(exclude_unset=True) == {}

invalid_cases = (
    (PilotGroupPayload, {"name": "x"}),
    (PilotGroupPayload, {"name": "Valid", "wave": 101}),
    (PilotGroupStatusPayload, {"status": "unknown"}),
    (FeatureFlagPayload, {"flag_key": "INVALID KEY", "title": "Title"}),
    (TrackAssignmentPayload, {"language": "chinese", "track_name": "A", "target_level": "A1"}),
    (TrackAssignmentPayload, {"language": "chinese", "track_name": "Valid track", "target_level": "D1"}),
)
for payload_type, kwargs in invalid_cases:
    try:
        payload_type(**kwargs)
    except ValidationError:
        pass
    else:
        raise AssertionError(f"invalid payload unexpectedly accepted: {payload_type.__name__} {kwargs}")

assert len(PILOT_ADMIN_HANDLER_NAMES) == 13
assert "mgc.legacy_app" not in sys.modules
assert "app" not in sys.modules
print("OK: v5.8.9 dependency-light pilot admin router preserves 13 routes and six payload contracts")
