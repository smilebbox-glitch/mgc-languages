from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB = Path(tempfile.gettempdir()) / "mgc_languages_v587_tts_core.db"
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
    "MGC_ADMIN_USERNAME": "v587admin",
    "MGC_ADMIN_PASSWORD": "V587AdminPassword!123456",
    "OIDC_STATE_SECRET": "v587-tts-core-secret-32-bytes-long-000001",
    "TTS_ENABLED": "false",
    "TTS_LEGACY_GET_ENABLED": "false",
    "TTS_CACHE_PERSISTENCE": "ephemeral",
    "TTS_CACHE_DIR": str(Path(tempfile.gettempdir()) / "mgc-v587-tts-cache"),
    "RLS_ENABLED": "true",
    "METRICS_TOKEN": "v587metrics",
})
sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient  # noqa: E402
import app  # noqa: E402
import asgi  # noqa: E402

assert asgi.app is app.app
assert asgi.CONTRACT_REPORT.ok
report = asgi.TTS_BINDING_REPORT
assert report.ok
assert report.cache_bound
assert report.circuit_bound
assert report.synthesis_bound
assert report.health_bound
assert report.pronunciation_response_bound
assert report.state_bound
assert report.config_preserved
assert report.lru_cache_preserved
assert report.observability_state_compatible
assert report.hooks_captured
assert report.module_owned

bindings = app._legacy.MGC_TTS_CORE_BINDINGS
assert app._legacy._TTS_SEMAPHORE is bindings.semaphore
assert app._legacy._TTS_RUNTIME_LOCK is bindings.runtime_lock
assert app._legacy._TTS_RUNTIME is bindings.runtime
assert app._legacy._TTS_HEALTH_LOCK is bindings.health_lock
assert app._legacy._TTS_HEALTH_CACHE is bindings.health_cache
assert app._legacy._tts_cache_path is bindings.cache_path
assert app._legacy._tts_cache_read is bindings.cache_read
assert app._legacy._prune_tts_cache is bindings.prune_cache
assert app._legacy._tts_cache_write is bindings.cache_write
assert app._legacy._tts_circuit_open is bindings.circuit_open
assert app._legacy._tts_mark_success is bindings.mark_success
assert app._legacy._tts_mark_failure is bindings.mark_failure
assert app._legacy._synthesize_wav is bindings.synthesize_wav
assert app._legacy._tts_health is bindings.health
assert app._legacy._pronunciation_response is bindings.pronunciation_response
for function in (
    app._legacy._tts_cache_path,
    app._legacy._tts_cache_read,
    app._legacy._prune_tts_cache,
    app._legacy._tts_cache_write,
    app._legacy._tts_circuit_open,
    app._legacy._tts_mark_success,
    app._legacy._tts_mark_failure,
    app._legacy._synthesize_wav,
    app._legacy._tts_health,
    app._legacy._pronunciation_response,
):
    assert function.__module__ == "mgc.tts_core"

pronunciation = asgi.PRONUNCIATION_ROUTER_BINDING_REPORT
assert pronunciation.ok
assert pronunciation.route_count == 2
assert pronunciation.legacy_get_enabled is False
assert pronunciation.legacy_get_route_count == 0
assert pronunciation.tts_core_bound
assert pronunciation.auth_core_bound

legacy_pronunciation = app._legacy.MGC_LEGACY_PRONUNCIATION_ROUTES
status_endpoint = legacy_pronunciation[("GET", "/api/pronunciation/status")].endpoint
post_endpoint = legacy_pronunciation[("POST", "/api/pronunciation/audio")].endpoint
assert status_endpoint.__globals__["_tts_health"] is bindings.health
assert post_endpoint.__globals__["_pronunciation_response"] is bindings.pronunciation_response

client = TestClient(asgi.app)
metrics = client.get(
    "/metrics",
    headers={"Authorization": "Bearer v587metrics"},
)
assert metrics.status_code == 200, metrics.text
for metric_name in (
    "mgc_tts_success_total",
    "mgc_tts_failure_total",
    "mgc_tts_disk_cache_hits_total",
    "mgc_tts_circuit_open",
    "mgc_tts_cache_writable",
):
    assert metric_name in metrics.text
assert "mgc_tts_success_total 0" in metrics.text
assert "mgc_tts_failure_total 0" in metrics.text

register = client.post(
    "/api/register",
    json={
        "username": "v587user",
        "password": "StrongPass123!",
        "display_name": "v587 TTS User",
    },
)
assert register.status_code == 200, register.text
csrf = register.cookies.get("mgc_csrf") or client.cookies.get("mgc_csrf")
assert csrf
headers = {"X-CSRF-Token": csrf}

status = client.get("/api/pronunciation/status")
assert status.status_code == 200, status.text
status_data = status.json()
assert status_data["server_available"] is False
assert status_data["offline"] is False
assert status_data["runtime"] == bindings.runtime

fallback = client.post(
    "/api/pronunciation/audio",
    headers=headers,
    json={"language": "chinese", "text": "你好", "rate": 0.9},
)
assert fallback.status_code == 503, fallback.text
assert "browser fallback" in fallback.json()["detail"]

metrics_after = client.get(
    "/metrics",
    headers={"Authorization": "Bearer v587metrics"},
)
assert metrics_after.status_code == 200, metrics_after.text
assert "mgc_tts_circuit_open 0" in metrics_after.text

print("OK: v5.8.7 production runtime uses one extracted TTS state across pronunciation and observability")
