from __future__ import annotations

from dataclasses import dataclass
from types import ModuleType

from fastapi import FastAPI
from fastapi.routing import APIRoute
from starlette.routing import Mount

from mgc.routers.practice_games import PRACTICE_GAME_HANDLER_NAMES, build_practice_games_router


PRACTICE_GAME_ROUTE_CONTRACT = {
    ("POST", "/api/practice/result"),
    ("POST", "/api/games/{game_type}/start"),
    ("POST", "/api/games/{session_id}/finish"),
    ("POST", "/api/learning/question-attempt"),
}


@dataclass(frozen=True)
class PracticeGamesRouterBindingReport:
    ok: bool
    route_count: int
    practice_route_count: int
    game_route_count: int
    question_attempt_route_count: int
    route_names_preserved: bool
    response_classes_preserved: bool
    root_mount_order_preserved: bool
    router_module_owned: bool
    auth_core_bound: bool
    workflow_service_bound: bool
    learning_service_captured: bool
    terminology_service_captured: bool


def _key(route: APIRoute) -> tuple[str, str]:
    methods = sorted((route.methods or set()) - {"HEAD", "OPTIONS"})
    if len(methods) != 1:
        raise RuntimeError(f"practice/game route must have one explicit method: {route.path} {methods}")
    return methods[0], route.path


def _single_route_index(application: FastAPI, key: tuple[str, str]) -> int:
    matches = [
        index
        for index, route in enumerate(application.router.routes)
        if isinstance(route, APIRoute) and _key(route) == key
    ]
    if len(matches) != 1:
        raise RuntimeError(
            f"practice/game route contract drifted for {key[0]} {key[1]}: {len(matches)} matches"
        )
    return matches[0]


def bind_practice_games_router(
    module: ModuleType,
    application: FastAPI,
) -> PracticeGamesRouterBindingReport:
    """Replace four workflow-bound APIRoutes with a dedicated practice/game router."""
    existing = getattr(module, "MGC_PRACTICE_GAMES_ROUTER_BINDING_REPORT", None)
    if isinstance(existing, PracticeGamesRouterBindingReport) and existing.ok:
        return existing

    if getattr(module.current_user, "__module__", "") != "mgc.auth_core":
        raise RuntimeError("practice/game router must bind after extracted current_user")
    auth_core_bound = True

    workflow_report = getattr(module, "MGC_WORKFLOW_BINDING_REPORT", None)
    workflow_bindings = getattr(module, "MGC_PRACTICE_GAME_WORKFLOW_BINDINGS", None)
    if not workflow_report or not getattr(workflow_report, "ok", False) or workflow_bindings is None:
        raise RuntimeError("practice/game router must bind after v5.7.9 workflow extraction")

    handlers = {
        name: getattr(workflow_bindings, name, None)
        for name in PRACTICE_GAME_HANDLER_NAMES
    }
    workflow_service_bound = all(
        callable(handler) and getattr(handler, "__module__", "") == "mgc.services.practice_games"
        for handler in handlers.values()
    )
    if not workflow_service_bound:
        raise RuntimeError("practice/game router handlers are not owned by extracted workflow service")

    learning_service_captured = bool(getattr(workflow_report, "learning_service_captured", False))
    terminology_service_captured = bool(getattr(workflow_report, "terminology_service_captured", False))
    if not learning_service_captured or not terminology_service_captured:
        raise RuntimeError("practice/game workflow service dependencies drifted")

    extracted = build_practice_games_router(
        db_session=module.db_session,
        current_user=module.current_user,
        handlers=handlers,
    )
    new_routes = {_key(route): route for route in extracted.routes if isinstance(route, APIRoute)}
    if set(new_routes) != PRACTICE_GAME_ROUTE_CONTRACT:
        raise RuntimeError(
            "extracted practice/game router contract drifted: "
            + str(sorted(set(new_routes) ^ PRACTICE_GAME_ROUTE_CONTRACT))
        )

    originals: dict[tuple[str, str], APIRoute] = {}
    replaced: dict[tuple[str, str], APIRoute] = {}
    indexes: list[int] = []
    route_names_preserved = True
    response_classes_preserved = True

    for key in sorted(PRACTICE_GAME_ROUTE_CONTRACT):
        index = _single_route_index(application, key)
        indexes.append(index)
        old_route = application.router.routes[index]
        assert isinstance(old_route, APIRoute)
        new_route = new_routes[key]
        route_names_preserved = route_names_preserved and old_route.name == new_route.name
        response_classes_preserved = (
            response_classes_preserved and old_route.response_class == new_route.response_class
        )
        originals[key] = old_route
        application.router.routes[index] = new_route
        replaced[key] = new_route
        setattr(module, old_route.name, new_route.endpoint)

    module.MGC_LEGACY_PRACTICE_GAME_ROUTES = originals
    module.MGC_PRACTICE_GAMES_ROUTER = extracted

    mount_indices = [
        index
        for index, route in enumerate(application.router.routes)
        if isinstance(route, Mount) and getattr(route, "name", None) == "static"
    ]
    root_mount_order_preserved = bool(mount_indices) and all(
        index < mount_indices[0] for index in indexes
    )
    router_module_owned = all(
        route.endpoint.__module__ == "mgc.routers.practice_games" for route in replaced.values()
    )

    practice_count = sum(1 for key in replaced if key[1] == "/api/practice/result")
    game_count = sum(1 for key in replaced if key[1].startswith("/api/games/"))
    question_count = sum(
        1 for key in replaced if key[1] == "/api/learning/question-attempt"
    )

    report = PracticeGamesRouterBindingReport(
        ok=(
            len(replaced) == 4
            and practice_count == 1
            and game_count == 2
            and question_count == 1
            and route_names_preserved
            and response_classes_preserved
            and root_mount_order_preserved
            and router_module_owned
            and auth_core_bound
            and workflow_service_bound
            and learning_service_captured
            and terminology_service_captured
        ),
        route_count=len(replaced),
        practice_route_count=practice_count,
        game_route_count=game_count,
        question_attempt_route_count=question_count,
        route_names_preserved=route_names_preserved,
        response_classes_preserved=response_classes_preserved,
        root_mount_order_preserved=root_mount_order_preserved,
        router_module_owned=router_module_owned,
        auth_core_bound=auth_core_bound,
        workflow_service_bound=workflow_service_bound,
        learning_service_captured=learning_service_captured,
        terminology_service_captured=terminology_service_captured,
    )
    if not report.ok:
        raise RuntimeError("v5.8.4 practice/game router binding failed closed")
    module.MGC_PRACTICE_GAMES_ROUTER_BINDING_REPORT = report
    return report


__all__ = [
    "PRACTICE_GAME_ROUTE_CONTRACT",
    "PracticeGamesRouterBindingReport",
    "bind_practice_games_router",
]
