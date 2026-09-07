from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB = Path(tempfile.gettempdir()) / "mgc_languages_v591_notifications_router.db"
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
    "MGC_ADMIN_USERNAME": "v591admin",
    "MGC_ADMIN_PASSWORD": "V591AdminPassword!123456",
    "OIDC_STATE_SECRET": "v591-notifications-router-secret-32-bytes-001",
    "TTS_ENABLED": "false",
    "TTS_LEGACY_GET_ENABLED": "false",
    "TTS_CACHE_PERSISTENCE": "ephemeral",
    "RLS_ENABLED": "true",
    "METRICS_TOKEN": "v591metrics",
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
assert asgi.LEARNING_BINDING_REPORT.ok
report = asgi.NOTIFICATIONS_ROUTER_BINDING_REPORT
assert report.ok
assert report.route_count == 4
assert report.settings_route_count == 2
assert report.nudge_route_count == 2
assert report.mutation_route_count == 2
assert report.route_names_preserved
assert report.response_classes_preserved
assert report.payload_schema_preserved
assert report.root_mount_order_preserved
assert report.router_module_owned
assert report.auth_core_bound
assert report.learning_service_bound

expected = {
    ("GET", "/api/notifications/settings"),
    ("PUT", "/api/notifications/settings"),
    ("GET", "/api/notifications/pending"),
    ("POST", "/api/notifications/{nudge_id}/read"),
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
        assert route.endpoint.__module__ == "mgc.routers.notifications"
assert set(route_indexes) == expected
mount_index = next(
    index for index, route in enumerate(asgi.app.router.routes)
    if isinstance(route, Mount) and getattr(route, "name", None) == "static"
)
assert all(index < mount_index for index in route_indexes.values())

assert app._legacy.current_user.__module__ == "mgc.auth_core"
assert app._legacy.get_profile.__module__ == "mgc.services.learning"
for name in (
    "get_notification_settings",
    "set_notification_settings",
    "pending_notifications",
    "read_notification",
):
    assert getattr(app._legacy, name).__module__ == "mgc.routers.notifications"

anonymous = TestClient(asgi.app)
assert anonymous.get("/api/notifications/settings").status_code == 401

client = TestClient(asgi.app)
register = client.post(
    "/api/register",
    json={
        "username": "v591user",
        "password": "StrongPass123!",
        "display_name": "v591 User",
    },
)
assert register.status_code == 200, register.text
csrf = register.cookies.get("mgc_csrf") or client.cookies.get("mgc_csrf")
assert csrf
headers = {"X-CSRF-Token": csrf}

settings = client.get("/api/notifications/settings")
assert settings.status_code == 200, settings.text
assert settings.json()["mode"] in {"off", "minimal", "normal", "active"}

updated = client.put(
    "/api/notifications/settings",
    headers=headers,
    json={
        "mode": "active",
        "window_start": "07:30",
        "window_end": "20:15",
        "browser_enabled": True,
    },
)
assert updated.status_code == 200, updated.text
assert updated.json() == {
    "ok": True,
    "mode": "active",
    "window_start": "07:30",
    "window_end": "20:15",
    "browser_enabled": True,
}
assert client.put(
    "/api/notifications/settings",
    headers=headers,
    json={
        "mode": "invalid",
        "window_start": "07:30",
        "window_end": "20:15",
        "browser_enabled": False,
    },
).status_code == 422

me = client.get("/api/me")
assert me.status_code == 200, me.text
user_id = me.json()["id"]
with app.SessionLocal() as db:
    nudge = app.LearningNudge(
        user_id=user_id,
        title="v591 review",
        body="Пора повторить несколько терминов",
        target_view="topics",
        reason="v591_test",
    )
    db.add(nudge)
    db.commit()
    db.refresh(nudge)
    nudge_id = nudge.id

pending = client.get("/api/notifications/pending")
assert pending.status_code == 200, pending.text
pending_data = pending.json()
assert pending_data["settings"]["mode"] == "active"
assert pending_data["settings"]["browser_enabled"] is True
assert any(item["id"] == nudge_id for item in pending_data["items"])

read = client.post(f"/api/notifications/{nudge_id}/read", headers=headers)
assert read.status_code == 200, read.text
assert read.json() == {"ok": True}
assert client.post("/api/notifications/999999/read", headers=headers).status_code == 404

pending_after = client.get("/api/notifications/pending")
assert pending_after.status_code == 200, pending_after.text
assert all(item["id"] != nudge_id for item in pending_after.json()["items"])

with app.SessionLocal() as db:
    row = db.get(app.NotificationPreference, user_id)
    assert row is not None
    assert row.mode == "active"
    assert row.window_start == "07:30"
    assert row.window_end == "20:15"
    assert row.browser_enabled is True
    saved_nudge = db.get(app.LearningNudge, nudge_id)
    assert saved_nudge is not None and saved_nudge.read is True

openapi = client.get("/openapi.json")
assert openapi.status_code == 200, openapi.text
for _, path in expected:
    assert path in openapi.json()["paths"]

print("OK: v5.9.1 notifications router preserves auth, settings, pending-nudge and read semantics")
