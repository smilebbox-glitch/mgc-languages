from __future__ import annotations

from dataclasses import dataclass
from types import ModuleType

from fastapi import FastAPI
from fastapi.routing import APIRoute
from starlette.routing import Mount

from mgc.routers.shift_analytics import build_shift_analytics_router
from mgc.services.practice_isolation import practice_storage_session_id


SHIFT_ANALYTICS_ROUTE_CONTRACT = {
    ("POST", "/api/shift-simulations"),
    ("GET", "/api/shift-simulations/history"),
}


@dataclass(frozen=True)
class ShiftAnalyticsRouterBindingReport:
    ok: bool
    route_count: int
    root_mount_order_preserved: bool
    router_module_owned: bool
    auth_core_bound: bool
    practice_result_bound: bool
    user_scoped_storage: bool


def _key(route: APIRoute) -> tuple[str, str]:
    methods = sorted((route.methods or set()) - {"HEAD", "OPTIONS"})
    if len(methods) != 1:
        raise RuntimeError(f"shift analytics route must have one explicit method: {route.path} {methods}")
    return methods[0], route.path


def bind_shift_analytics_router(
    module: ModuleType,
    application: FastAPI,
) -> ShiftAnalyticsRouterBindingReport:
    """Add user-scoped Shift Simulation history before the root StaticFiles mount."""
    existing = getattr(module, "MGC_SHIFT_ANALYTICS_ROUTER_BINDING_REPORT", None)
    if isinstance(existing, ShiftAnalyticsRouterBindingReport) and existing.ok:
        return existing

    auth_core_bound = getattr(module.current_user, "__module__", "") == "mgc.auth_core"
    if not auth_core_bound:
        raise RuntimeError("shift analytics router must bind after extracted current_user")

    practice_result_model = getattr(module, "PracticeResult", None)
    practice_result_bound = bool(
        practice_result_model is not None
        and getattr(practice_result_model, "__tablename__", "") == "practice_results"
    )
    if not practice_result_bound:
        raise RuntimeError("shift analytics router requires the existing PracticeResult model")

    extracted = build_shift_analytics_router(
        db_session=module.db_session,
        current_user=module.current_user,
        practice_result_model=practice_result_model,
        storage_session_id=practice_storage_session_id,
    )
    routes = [route for route in extracted.routes if isinstance(route, APIRoute)]
    keys = {_key(route) for route in routes}
    if keys != SHIFT_ANALYTICS_ROUTE_CONTRACT:
        raise RuntimeError(
            "shift analytics router contract drifted: "
            + str(sorted(keys ^ SHIFT_ANALYTICS_ROUTE_CONTRACT))
        )

    existing_keys = {
        _key(route)
        for route in application.router.routes
        if isinstance(route, APIRoute)
    }
    duplicates = keys & existing_keys
    if duplicates:
        raise RuntimeError("shift analytics routes already exist: " + str(sorted(duplicates)))

    mount_indices = [
        index
        for index, route in enumerate(application.router.routes)
        if isinstance(route, Mount) and getattr(route, "name", None) == "static"
    ]
    if not mount_indices:
        raise RuntimeError("shift analytics router requires the root static mount")
    insert_at = mount_indices[0]
    for route in routes:
        application.router.routes.insert(insert_at, route)
        insert_at += 1

    final_mount_indices = [
        index
        for index, route in enumerate(application.router.routes)
        if isinstance(route, Mount) and getattr(route, "name", None) == "static"
    ]
    bound_indices = [
        index
        for index, route in enumerate(application.router.routes)
        if isinstance(route, APIRoute) and _key(route) in SHIFT_ANALYTICS_ROUTE_CONTRACT
    ]
    root_mount_order_preserved = bool(final_mount_indices) and all(
        index < final_mount_indices[0] for index in bound_indices
    )
    router_module_owned = all(
        route.endpoint.__module__ == "mgc.routers.shift_analytics" for route in routes
    )
    user_scoped_storage = practice_storage_session_id(7, "shift-demo") != practice_storage_session_id(8, "shift-demo")

    report = ShiftAnalyticsRouterBindingReport(
        ok=(
            len(routes) == 2
            and root_mount_order_preserved
            and router_module_owned
            and auth_core_bound
            and practice_result_bound
            and user_scoped_storage
        ),
        route_count=len(routes),
        root_mount_order_preserved=root_mount_order_preserved,
        router_module_owned=router_module_owned,
        auth_core_bound=auth_core_bound,
        practice_result_bound=practice_result_bound,
        user_scoped_storage=user_scoped_storage,
    )
    if not report.ok:
        raise RuntimeError("v6.0.25 shift analytics router binding failed closed")

    module.MGC_SHIFT_ANALYTICS_ROUTER = extracted
    module.MGC_SHIFT_ANALYTICS_ROUTER_BINDING_REPORT = report
    return report


__all__ = [
    "SHIFT_ANALYTICS_ROUTE_CONTRACT",
    "ShiftAnalyticsRouterBindingReport",
    "bind_shift_analytics_router",
]
