from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from fastapi.routing import APIRoute  # noqa: E402
from pydantic import ValidationError  # noqa: E402
from mgc.routers.admin_ops import (  # noqa: E402
    ADMIN_OPS_HANDLER_NAMES,
    AlertAckPayload,
    build_admin_ops_router,
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


handlers = {name: make_handler(name) for name in ADMIN_OPS_HANDLER_NAMES}
router = build_admin_ops_router(
    db_session=db_session,
    require_roles=require_roles,
    handlers=handlers,
)

expected = {
    ("GET", "/api/admin/slo", "admin_slo"),
    ("GET", "/api/admin/alerts", "admin_alerts"),
    ("PATCH", "/api/admin/alerts/{alert_id}/ack", "admin_alert_ack"),
    ("GET", "/api/admin/learning-error-telemetry", "learning_error_telemetry"),
    ("GET", "/api/admin/pilot-telemetry", "pilot_telemetry"),
    ("GET", "/api/admin/analytics", "admin_analytics"),
    ("GET", "/api/admin/audit", "admin_audit"),
    ("GET", "/api/admin/database/telemetry", "admin_database_telemetry"),
    ("GET", "/api/admin/recovery/evidence", "admin_recovery_evidence"),
    ("GET", "/api/admin/it-dashboard", "admin_it_dashboard"),
    ("POST", "/api/admin/maintenance/cleanup", "admin_maintenance_cleanup"),
    ("GET", "/api/admin/operational-events", "admin_operational_events"),
    ("GET", "/api/admin/system/summary", "admin_system_summary"),
}
actual = set()
for route in router.routes:
    assert isinstance(route, APIRoute)
    methods = (route.methods or set()) - {"HEAD", "OPTIONS"}
    assert len(methods) == 1
    actual.add((next(iter(methods)), route.path, route.name))
    assert route.endpoint.__module__ == "mgc.routers.admin_ops"
assert actual == expected

schema = AlertAckPayload.model_json_schema()["properties"]["note"]
assert schema["default"] == ""
assert schema["maxLength"] == 500
assert AlertAckPayload().note == ""
assert AlertAckPayload(note="ok").note == "ok"
try:
    AlertAckPayload(note="x" * 501)
    raise AssertionError("oversized alert acknowledgement note unexpectedly accepted")
except ValidationError:
    pass

assert set(ADMIN_OPS_HANDLER_NAMES) == {item[2] for item in expected}
assert "mgc.legacy_app" not in sys.modules
assert "app" not in sys.modules
print("OK: v5.9.0 dependency-light admin operations router preserves 13 routes and payload contract")
