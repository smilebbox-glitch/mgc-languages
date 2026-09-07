from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from types import ModuleType
from typing import Any

from fastapi import FastAPI
from fastapi.routing import APIRoute
from sqlalchemy import func, select
from starlette.routing import Mount

from mgc.observability import render_prometheus_metrics
from mgc.routers.observability import build_observability_router


OBSERVABILITY_ROUTE_CONTRACT = {("GET", "/metrics")}


@dataclass(frozen=True)
class ObservabilityRouterBindingReport:
    ok: bool
    metrics_route_bound: bool
    route_name_preserved: bool
    response_class_preserved: bool
    root_mount_order_preserved: bool
    router_module_owned: bool
    renderer_module_owned: bool


def _key(route: APIRoute) -> tuple[str, str]:
    methods = sorted((route.methods or set()) - {"HEAD", "OPTIONS"})
    if len(methods) != 1:
        raise RuntimeError(f"observability route must have one explicit method: {route.path} {methods}")
    return methods[0], route.path


def _single_route_index(application: FastAPI, key: tuple[str, str]) -> int:
    matches = [
        index
        for index, route in enumerate(application.router.routes)
        if isinstance(route, APIRoute) and _key(route) == key
    ]
    if len(matches) != 1:
        raise RuntimeError(
            f"observability route contract drifted for {key[0]} {key[1]}: {len(matches)} matches"
        )
    return matches[0]


def _database_gauges(module: ModuleType) -> dict[str, int] | None:
    try:
        now = datetime.now(timezone.utc)
        with module.SessionLocal() as metric_db:
            op_24h = int(
                metric_db.scalar(
                    select(func.count())
                    .select_from(module.OperationalEvent)
                    .where(module.OperationalEvent.created_at >= now - timedelta(hours=24))
                )
                or 0
            )
            op_err_24h = int(
                metric_db.scalar(
                    select(func.count())
                    .select_from(module.OperationalEvent)
                    .where(
                        module.OperationalEvent.created_at >= now - timedelta(hours=24),
                        module.OperationalEvent.severity == "error",
                    )
                )
                or 0
            )
            expired_sessions = int(
                metric_db.scalar(
                    select(func.count())
                    .select_from(module.LoginSession)
                    .where(module.LoginSession.expires_at <= now)
                )
                or 0
            )
            open_alerts = int(
                metric_db.scalar(
                    select(func.count())
                    .select_from(module.PilotAlert)
                    .where(module.PilotAlert.status.in_(["open", "acknowledged"]))
                )
                or 0
            )
            module.apply_rls_context(metric_db, system_admin=True)
            srs_due = int(
                metric_db.scalar(
                    select(func.count())
                    .select_from(module.SRSCard)
                    .where(module.SRSCard.due_at <= now)
                )
                or 0
            )
            q_total = int(
                metric_db.scalar(select(func.count()).select_from(module.QuestionAttempt)) or 0
            )
        return {
            "operational_events_24h": op_24h,
            "operational_errors_24h": op_err_24h,
            "expired_sessions": expired_sessions,
            "open_alerts": open_alerts,
            "srs_due": srs_due,
            "question_attempts_total": q_total,
        }
    except Exception:
        return None


def _metrics_text(module: ModuleType) -> str:
    with module._METRIC_LOCK:
        http_requests = dict(module._METRIC_REQUESTS)
        http_latency = dict(module._METRIC_LATENCY)
    with module._RELIABILITY_LOCK:
        reliability_runtime = dict(module._RELIABILITY_RUNTIME)
    with module._TTS_RUNTIME_LOCK:
        tts_runtime = dict(module._TTS_RUNTIME)

    return render_prometheus_metrics(
        http_requests=http_requests,
        http_latency=http_latency,
        reliability_runtime=reliability_runtime,
        tts_runtime=tts_runtime,
        db_gauges=_database_gauges(module),
        db_queries=module.db_query_telemetry_snapshot(),
        db_pool=module.db_pool_snapshot(),
        recovery_evidence=module.recovery_evidence_snapshot(),
        slo=module.slo_snapshot(),
        recovery=module._recovery_view(),
        rpo_target_minutes=int(module.RPO_TARGET_MINUTES),
        rto_target_minutes=int(module.RTO_TARGET_MINUTES),
        tts_circuit_open=bool(module._tts_circuit_open()),
        tts_cache_writable=bool(module._tts_health().get("cache_writable")),
    )


