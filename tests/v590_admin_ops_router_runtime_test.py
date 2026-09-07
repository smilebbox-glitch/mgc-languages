from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB = Path(tempfile.gettempdir()) / "mgc_languages_v590_admin_ops_router.db"
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
    "MGC_ADMIN_USERNAME": "v590admin",
    "MGC_ADMIN_PASSWORD": "V590AdminPassword!123456",
    "MGC_ADMIN_DISPLAY_NAME": "v590 Admin",
    "OIDC_STATE_SECRET": "v590-admin-ops-router-secret-32-bytes-0001",
    "TTS_ENABLED": "false",
    "TTS_LEGACY_GET_ENABLED": "false",
    "TTS_CACHE_PERSISTENCE": "ephemeral",
    "RLS_ENABLED": "true",
    "METRICS_TOKEN": "v590metrics",
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
assert asgi.TTS_BINDING_REPORT.ok
report = asgi.ADMIN_OPS_ROUTER_BINDING_REPORT
assert report.ok
assert report.route_count == 13
assert report.mutation_route_count == 2
assert report.route_names_preserved
assert report.response_classes_preserved
assert report.payload_schema_preserved
assert report.root_mount_order_preserved
assert report.router_module_owned
assert report.auth_core_bound
assert report.user_service_bound
assert report.governance_core_bound
assert report.tts_core_bound
assert report.observability_helpers_available

expected = {
    ("GET", "/api/admin/slo"),
    ("GET", "/api/admin/alerts"),
    ("PATCH", "/api/admin/alerts/{alert_id}/ack"),
    ("GET", "/api/admin/learning-error-telemetry"),
    ("GET", "/api/admin/pilot-telemetry"),
    ("GET", "/api/admin/analytics"),
    ("GET", "/api/admin/audit"),
    ("GET", "/api/admin/database/telemetry"),
    ("GET", "/api/admin/recovery/evidence"),
    ("GET", "/api/admin/it-dashboard"),
    ("POST", "/api/admin/maintenance/cleanup"),
    ("GET", "/api/admin/operational-events"),
    ("GET", "/api/admin/system/summary"),
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
        assert route.endpoint.__module__ == "mgc.routers.admin_ops"
assert set(route_indexes) == expected
mount_index = next(
    index for index, route in enumerate(asgi.app.router.routes)
    if isinstance(route, Mount) and getattr(route, "name", None) == "static"
)
assert all(index < mount_index for index in route_indexes.values())

assert app._legacy.require_roles.__module__ == "mgc.auth_core"
assert app._legacy.user_admin_stats.__module__ == "mgc.services.users"
assert app._legacy.audit_event.__module__ == "mgc.governance_core"
assert app._legacy._tts_health.__module__ == "mgc.tts_core"
for name in (
    "admin_slo",
    "admin_alerts",
    "admin_alert_ack",
    "learning_error_telemetry",
    "pilot_telemetry",
    "admin_analytics",
    "admin_audit",
    "admin_database_telemetry",
    "admin_recovery_evidence",
    "admin_it_dashboard",
    "admin_maintenance_cleanup",
    "admin_operational_events",
    "admin_system_summary",
):
    assert getattr(app._legacy, name).__module__ == "mgc.routers.admin_ops"

regular = TestClient(asgi.app)
register = regular.post(
    "/api/register",
    json={
        "username": "v590user",
        "password": "StrongPass123!",
        "display_name": "v590 User",
    },
)
assert register.status_code == 200, register.text
assert regular.get("/api/admin/slo").status_code == 403
assert regular.get("/api/admin/system/summary").status_code == 403

admin = TestClient(asgi.app)
login = admin.post(
    "/api/login",
    json={"username": "v590admin", "password": "V590AdminPassword!123456"},
)
assert login.status_code == 200, login.text
csrf = login.cookies.get("mgc_csrf") or admin.cookies.get("mgc_csrf")
assert csrf
csrf_headers = {"X-CSRF-Token": csrf}

slo = admin.get("/api/admin/slo")
assert slo.status_code == 200, slo.text
assert "slo" in slo.json() and "recovery" in slo.json()

alerts = admin.get("/api/admin/alerts")
assert alerts.status_code == 200, alerts.text
assert "alerts" in alerts.json() and "active_count" in alerts.json()

learning_errors = admin.get("/api/admin/learning-error-telemetry?days=7")
assert learning_errors.status_code == 200, learning_errors.text
assert learning_errors.json()["days"] == 7
assert "HR performance rating" in learning_errors.json()["note"]
assert admin.get("/api/admin/learning-error-telemetry?days=0").status_code == 422

pilot = admin.get("/api/admin/pilot-telemetry")
assert pilot.status_code == 200, pilot.text
assert "users_total" in pilot.json()
assert "tts_cache" in pilot.json()

analytics = admin.get("/api/admin/analytics")
assert analytics.status_code == 200, analytics.text
assert "users" in analytics.json() and "lifetime_xp" in analytics.json()

db_telemetry = admin.get("/api/admin/database/telemetry")
assert db_telemetry.status_code == 200, db_telemetry.text
assert set(db_telemetry.json()) == {"queries", "pool"}

recovery = admin.get("/api/admin/recovery/evidence")
assert recovery.status_code == 200, recovery.text
assert "objectives" in recovery.json()

it_dashboard = admin.get("/api/admin/it-dashboard")
assert it_dashboard.status_code == 200, it_dashboard.text
assert "readiness" in it_dashboard.json()
assert "database" in it_dashboard.json()
assert "tts" in it_dashboard.json()

cleanup = admin.post(
    "/api/admin/maintenance/cleanup?dry_run=true",
    headers=csrf_headers,
)
assert cleanup.status_code == 200, cleanup.text
assert cleanup.json()["dry_run"] is True
assert "counts" in cleanup.json()

operational = admin.get("/api/admin/operational-events?limit=20")
assert operational.status_code == 200, operational.text
assert isinstance(operational.json(), list)
assert admin.get("/api/admin/operational-events?limit=0").status_code == 422

summary = admin.get("/api/admin/system/summary")
assert summary.status_code == 200, summary.text
summary_data = summary.json()
assert "ready" in summary_data and "checks" in summary_data
assert "Путунхуа (普通话)" in summary_data["chinese_learning_standard"]

with app.SessionLocal() as db:
    alert = app.PilotAlert(
        alert_key="v590.manual",
        severity="warning",
        status="open",
        component="test",
        title="v590 manual alert",
        detail="runtime router contract",
        metadata_json="{}",
    )
    db.add(alert)
    db.commit()
    db.refresh(alert)
    alert_id = alert.id

ack = admin.patch(
    f"/api/admin/alerts/{alert_id}/ack",
    headers=csrf_headers,
    json={"note": "checked by v590"},
)
assert ack.status_code == 200, ack.text
assert ack.json() == {"ok": True, "status": "acknowledged"}
assert admin.patch(
    f"/api/admin/alerts/{alert_id}/ack",
    headers=csrf_headers,
    json={"note": "x" * 501},
).status_code == 422

audit = admin.get("/api/admin/audit?event_type=pilot_alert.acknowledged&limit=20")
assert audit.status_code == 200, audit.text
assert any(row["event_type"] == "pilot_alert.acknowledged" for row in audit.json())

openapi = admin.get("/openapi.json")
assert openapi.status_code == 200, openapi.text
paths = openapi.json()["paths"]
for _, path in expected:
    assert path in paths

print("OK: v5.9.0 admin operations router preserves RBAC, telemetry, recovery, TTS state and audit semantics")
