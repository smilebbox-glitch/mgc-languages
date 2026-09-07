from __future__ import annotations

from dataclasses import dataclass
from types import ModuleType
from typing import Any

from fastapi import FastAPI
from fastapi.routing import APIRoute
from starlette.routing import Mount

from mgc.routers.learning import LEARNING_HANDLER_NAMES, build_learning_router


LEARNING_ROUTE_CONTRACT = {
    ("GET", "/api/language/{language}/progress"),
    ("POST", "/api/language/{language}/progress"),
    ("GET", "/api/language/{language}/course30"),
    ("POST", "/api/course-day/result"),
    ("GET", "/api/review/queue"),
    ("POST", "/api/review/result"),
    ("GET", "/api/gamification/me"),
    ("GET", "/api/gamification/levels"),
    ("GET", "/api/gamification/rewards"),
    ("POST", "/api/gamification/spend"),
    ("GET", "/api/learning/preferences"),
    ("PUT", "/api/learning/preferences"),
}


@dataclass(frozen=True)
class LearningRouterBindingReport:
    ok: bool
    learning_route_count: int
    progress_route_count: int
    course_route_count: int
    review_route_count: int
    gamification_route_count: int
    preferences_route_count: int
    route_names_preserved: bool
    response_classes_preserved: bool
    root_mount_order_preserved: bool
    router_module_owned: bool
    auth_core_bound: bool
    learning_core_bound: bool
    terminology_service_bound: bool


def _key(route: APIRoute) -> tuple[str, str]:
    methods = sorted((route.methods or set()) - {"HEAD", "OPTIONS"})
    if len(methods) != 1:
        raise RuntimeError(f"learning route must have one explicit method: {route.path} {methods}")
    return methods[0], route.path


def _single_route_index(application: FastAPI, key: tuple[str, str]) -> int:
    matches = [
        index
        for index, route in enumerate(application.router.routes)
        if isinstance(route, APIRoute) and _key(route) == key
    ]
    if len(matches) != 1:
        raise RuntimeError(
            f"learning route contract drifted for {key[0]} {key[1]}: {len(matches)} matches"
        )
    return matches[0]


def _service_contracts(module: ModuleType) -> tuple[bool, bool, bool]:
    auth_core_bound = getattr(module.current_user, "__module__", "") == "mgc.auth_core"

    learning = getattr(module, "MGC_LEARNING_SERVICE_BINDINGS", None)
    learning_core_bound = bool(learning) and all(
        (
            module.gamification_view is learning.gamification_view,
            module.level_info is learning.level_info,
            module.spend_xp is learning.spend_xp,
            module.get_or_create_srs_card is learning.get_or_create_srs_card,
            module.schedule_srs is learning.schedule_srs,
        )
    )

    terminology = getattr(module, "MGC_TERMINOLOGY_SERVICE_BINDINGS", None)
    terminology_service_bound = bool(terminology) and all(
        (
            module.terms_for is terminology.terms_for,
            module.term_by_id is terminology.term_by_id,
        )
    )
    return auth_core_bound, learning_core_bound, terminology_service_bound


def bind_learning_router(module: ModuleType, application: FastAPI) -> LearningRouterBindingReport:
    """Replace twelve legacy learning APIRoutes in-place with mgc.routers.learning."""
    existing = getattr(module, "MGC_LEARNING_ROUTER_BINDING_REPORT", None)
    if isinstance(existing, LearningRouterBindingReport) and existing.ok:
        return existing

    required = (
        "db_session",
        "current_user",
        "gamification_view",
        "level_info",
        "spend_xp",
        "get_or_create_srs_card",
        "schedule_srs",
        "terms_for",
        "term_by_id",
        *LEARNING_HANDLER_NAMES,
    )
    missing = [name for name in required if not hasattr(module, name)]
    if missing:
        raise RuntimeError(f"legacy learning router dependencies are incomplete: {missing}")

    auth_core_bound, learning_core_bound, terminology_service_bound = _service_contracts(module)
    if not auth_core_bound:
        raise RuntimeError("learning router must bind after extracted current_user")
    if not learning_core_bound:
        raise RuntimeError("learning router must bind after extracted XP/SRS service")
    if not terminology_service_bound:
        raise RuntimeError("learning router must bind after extracted terminology service")

    handlers = {name: getattr(module, name) for name in LEARNING_HANDLER_NAMES}
    extracted = build_learning_router(
        db_session=module.db_session,
        current_user=module.current_user,
        handlers=handlers,
    )
    new_routes = {_key(route): route for route in extracted.routes if isinstance(route, APIRoute)}
    if set(new_routes) != LEARNING_ROUTE_CONTRACT:
        raise RuntimeError(
            "extracted learning router contract drifted: "
            + str(sorted(set(new_routes) ^ LEARNING_ROUTE_CONTRACT))
        )

    originals: dict[tuple[str, str], APIRoute] = {}
    replaced: dict[tuple[str, str], APIRoute] = {}
    indexes: list[int] = []
    route_names_preserved = True
    response_classes_preserved = True

    for key in sorted(LEARNING_ROUTE_CONTRACT):
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

    module.MGC_LEGACY_LEARNING_ROUTES = originals
    module.MGC_LEARNING_ROUTER = extracted

    mount_indices = [
        index
        for index, route in enumerate(application.router.routes)
        if isinstance(route, Mount) and getattr(route, "name", None) == "static"
    ]
    root_mount_order_preserved = bool(mount_indices) and all(
        index < mount_indices[0] for index in indexes
    )
    router_module_owned = all(
        route.endpoint.__module__ == "mgc.routers.learning" for route in replaced.values()
    )

    progress_count = sum(1 for key in replaced if key[1].endswith("/progress"))
    course_count = sum(
        1 for key in replaced if key[1] in {"/api/language/{language}/course30", "/api/course-day/result"}
    )
    review_count = sum(1 for key in replaced if key[1].startswith("/api/review/"))
    gamification_count = sum(1 for key in replaced if key[1].startswith("/api/gamification/"))
    preferences_count = sum(1 for key in replaced if key[1] == "/api/learning/preferences")

    report = LearningRouterBindingReport(
        ok=(
            len(replaced) == len(LEARNING_ROUTE_CONTRACT)
            and progress_count == 2
            and course_count == 2
            and review_count == 2
            and gamification_count == 4
            and preferences_count == 2
            and route_names_preserved
            and response_classes_preserved
            and root_mount_order_preserved
            and router_module_owned
            and auth_core_bound
            and learning_core_bound
            and terminology_service_bound
        ),
        learning_route_count=len(replaced),
        progress_route_count=progress_count,
        course_route_count=course_count,
        review_route_count=review_count,
        gamification_route_count=gamification_count,
        preferences_route_count=preferences_count,
        route_names_preserved=route_names_preserved,
        response_classes_preserved=response_classes_preserved,
        root_mount_order_preserved=root_mount_order_preserved,
        router_module_owned=router_module_owned,
        auth_core_bound=auth_core_bound,
        learning_core_bound=learning_core_bound,
        terminology_service_bound=terminology_service_bound,
    )
    if not report.ok:
        raise RuntimeError("v5.8.3 learning router binding failed closed")
    module.MGC_LEARNING_ROUTER_BINDING_REPORT = report
    return report


__all__ = [
    "LEARNING_ROUTE_CONTRACT",
    "LearningRouterBindingReport",
    "bind_learning_router",
]
