from __future__ import annotations

from dataclasses import dataclass
from types import ModuleType
from typing import Any

from fastapi import FastAPI
from fastapi.routing import APIRoute
from starlette.routing import Mount

from mgc.routers.terminology_admin import (
    TERMINOLOGY_ADMIN_HANDLER_NAMES,
    build_terminology_admin_router,
)


TERMINOLOGY_ADMIN_ROUTE_CONTRACT = {
    ("GET", "/api/language/{language}/topics"),
    ("GET", "/api/language/{language}/terms"),
    ("GET", "/api/admin/terms"),
    ("POST", "/api/admin/terms"),
    ("PATCH", "/api/admin/terms/{term_id}"),
    ("DELETE", "/api/admin/terms/{term_id}"),
    ("GET", "/api/admin/terms/{term_id}/revisions"),
    ("POST", "/api/admin/terms/{term_id}/submit-review"),
    ("POST", "/api/admin/terms/{term_id}/approve"),
    ("POST", "/api/admin/terms/{term_id}/reject"),
    ("POST", "/api/admin/terms/{term_id}/rollback/{revision_no}"),
    ("POST", "/api/admin/terms/import"),
    ("GET", "/api/admin/taxonomy"),
}


@dataclass(frozen=True)
class TerminologyAdminRouterBindingReport:
    ok: bool
    route_count: int
    public_route_count: int
    admin_term_route_count: int
    taxonomy_route_count: int
    route_names_preserved: bool
    response_classes_preserved: bool
    root_mount_order_preserved: bool
    router_module_owned: bool
    auth_core_bound: bool
    terminology_service_bound: bool
    governance_core_bound: bool


def _key(route: APIRoute) -> tuple[str, str]:
    methods = sorted((route.methods or set()) - {"HEAD", "OPTIONS"})
    if len(methods) != 1:
        raise RuntimeError(f"terminology/admin route must have one explicit method: {route.path} {methods}")
    return methods[0], route.path


def _single_route_index(application: FastAPI, key: tuple[str, str]) -> int:
    matches = [
        index
        for index, route in enumerate(application.router.routes)
        if isinstance(route, APIRoute) and _key(route) == key
    ]
    if len(matches) != 1:
        raise RuntimeError(
            f"terminology/admin route contract drifted for {key[0]} {key[1]}: {len(matches)} matches"
        )
    return matches[0]


def _service_contracts(module: ModuleType) -> tuple[bool, bool, bool]:
    auth_core_bound = all(
        getattr(getattr(module, name, None), "__module__", "") == "mgc.auth_core"
        for name in ("current_user", "require_roles")
    )

    terminology = getattr(module, "MGC_TERMINOLOGY_SERVICE_BINDINGS", None)
    terminology_service_bound = bool(terminology) and all(
        (
            module.custom_term_view is terminology.custom_term_view,
            module.terms_for is terminology.terms_for,
            module.term_by_id is terminology.term_by_id,
            module.record_term_revision is terminology.record_term_revision,
            module.admin_term_response is terminology.admin_term_response,
        )
    )

    governance = getattr(module, "MGC_GOVERNANCE_BINDINGS", None)
    governance_core_bound = bool(governance) and module.audit_event is governance.audit_event
    return auth_core_bound, terminology_service_bound, governance_core_bound


