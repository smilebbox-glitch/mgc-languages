from __future__ import annotations

from dataclasses import dataclass
from types import ModuleType

from fastapi import FastAPI
from fastapi.routing import APIRoute
from starlette.routing import Mount

from mgc.routers.users_manager import (
    USERS_MANAGER_HANDLER_NAMES,
    UserDepartmentPayload,
    UserRolePayload,
    build_users_manager_router,
)


USERS_MANAGER_ROUTE_CONTRACT = {
    ("GET", "/api/admin/users"),
    ("GET", "/api/admin/users/{user_id}/learning-stats"),
    ("PATCH", "/api/admin/users/{user_id}/role"),
    ("PATCH", "/api/admin/users/{user_id}/department"),
    ("GET", "/api/manager/team"),
    ("GET", "/api/manager/team/{user_id}/learning-stats"),
}


@dataclass(frozen=True)
class UsersManagerRouterBindingReport:
    ok: bool
    route_count: int
    admin_route_count: int
    manager_route_count: int
    route_names_preserved: bool
    response_classes_preserved: bool
    payload_schemas_preserved: bool
    root_mount_order_preserved: bool
    router_module_owned: bool
    auth_core_bound: bool
    user_service_bound: bool
    terminology_service_bound: bool
    governance_core_bound: bool


def _key(route: APIRoute) -> tuple[str, str]:
    methods = sorted((route.methods or set()) - {"HEAD", "OPTIONS"})
    if len(methods) != 1:
        raise RuntimeError(f"users/manager route must have one explicit method: {route.path} {methods}")
    return methods[0], route.path


def _single_route_index(application: FastAPI, key: tuple[str, str]) -> int:
    matches = [
        index
        for index, route in enumerate(application.router.routes)
        if isinstance(route, APIRoute) and _key(route) == key
    ]
    if len(matches) != 1:
        raise RuntimeError(
            f"users/manager route contract drifted for {key[0]} {key[1]}: {len(matches)} matches"
        )
    return matches[0]


def _service_contracts(module: ModuleType) -> tuple[bool, bool, bool, bool]:
    auth_core_bound = getattr(getattr(module, "require_roles", None), "__module__", "") == "mgc.auth_core"

    users = getattr(module, "MGC_USER_SERVICE_BINDINGS", None)
    user_service_bound = bool(users) and all(
        (
            module.user_view is users.user_view,
            module.user_admin_stats is users.user_admin_stats,
            module._manager_target_allowed is users.manager_target_allowed,
        )
    )

    terminology = getattr(module, "MGC_TERMINOLOGY_SERVICE_BINDINGS", None)
    terminology_service_bound = bool(terminology) and module.terms_for is terminology.terms_for

    governance = getattr(module, "MGC_GOVERNANCE_BINDINGS", None)
    governance_core_bound = bool(governance) and module.audit_event is governance.audit_event
    return auth_core_bound, user_service_bound, terminology_service_bound, governance_core_bound


