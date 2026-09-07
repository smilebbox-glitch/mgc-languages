from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from fastapi.routing import APIRoute  # noqa: E402
from pydantic import ValidationError  # noqa: E402
from mgc.routers.notifications import (  # noqa: E402
    NOTIFICATION_HANDLER_NAMES,
    NotificationSettingsPayload,
    build_notifications_router,
)

assert "mgc.legacy_app" not in sys.modules
assert "app" not in sys.modules


def db_session():
    yield object()


def current_user():
    return object()


def make_handler(name: str):
    def handler(**kwargs):
        return {"handler": name, "keys": sorted(kwargs)}
    return handler


handlers = {name: make_handler(name) for name in NOTIFICATION_HANDLER_NAMES}
router = build_notifications_router(
    db_session=db_session,
    current_user=current_user,
    handlers=handlers,
)
expected = {
    ("GET", "/api/notifications/settings", "get_notification_settings"),
    ("PUT", "/api/notifications/settings", "set_notification_settings"),
    ("GET", "/api/notifications/pending", "pending_notifications"),
    ("POST", "/api/notifications/{nudge_id}/read", "read_notification"),
}
actual = set()
for route in router.routes:
    assert isinstance(route, APIRoute)
    methods = (route.methods or set()) - {"HEAD", "OPTIONS"}
    assert len(methods) == 1
    actual.add((next(iter(methods)), route.path, route.name))
    assert route.endpoint.__module__ == "mgc.routers.notifications"
assert actual == expected

valid = NotificationSettingsPayload(
    mode="normal", window_start="08:30", window_end="19:00", browser_enabled=True
)
assert valid.mode == "normal"
assert valid.browser_enabled is True
for payload in (
    {"mode": "spam", "window_start": "08:00", "window_end": "19:00"},
    {"mode": "normal", "window_start": "25:00", "window_end": "19:00"},
    {"mode": "normal", "window_start": "08:00", "window_end": "19:99"},
):
    try:
        NotificationSettingsPayload(**payload)
        raise AssertionError(f"invalid notification payload accepted: {payload}")
    except ValidationError:
        pass

assert len(NOTIFICATION_HANDLER_NAMES) == 4
assert set(NOTIFICATION_HANDLER_NAMES) == {item[2] for item in expected}
assert "mgc.legacy_app" not in sys.modules
assert "app" not in sys.modules
print("OK: v5.9.1 dependency-light notifications router preserves four routes and settings schema")