def bind_observability_router(
    module: ModuleType,
    application: FastAPI,
) -> ObservabilityRouterBindingReport:
    """Replace the legacy /metrics APIRoute in-place with the extracted router."""
    existing = getattr(module, "MGC_OBSERVABILITY_ROUTER_BINDING_REPORT", None)
    if isinstance(existing, ObservabilityRouterBindingReport) and existing.ok:
        return existing

    required = (
        "METRICS_ENABLED",
        "METRICS_TOKEN",
        "SessionLocal",
        "OperationalEvent",
        "LoginSession",
        "PilotAlert",
        "SRSCard",
        "QuestionAttempt",
        "apply_rls_context",
        "db_query_telemetry_snapshot",
        "db_pool_snapshot",
        "recovery_evidence_snapshot",
        "slo_snapshot",
        "_recovery_view",
        "_tts_circuit_open",
        "_tts_health",
        "RPO_TARGET_MINUTES",
        "RTO_TARGET_MINUTES",
        "_METRIC_LOCK",
        "_METRIC_REQUESTS",
        "_METRIC_LATENCY",
        "_RELIABILITY_LOCK",
        "_RELIABILITY_RUNTIME",
        "_TTS_RUNTIME_LOCK",
        "_TTS_RUNTIME",
    )
    missing = [name for name in required if not hasattr(module, name)]
    if missing:
        raise RuntimeError(f"legacy observability dependencies are incomplete: {missing}")

    extracted = build_observability_router(
        metrics_enabled=bool(module.METRICS_ENABLED),
        metrics_token=str(module.METRICS_TOKEN or ""),
        metrics_text=lambda: _metrics_text(module),
    )
    new_routes = {
        _key(route): route for route in extracted.routes if isinstance(route, APIRoute)
    }
    if set(new_routes) != OBSERVABILITY_ROUTE_CONTRACT:
        raise RuntimeError(
            "extracted observability router contract drifted: "
            + str(sorted(set(new_routes) ^ OBSERVABILITY_ROUTE_CONTRACT))
        )

    key = ("GET", "/metrics")
    index = _single_route_index(application, key)
    old_route = application.router.routes[index]
    assert isinstance(old_route, APIRoute)
    new_route = new_routes[key]
    route_name_preserved = old_route.name == new_route.name
    response_class_preserved = old_route.response_class is new_route.response_class
    application.router.routes[index] = new_route

    module.metrics = new_route.endpoint
    module.MGC_LEGACY_OBSERVABILITY_ROUTES = {key: old_route}
    module.MGC_OBSERVABILITY_ROUTER = extracted

    mount_indices = [
        route_index
        for route_index, route in enumerate(application.router.routes)
        if isinstance(route, Mount) and getattr(route, "name", None) == "static"
    ]
    root_mount_order_preserved = bool(mount_indices) and index < mount_indices[0]
    router_module_owned = new_route.endpoint.__module__ == "mgc.routers.observability"
    renderer_module_owned = render_prometheus_metrics.__module__ == "mgc.observability"
    report = ObservabilityRouterBindingReport(
        ok=(
            route_name_preserved
            and response_class_preserved
            and root_mount_order_preserved
            and router_module_owned
            and renderer_module_owned
        ),
        metrics_route_bound=True,
        route_name_preserved=route_name_preserved,
        response_class_preserved=response_class_preserved,
        root_mount_order_preserved=root_mount_order_preserved,
        router_module_owned=router_module_owned,
        renderer_module_owned=renderer_module_owned,
    )
    if not report.ok:
        raise RuntimeError("v5.8.1 observability router binding failed closed")
    module.MGC_OBSERVABILITY_ROUTER_BINDING_REPORT = report
    return report


__all__ = [
    "OBSERVABILITY_ROUTE_CONTRACT",
    "ObservabilityRouterBindingReport",
    "bind_observability_router",
]
