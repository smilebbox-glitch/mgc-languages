from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from fastapi import FastAPI  # noqa: E402
from fastapi.routing import APIRoute  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from mgc.observability import render_prometheus_metrics  # noqa: E402
from mgc.routers.observability import build_observability_router  # noqa: E402


text = render_prometheus_metrics(
    http_requests={("GET", "/health", 200): 3},
    http_latency={("GET", "/health"): 0.125},
    reliability_runtime={"database_failures_total": 2, "http_5xx_total": 1},
    tts_runtime={"success_total": 9, "failure_total": 2, "disk_cache_hits": 4},
    db_gauges={
        "operational_events_24h": 11,
        "operational_errors_24h": 2,
        "expired_sessions": 1,
        "open_alerts": 3,
        "srs_due": 7,
        "question_attempts_total": 19,
    },
    db_queries={"p95_ms": 12.5, "slow_queries": 2, "lifetime_slow_queries": 8},
    db_pool={"checked_out": 2, "capacity": 12, "saturation_percent": 16.67},
    recovery_evidence={
        "backup": {"age_minutes": 15},
        "restore_rehearsal": {"age_days": 4},
    },
    slo={"availability_percent": 99.9, "error_rate_percent": 0.1, "p95_ms": 180.0, "samples": 42},
    recovery={"state": "degraded"},
    rpo_target_minutes=1440,
    rto_target_minutes=60,
    tts_circuit_open=True,
    tts_cache_writable=False,
)
assert 'mgc_http_requests_total{method="GET",path="/health",status="200"} 3' in text
assert 'mgc_http_request_duration_seconds_sum{method="GET",path="/health"} 0.125000' in text
assert "mgc_database_failures_total 2" in text
assert "mgc_database_metrics_available 1" in text
assert "mgc_db_query_p95_ms 12.5" in text
assert "mgc_db_pool_saturation_percent 16.67" in text
assert "mgc_recovery_backup_age_minutes 15.0" in text
assert "mgc_recovery_state 1" in text
assert "mgc_tts_circuit_open 1" in text
assert "mgc_tts_cache_writable 0" in text
assert text.endswith("\n")

unavailable = render_prometheus_metrics(
    http_requests={},
    http_latency={},
    reliability_runtime={},
    tts_runtime={"success_total": 0, "failure_total": 0, "disk_cache_hits": 0},
    db_gauges=None,
    db_queries={"p95_ms": 0, "slow_queries": 0, "lifetime_slow_queries": 0},
    db_pool={},
    recovery_evidence={"backup": {"age_minutes": None}, "restore_rehearsal": {"age_days": None}},
    slo={"availability_percent": 100, "error_rate_percent": 0, "p95_ms": 0, "samples": 0},
    recovery={"state": "healthy"},
    rpo_target_minutes=60,
    rto_target_minutes=30,
    tts_circuit_open=False,
    tts_cache_writable=True,
)
assert "mgc_database_metrics_available 0" in unavailable
assert "mgc_operational_events_24h" not in unavailable

router = build_observability_router(
    metrics_enabled=True,
    metrics_token="v581-token",
    metrics_text=lambda: text,
)
routes = [route for route in router.routes if isinstance(route, APIRoute)]
assert len(routes) == 1
assert routes[0].path == "/metrics"
assert routes[0].methods == {"GET"}
assert routes[0].endpoint.__module__ == "mgc.routers.observability"

api = FastAPI()
api.include_router(router)
client = TestClient(api)
unauthorized = client.get("/metrics")
assert unauthorized.status_code == 401
assert unauthorized.headers.get("www-authenticate") == "Bearer"
assert client.get("/metrics", headers={"Authorization": "Bearer wrong"}).status_code == 401
ok = client.get("/metrics", headers={"Authorization": "Bearer v581-token"})
assert ok.status_code == 200
assert ok.text == text
assert ok.headers["content-type"].startswith("text/plain")

disabled_api = FastAPI()
disabled_api.include_router(
    build_observability_router(metrics_enabled=False, metrics_token="", metrics_text=lambda: text)
)
assert TestClient(disabled_api).get("/metrics").status_code == 404
assert "app" not in sys.modules
print("OK: v5.8.1 Prometheus renderer and observability APIRouter preserve metrics/auth semantics without importing the monolith")