def bind_users_manager_router(
    module: ModuleType,
    application: FastAPI,
) -> UsersManagerRouterBindingReport:
    """Replace six user/manager APIRoutes with a modular router."""
    existing = getattr(module, "MGC_USERS_MANAGER_ROUTER_BINDING_REPORT", None)
    if isinstance(existing, UsersManagerRouterBindingReport) and existing.ok:
        return existing

    required = (
        "db_session",
        "require_roles",
        "UserDepartmentPayload",
        "UserRolePayload",
        "user_view",
        "user_admin_stats",
        "_manager_target_allowed",
        "terms_for",
        "audit_event",
        *USERS_MANAGER_HANDLER_NAMES,
    )
    missing = [name for name in required if not hasattr(module, name)]
    if missing:
        raise RuntimeError(f"legacy users/manager router dependencies are incomplete: {missing}")

    auth_core_bound, user_service_bound, terminology_service_bound, governance_core_bound = _service_contracts(module)
    if not auth_core_bound:
        raise RuntimeError("users/manager router must bind after extracted auth core")
    if not user_service_bound:
        raise RuntimeError("users/manager router must bind after extracted user service")
    if not terminology_service_bound:
        raise RuntimeError("users/manager router must bind after extracted terminology service")
    if not governance_core_bound:
        raise RuntimeError("users/manager router must bind after extracted governance core")

    legacy_department = getattr(module, "UserDepartmentPayload")
    legacy_role = getattr(module, "UserRolePayload")
    payload_schemas_preserved = (
        callable(getattr(legacy_department, "model_json_schema", None))
        and callable(getattr(legacy_role, "model_json_schema", None))
        and legacy_department.model_json_schema() == UserDepartmentPayload.model_json_schema()
        and legacy_role.model_json_schema() == UserRolePayload.model_json_schema()
    )
    if not payload_schemas_preserved:
        raise RuntimeError("users/manager payload contract drifted")

    handlers = {name: getattr(module, name) for name in USERS_MANAGER_HANDLER_NAMES}
    extracted = build_users_manager_router(
        db_session=module.db_session,
        require_roles=module.require_roles,
        handlers=handlers,
    )
    new_routes = {_key(route): route for route in extracted.routes if isinstance(route, APIRoute)}
    if set(new_routes) != USERS_MANAGER_ROUTE_CONTRACT:
        raise RuntimeError(
            "extracted users/manager router contract drifted: "
            + str(sorted(set(new_routes) ^ USERS_MANAGER_ROUTE_CONTRACT))
        )

    originals: dict[tuple[str, str], APIRoute] = {}
    replaced: dict[tuple[str, str], APIRoute] = {}
    indexes: list[int] = []
    route_names_preserved = True
    response_classes_preserved = True

    for key in sorted(USERS_MANAGER_ROUTE_CONTRACT):
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

    module.MGC_LEGACY_USERS_MANAGER_ROUTES = originals
    module.MGC_USERS_MANAGER_ROUTER = extracted

    mount_indices = [
        index
        for index, route in enumerate(application.router.routes)
        if isinstance(route, Mount) and getattr(route, "name", None) == "static"
    ]
    root_mount_order_preserved = bool(mount_indices) and all(index < mount_indices[0] for index in indexes)
    router_module_owned = all(
        route.endpoint.__module__ == "mgc.routers.users_manager"
        for route in replaced.values()
    )

    admin_count = sum(1 for key in replaced if key[1].startswith("/api/admin/users"))
    manager_count = sum(1 for key in replaced if key[1].startswith("/api/manager/team"))

    report = UsersManagerRouterBindingReport(
        ok=(
            len(replaced) == 6
            and admin_count == 4
            and manager_count == 2
            and route_names_preserved
            and response_classes_preserved
            and payload_schemas_preserved
            and root_mount_order_preserved
            and router_module_owned
            and auth_core_bound
            and user_service_bound
            and terminology_service_bound
            and governance_core_bound
        ),
        route_count=len(replaced),
        admin_route_count=admin_count,
        manager_route_count=manager_count,
        route_names_preserved=route_names_preserved,
        response_classes_preserved=response_classes_preserved,
        payload_schemas_preserved=payload_schemas_preserved,
        root_mount_order_preserved=root_mount_order_preserved,
        router_module_owned=router_module_owned,
        auth_core_bound=auth_core_bound,
        user_service_bound=user_service_bound,
        terminology_service_bound=terminology_service_bound,
        governance_core_bound=governance_core_bound,
    )
    if not report.ok:
        raise RuntimeError("v5.8.7 users/manager router binding failed closed")
    module.MGC_USERS_MANAGER_ROUTER_BINDING_REPORT = report
    return report


__all__ = [
    "USERS_MANAGER_ROUTE_CONTRACT",
    "UsersManagerRouterBindingReport",
    "bind_users_manager_router",
]
