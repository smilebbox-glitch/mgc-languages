from __future__ import annotations

from dataclasses import dataclass
from types import ModuleType

from fastapi import FastAPI
from fastapi.routing import APIRoute
from starlette.routing import Mount

from mgc.routers.language_content import (
    LANGUAGE_CONTENT_HANDLER_NAMES,
    build_language_content_router,
)


LANGUAGE_CONTENT_ROUTE_CONTRACT = {
    ("GET", "/api/language/{language}/summary"),
    ("GET", "/api/language/{language}/quiz"),
    ("GET", "/api/language/{language}/situations"),
    ("GET", "/api/language/{language}/roleplays"),
    ("GET", "/api/language/{language}/mgc-scenarios"),
}


@dataclass(frozen=True)
class LanguageContentRouterBindingReport:
    ok: bool
    route_count: int
    summary_route_count: int
    quiz_route_count: int
    scenario_route_count: int
    route_names_preserved: bool
    response_classes_preserved: bool
    root_mount_order_preserved: bool
    router_module_owned: bool
    auth_core_bound: bool
    terminology_service_bound: bool


def _key(route: APIRoute) -> tuple[str, str]:
    methods = sorted((route.methods or set()) - {"HEAD", "OPTIONS"})
    if len(methods) != 1:
        raise RuntimeError(f"language content route must have one explicit method: {route.path} {methods}")
    return methods[0], route.path


def _single_route_index(application: FastAPI, key: tuple[str, str]) -> int:
    matches = [
        index
        for index, route in enumerate(application.router.routes)
        if isinstance(route, APIRoute) and _key(route) == key
    ]
    if len(matches) != 1:
        raise RuntimeError(
            f"language content route contract drifted for {key[0]} {key[1]}: {len(matches)} matches"
        )
    return matches[0]


def bind_language_content_router(
    module: ModuleType,
    application: FastAPI,
) -> LanguageContentRouterBindingReport:
    """Replace five language-content APIRoutes with a dedicated router."""
    existing = getattr(module, "MGC_LANGUAGE_CONTENT_ROUTER_BINDING_REPORT", None)
    if isinstance(existing, LanguageContentRouterBindingReport) and existing.ok:
        return existing

    required = (
        "db_session",
        "current_user",
        "terms_for",
        "validate_language",
        *LANGUAGE_CONTENT_HANDLER_NAMES,
    )
    missing = [name for name in required if not hasattr(module, name)]
    if missing:
        raise RuntimeError(f"legacy language content dependencies are incomplete: {missing}")

    auth_core_bound = getattr(module.current_user, "__module__", "") == "mgc.auth_core"
    if not auth_core_bound:
        raise RuntimeError("language content router must bind after extracted auth core")

    terminology = getattr(module, "MGC_TERMINOLOGY_SERVICE_BINDINGS", None)
    terminology_service_bound = bool(terminology) and module.terms_for is terminology.terms_for
    if not terminology_service_bound:
        raise RuntimeError("language content router must bind after extracted terminology service")

    handlers = {name: getattr(module, name) for name in LANGUAGE_CONTENT_HANDLER_NAMES}
    extracted = build_language_content_router(
        db_session=module.db_session,
        current_user=module.current_user,
        handlers=handlers,
    )
    new_routes = {_key(route): route for route in extracted.routes if isinstance(route, APIRoute)}
    if set(new_routes) != LANGUAGE_CONTENT_ROUTE_CONTRACT:
        raise RuntimeError(
            "extracted language content router contract drifted: "
            + str(sorted(set(new_routes) ^ LANGUAGE_CONTENT_ROUTE_CONTRACT))
        )

    originals: dict[tuple[str, str], APIRoute] = {}
    replaced: dict[tuple[str, str], APIRoute] = {}
    indexes: list[int] = []
    route_names_preserved = True
    response_classes_preserved = True

    for key in sorted(LANGUAGE_CONTENT_ROUTE_CONTRACT):
        index = _single_route_index(application, key)
        indexes.append(index)
        old_route = application.router.routes[index]
        assert isinstance(old_route, APIRoute)
        new_route = new_routes[key]
        route_names_preserved = route_names_preserved and old_route.name == new_route.name
        response_classes_preserved = response_classes_preserved and old_route.response_class == new_route.response_class
        originals[key] = old_route
        application.router.routes[index] = new_route
        replaced[key] = new_route
        setattr(module, old_route.name, new_route.endpoint)

    module.MGC_LEGACY_LANGUAGE_CONTENT_ROUTES = originals
    module.MGC_LANGUAGE_CONTENT_ROUTER = extracted

    mount_indices = [
        index
        for index, route in enumerate(application.router.routes)
        if isinstance(route, Mount) and getattr(route, "name", None) == "static"
    ]
    root_mount_order_preserved = bool(mount_indices) and all(index < mount_indices[0] for index in indexes)
    router_module_owned = all(
        route.endpoint.__module__ == "mgc.routers.language_content" for route in replaced.values()
    )

    summary_count = sum(1 for key in replaced if key[1].endswith("/summary"))
    quiz_count = sum(1 for key in replaced if key[1].endswith("/quiz"))
    scenario_count = len(replaced) - summary_count - quiz_count

    report = LanguageContentRouterBindingReport(
        ok=(
            len(replaced) == 5
            and summary_count == 1
            and quiz_count == 1
            and scenario_count == 3
            and route_names_preserved
            and response_classes_preserved
            and root_mount_order_preserved
            and router_module_owned
            and auth_core_bound
            and terminology_service_bound
        ),
        route_count=len(replaced),
        summary_route_count=summary_count,
        quiz_route_count=quiz_count,
        scenario_route_count=scenario_count,
        route_names_preserved=route_names_preserved,
        response_classes_preserved=response_classes_preserved,
        root_mount_order_preserved=root_mount_order_preserved,
        router_module_owned=router_module_owned,
        auth_core_bound=auth_core_bound,
        terminology_service_bound=terminology_service_bound,
    )
    if not report.ok:
        raise RuntimeError("v5.9.2 language content router binding failed closed")
    module.MGC_LANGUAGE_CONTENT_ROUTER_BINDING_REPORT = report
    return report


__all__ = [
    "LANGUAGE_CONTENT_ROUTE_CONTRACT",
    "LanguageContentRouterBindingReport",
    "bind_language_content_router",
]
