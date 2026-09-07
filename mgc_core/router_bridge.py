from __future__ import annotations

from dataclasses import dataclass
from types import ModuleType
from typing import Any

from fastapi import FastAPI
from fastapi.routing import APIRoute
from starlette.routing import Mount

from mgc.routers.system import build_system_router


SYSTEM_ROUTE_CONTRACT = {
    ("GET", "/health"),
    ("GET", "/health/live"),
    ("GET", "/ready"),
    ("GET", "/health/ready"),
    ("GET", "/api/meta"),
}


@dataclass(frozen=True)
class RouterBindingReport:
    ok: bool
    system_route_count: int
    health_routes_bound: int
    readiness_routes_bound: int
    meta_route_bound: bool
    route_names_preserved: bool
    root_mount_order_preserved: bool
    router_module_owned: bool


def _key(route: APIRoute) -> tuple[str, str]:
    methods = sorted((route.methods or set()) - {"HEAD", "OPTIONS"})
    if len(methods) != 1:
        raise RuntimeError(f"system route must have one explicit method: {route.path} {methods}")
    return methods[0], route.path


def _single_route_index(application: FastAPI, key: tuple[str, str]) -> int:
    matches = [
        index
        for index, route in enumerate(application.router.routes)
        if isinstance(route, APIRoute) and _key(route) == key
    ]
    if len(matches) != 1:
        raise RuntimeError(f"system route contract drifted for {key[0]} {key[1]}: {len(matches)} matches")
    return matches[0]


def bind_system_router(module: ModuleType, application: FastAPI) -> RouterBindingReport:
    """Replace legacy system APIRoutes in-place so the root static mount keeps its order."""
    existing = getattr(module, "MGC_ROUTER_BINDING_REPORT", None)
    if isinstance(existing, RouterBindingReport) and existing.ok:
        return existing

    required = (
        "APP_VERSION",
        "INSTANCE_ID",
        "APP_ENV",
        "AUTH_MODE",
        "REGISTRATION_ENABLED",
        "TTS_LEGACY_GET_ENABLED",
        "TTS_CACHE_PERSISTENCE",
        "EXPECTED_ALEMBIC_HEAD",
        "OTEL_ENABLED",
        "db_session",
        "readiness_checks",
        "update_recovery_state",
        "_tts_health",
        "_recovery_view",
    )
    missing = [name for name in required if not hasattr(module, name)]
    if missing:
        raise RuntimeError(f"legacy system router dependencies are incomplete: {missing}")

    extracted = build_system_router(
        app_version=str(module.APP_VERSION),
        instance_id=str(module.INSTANCE_ID),
        app_env=str(module.APP_ENV),
        auth_mode=str(module.AUTH_MODE),
        registration_enabled=bool(module.REGISTRATION_ENABLED),
        tts_legacy_get_enabled=bool(module.TTS_LEGACY_GET_ENABLED),
        tts_cache_persistence=str(module.TTS_CACHE_PERSISTENCE),
        expected_alembic_head=str(module.EXPECTED_ALEMBIC_HEAD),
        otel_enabled=bool(module.OTEL_ENABLED),
        db_session=module.db_session,
        readiness_checks=module.readiness_checks,
        update_recovery_state=module.update_recovery_state,
        tts_health=module._tts_health,
        recovery_view=module._recovery_view,
    )
    new_routes = {
        _key(route): route for route in extracted.routes if isinstance(route, APIRoute)
    }
    if set(new_routes) != SYSTEM_ROUTE_CONTRACT:
        raise RuntimeError(
            f"extracted system router contract drifted: {sorted(set(new_routes) ^ SYSTEM_ROUTE_CONTRACT)}"
        )

    originals: dict[tuple[str, str], APIRoute] = {}
    replaced: dict[tuple[str, str], APIRoute] = {}
    route_names_preserved = True
    for key in sorted(SYSTEM_ROUTE_CONTRACT):
        index = _single_route_index(application, key)
        old_route = application.router.routes[index]
        assert isinstance(old_route, APIRoute)
        new_route = new_routes[key]
        if old_route.name != new_route.name:
            route_names_preserved = False
        originals[key] = old_route
        application.router.routes[index] = new_route
        replaced[key] = new_route

    # Keep historical module attributes usable while active route ownership moves.
    module.health = replaced[("GET", "/health")].endpoint
    module.ready = replaced[("GET", "/ready")].endpoint
    module.meta = replaced[("GET", "/api/meta")].endpoint
    module.MGC_LEGACY_SYSTEM_ROUTES = originals
    module.MGC_SYSTEM_ROUTER = extracted

    mount_indices = [
        index
        for index, route in enumerate(application.router.routes)
        if isinstance(route, Mount) and getattr(route, "name", None) == "static"
    ]
    root_mount_order_preserved = bool(mount_indices) and all(
        _single_route_index(application, key) < mount_indices[0]
        for key in SYSTEM_ROUTE_CONTRACT
    )
    router_module_owned = all(
        route.endpoint.__module__ == "mgc.routers.system" for route in replaced.values()
    )
    health_count = sum(1 for key in replaced if key[1] in {"/health", "/health/live"})
    readiness_count = sum(1 for key in replaced if key[1] in {"/ready", "/health/ready"})
    report = RouterBindingReport(
        ok=(
            len(replaced) == len(SYSTEM_ROUTE_CONTRACT)
            and route_names_preserved
            and root_mount_order_preserved
            and router_module_owned
        ),
        system_route_count=len(replaced),
        health_routes_bound=health_count,
        readiness_routes_bound=readiness_count,
        meta_route_bound=(("GET", "/api/meta") in replaced),
        route_names_preserved=route_names_preserved,
        root_mount_order_preserved=root_mount_order_preserved,
        router_module_owned=router_module_owned,
    )
    if not report.ok:
        raise RuntimeError("v5.8.0 system router binding failed closed")
    module.MGC_ROUTER_BINDING_REPORT = report
    return report


__all__ = ["RouterBindingReport", "SYSTEM_ROUTE_CONTRACT", "bind_system_router"]
