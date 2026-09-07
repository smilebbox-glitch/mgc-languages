from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB = Path(tempfile.gettempdir()) / "mgc_languages_v581_observability.db"
try:
    DB.unlink()
except FileNotFoundError:
    pass

os.environ.update({
    "DATABASE_URL": f"sqlite:///{DB}",
    "AUTO_CREATE_SCHEMA": "true",
    "APP_ENV": "development",
    "AUTH_MODE": "local",
    "REGISTRATION_ENABLED": "true",
    "TRUSTED_HOSTS": "testserver,localhost,127.0.0.1",
    "OIDC_STATE_SECRET": "v581-observability-secret-32-bytes-001",
    "TTS_LEGACY_GET_ENABLED": "false",
    "TTS_CACHE_PERSISTENCE": "ephemeral",
    "METRICS_ENABLED": "true",
    "METRICS_TOKEN": "v581metrics",
})
sys.path.insert(0, str(ROOT))

from fastapi import Request  # noqa: E402
from fastapi.routing import APIRoute  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from starlette.routing import Mount  # noqa: E402
import app  # noqa: E402
import asgi  # noqa: E402

assert asgi.app is app.app
assert asgi.CONTRACT_REPORT.ok
assert asgi.ROUTER_BINDING_REPORT.ok
report = asgi.OBSERVABILITY_ROUTER_BINDING_REPORT
assert report.ok
assert report.metrics_route_bound
assert report.route_name_preserved
assert report.response_class_preserved
assert report.root_mount_order_preserved
assert report.router_module_owned
assert report.renderer_module_owned

active = [
    (index, route)
    for index, route in enumerate(asgi.app.router.routes)
    if isinstance(route, APIRoute)
    and route.path == "/metrics"
    and ((route.methods or set()) - {"HEAD", "OPTIONS"}) == {"GET"}
]
assert len(active) == 1
metrics_index, metrics_route = active[0]
assert metrics_route.endpoint.__module__ == "mgc.routers.observability"
mount_index = next(
    index for index, route in enumerate(asgi.app.router.routes)
    if isinstance(route, Mount) and getattr(route, "name", None) == "static"
)
assert metrics_index < mount_index
assert app.metrics is metrics_route.endpoint

legacy = app._legacy
legacy_route = legacy.MGC_LEGACY_OBSERVABILITY_ROUTES[("GET", "/metrics")]
assert legacy_route.endpoint.__module__ == "mgc.legacy_app"

# Freeze variable snapshot sources so old and new renderers can be compared byte-for-byte.
legacy.db_query_telemetry_snapshot = lambda: {
    "p95_ms": 8.5,
    "slow_queries": 2,
    "lifetime_slow_queries": 5,
}
legacy.db_pool_snapshot = lambda: {
    "checked_out": 1,
    "capacity": 10,
    "saturation_percent": 10.0,
}
legacy.recovery_evidence_snapshot = lambda: {
    "backup": {"age_minutes": 25},
    "restore_rehearsal": {"age_days": 2},
}
legacy.slo_snapshot = lambda: {
    "availability_percent": 99.95,
    "error_rate_percent": 0.05,
    "p95_ms": 140.0,
    "samples": 100,
}
legacy._recovery_view = lambda: {"state": "healthy"}
legacy._tts_circuit_open = lambda: False
legacy._tts_health = lambda *args, **kwargs: {
    "cache_writable": True,
    "server_available": False,
    "engine": "browser-fallback",
}

scope = {
    "type": "http",
    "asgi": {"version": "3.0"},
    "http_version": "1.1",
    "method": "GET",
    "scheme": "http",
    "path": "/metrics",
    "raw_path": b"/metrics",
    "query_string": b"",
    "headers": [(b"authorization", b"Bearer v581metrics")],
    "client": ("testclient", 50000),
    "server": ("testserver", 80),
}
legacy_text = legacy_route.endpoint(Request(scope))
extracted_text = metrics_route.endpoint(Request(scope))
assert extracted_text == legacy_text

client = TestClient(asgi.app)
missing = client.get("/metrics")
assert missing.status_code == 401
assert missing.headers.get("www-authenticate") == "Bearer"
assert client.get("/metrics", headers={"Authorization": "Bearer wrong"}).status_code == 401
metrics = client.get("/metrics", headers={"Authorization": "Bearer v581metrics"})
assert metrics.status_code == 200, metrics.text
for name in (
    "mgc_http_requests_total",
    "mgc_database_metrics_available",
    "mgc_db_query_p95_ms",
    "mgc_db_pool_saturation_percent",
    "mgc_recovery_backup_age_minutes",
    "mgc_recovery_rpo_target_minutes",
    "mgc_slo_availability_percent",
    "mgc_tts_success_total",
):
    assert name in metrics.text, name

schema = client.get("/openapi.json")
assert schema.status_code == 200
assert "/metrics" in schema.json()["paths"]
assert "get" in schema.json()["paths"]["/metrics"]

print("OK: v5.8.1 active /metrics is router-owned, auth-compatible and byte-compatible with the frozen legacy Prometheus contract")
