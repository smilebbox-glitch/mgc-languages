from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from fastapi.routing import APIRoute  # noqa: E402
from mgc.routers.system import build_system_router  # noqa: E402


def db_session():
    yield object()


def readiness_checks(_db):
    return True, {"database": "ok"}


def update_recovery_state(**_kwargs):
    return {"state": "healthy"}


def tts_health(*_args, **_kwargs):
    return {"server_available": False}


def recovery_view():
    return {"state": "healthy"}


router = build_system_router(
    app_version="5.7.1",
    instance_id="test-instance",
    app_env="development",
    auth_mode="local",
    registration_enabled=True,
    tts_legacy_get_enabled=False,
    tts_cache_persistence="ephemeral",
    expected_alembic_head="c57d0a31f570",
    otel_enabled=False,
    db_session=db_session,
    readiness_checks=readiness_checks,
    update_recovery_state=update_recovery_state,
    tts_health=tts_health,
    recovery_view=recovery_view,
)
routes = [route for route in router.routes if isinstance(route, APIRoute)]
keys = {(next(iter(route.methods)), route.path) for route in routes}
assert keys == {
    ("GET", "/health"),
    ("GET", "/health/live"),
    ("GET", "/ready"),
    ("GET", "/health/ready"),
    ("GET", "/api/meta"),
}
meta = next(route for route in routes if route.path == "/api/meta").endpoint()
assert meta["title"] == "MGC Languages"
assert meta["chinese_learning_standard"] == "Путунхуа (普通话) — стандартный китайский"
assert meta["registration_enabled"] is True
assert "app" not in sys.modules
print("OK: v5.8.0 system APIRouter is dependency-light and owns the five extracted route contracts")