def bind_terminology_admin_router(
    module: ModuleType,
    application: FastAPI,
) -> TerminologyAdminRouterBindingReport:
    """Replace thirteen terminology/admin APIRoutes in-place with a modular router."""
    existing = getattr(module, "MGC_TERMINOLOGY_ADMIN_ROUTER_BINDING_REPORT", None)
    if isinstance(existing, TerminologyAdminRouterBindingReport) and existing.ok:
        return existing

    required = (
        "db_session",
        "current_user",
        "require_roles",
        "custom_term_view",
        "terms_for",
        "term_by_id",
        "record_term_revision",
        "admin_term_response",
        "audit_event",
        *TERMINOLOGY_ADMIN_HANDLER_NAMES,
    )
    missing = [name for name in required if not hasattr(module, name)]
    if missing:
        raise RuntimeError(f"legacy terminology/admin router dependencies are incomplete: {missing}")

    auth_core_bound, terminology_service_bound, governance_core_bound = _service_contracts(module)
    if not auth_core_bound:
        raise RuntimeError("terminology/admin router must bind after extracted auth core")
    if not terminology_service_bound:
        raise RuntimeError("terminology/admin router must bind after extracted terminology service")
    if not governance_core_bound:
        raise RuntimeError("terminology/admin router must bind after extracted governance core")

    handlers = {name: getattr(module, name) for name in TERMINOLOGY_ADMIN_HANDLER_NAMES}
    extracted = build_terminology_admin_router(
        db_session=module.db_session,
        current_user=module.current_user,
        require_roles=module.require_roles,
        handlers=handlers,
    )
    new_routes = {_key(route): route for route in extracted.routes if isinstance(route, APIRoute)}
    if set(new_routes) != TERMINOLOGY_ADMIN_ROUTE_CONTRACT:
        raise RuntimeError(
            "extracted terminology/admin router contract drifted: "
            + str(sorted(set(new_routes) ^ TERMINOLOGY_ADMIN_ROUTE_CONTRACT))
        )

    originals: dict[tuple[str, str], APIRoute] = {}
    replaced: dict[tuple[str, str], APIRoute] = {}
    indexes: list[int] = []
    route_names_preserved = True
    response_classes_preserved = True

    for key in sorted(TERMINOLOGY_ADMIN_ROUTE_CONTRACT):
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

    module.MGC_LEGACY_TERMINOLOGY_ADMIN_ROUTES = originals
    module.MGC_TERMINOLOGY_ADMIN_ROUTER = extracted

    mount_indices = [
        index
        for index, route in enumerate(application.router.routes)
        if isinstance(route, Mount) and getattr(route, "name", None) == "static"
    ]
    root_mount_order_preserved = bool(mount_indices) and all(
        index < mount_indices[0] for index in indexes
    )
    router_module_owned = all(
        route.endpoint.__module__ == "mgc.routers.terminology_admin"
        for route in replaced.values()
    )

    public_count = sum(1 for key in replaced if key[1].startswith("/api/language/"))
    admin_term_count = sum(1 for key in replaced if key[1].startswith("/api/admin/terms"))
    taxonomy_count = sum(1 for key in replaced if key[1] == "/api/admin/taxonomy")

    report = TerminologyAdminRouterBindingReport(
        ok=(
            len(replaced) == 13
            and public_count == 2
            and admin_term_count == 10
            and taxonomy_count == 1
            and route_names_preserved
            and response_classes_preserved
            and root_mount_order_preserved
            and router_module_owned
            and auth_core_bound
            and terminology_service_bound
            and governance_core_bound
        ),
        route_count=len(replaced),
        public_route_count=public_count,
        admin_term_route_count=admin_term_count,
        taxonomy_route_count=taxonomy_count,
        route_names_preserved=route_names_preserved,
        response_classes_preserved=response_classes_preserved,
        root_mount_order_preserved=root_mount_order_preserved,
        router_module_owned=router_module_owned,
        auth_core_bound=auth_core_bound,
        terminology_service_bound=terminology_service_bound,
        governance_core_bound=governance_core_bound,
    )
    if not report.ok:
        raise RuntimeError("v5.8.5 terminology/admin router binding failed closed")
    module.MGC_TERMINOLOGY_ADMIN_ROUTER_BINDING_REPORT = report
    return report


__all__ = [
    "TERMINOLOGY_ADMIN_ROUTE_CONTRACT",
    "TerminologyAdminRouterBindingReport",
    "bind_terminology_admin_router",
]
