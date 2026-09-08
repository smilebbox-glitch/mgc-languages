from __future__ import annotations

from dataclasses import dataclass
from types import ModuleType

from fastapi import FastAPI
from fastapi.routing import APIRoute
from starlette.routing import Mount

from mgc.routers.team_analytics import build_team_analytics_router


TEAM_ANALYTICS_ROUTE_CONTRACT = {
    ("GET", "/api/manager/shift-analytics"),
    ("GET", "/api/leaderboards/games/{game_type}"),
    ("GET", "/api/leaderboards/shifts"),
}


@dataclass(frozen=True)
class TeamAnalyticsRouterBindingReport:
    ok: bool
    route_count: int
    root_mount_order_preserved: bool
    router_module_owned: bool
    auth_core_bound: bool
    models_bound: bool


def _key(route: APIRoute) -> tuple[str, str]:
    methods = sorted((route.methods or set()) - {"HEAD", "OPTIONS"})
    if len(methods) != 1:
        raise RuntimeError(f"team analytics route must have one explicit method: {route.path} {methods}")
    return methods[0], route.path


def bind_team_analytics_router(module: ModuleType, application: FastAPI) -> TeamAnalyticsRouterBindingReport:
    existing = getattr(module, "MGC_TEAM_ANALYTICS_ROUTER_BINDING_REPORT", None)
    if isinstance(existing, TeamAnalyticsRouterBindingReport) and existing.ok:
        return existing

    auth_core_bound = (
        getattr(module.current_user, "__module__", "") == "mgc.auth_core"
        and getattr(module.require_roles, "__module__", "") == "mgc.auth_core"
    )
    if not auth_core_bound:
        raise RuntimeError("team analytics router must bind after extracted auth core")

    user_model = getattr(module, "User", None)
    practice_result_model = getattr(module, "PracticeResult", None)
    game_session_model = getattr(module, "GameSession", None)
    models_bound = all(model is not None for model in (user_model, practice_result_model, game_session_model))
    if not models_bound:
        raise RuntimeError("team analytics router requires User, PracticeResult and GameSession models")

    extracted = build_team_analytics_router(
        db_session=module.db_session,
        current_user=module.current_user,
        require_roles=module.require_roles,
        user_model=user_model,
        practice_result_model=practice_result_model,
        game_session_model=game_session_model,
    )
    routes = [route for route in extracted.routes if isinstance(route, APIRoute)]
    keys = {_key(route) for route in routes}
    if keys != TEAM_ANALYTICS_ROUTE_CONTRACT:
        raise RuntimeError("team analytics route contract drifted: " + str(sorted(keys ^ TEAM_ANALYTICS_ROUTE_CONTRACT)))

    existing_keys = {_key(route) for route in application.router.routes if isinstance(route, APIRoute)}
    duplicates = keys & existing_keys
    if duplicates:
        raise RuntimeError("team analytics routes already exist: " + str(sorted(duplicates)))

    mount_indices = [
        index for index, route in enumerate(application.router.routes)
        if isinstance(route, Mount) and getattr(route, "name", None) == "static"
    ]
    if not mount_indices:
        raise RuntimeError("team analytics router requires the root static mount")
    insert_at = mount_indices[0]
    for route in routes:
        application.router.routes.insert(insert_at, route)
        insert_at += 1

    final_mount = [
        index for index, route in enumerate(application.router.routes)
        if isinstance(route, Mount) and getattr(route, "name", None) == "static"
    ][0]
    bound_indices = [
        index for index, route in enumerate(application.router.routes)
        if isinstance(route, APIRoute) and _key(route) in TEAM_ANALYTICS_ROUTE_CONTRACT
    ]
    root_mount_order_preserved = all(index < final_mount for index in bound_indices)
    router_module_owned = all(route.endpoint.__module__ == "mgc.routers.team_analytics" for route in routes)

    report = TeamAnalyticsRouterBindingReport(
        ok=(len(routes) == 3 and root_mount_order_preserved and router_module_owned and auth_core_bound and models_bound),
        route_count=len(routes),
        root_mount_order_preserved=root_mount_order_preserved,
        router_module_owned=router_module_owned,
        auth_core_bound=auth_core_bound,
        models_bound=models_bound,
    )
    if not report.ok:
        raise RuntimeError("v6.0.26 team analytics router binding failed closed")
    module.MGC_TEAM_ANALYTICS_ROUTER = extracted
    module.MGC_TEAM_ANALYTICS_ROUTER_BINDING_REPORT = report
    return report


__all__ = ["TEAM_ANALYTICS_ROUTE_CONTRACT", "TeamAnalyticsRouterBindingReport", "bind_team_analytics_router"]
