from __future__ import annotations

import inspect
from dataclasses import dataclass
from types import ModuleType

from fastapi import FastAPI
from fastapi.routing import APIRoute
from starlette.routing import Mount

from mgc.routers.auth import build_auth_router


AUTH_ROUTE_CONTRACT = {
    ("POST", "/api/register"),
    ("POST", "/api/login"),
    ("POST", "/api/logout"),
    ("GET", "/api/auth/oidc/login"),
    ("GET", "/api/auth/oidc/callback"),
    ("GET", "/api/me"),
}


@dataclass(frozen=True)
class AuthRouterBindingReport:
    ok: bool
    auth_route_count: int
    local_route_count: int
    oidc_route_count: int
    route_names_preserved: bool
    root_mount_order_preserved: bool
    router_module_owned: bool
    current_user_dependency_is_extracted: bool
    session_factory_is_extracted: bool


def _key(route: APIRoute) -> tuple[str, str]:
    methods = sorted((route.methods or set()) - {"HEAD", "OPTIONS"})
    if len(methods) != 1:
        raise RuntimeError(f"auth route must have one explicit method: {route.path} {methods}")
    return methods[0], route.path


def _single_route_index(application: FastAPI, key: tuple[str, str]) -> int:
    matches = [
        index
        for index, route in enumerate(application.router.routes)
        if isinstance(route, APIRoute) and _key(route) == key
    ]
    if len(matches) != 1:
        raise RuntimeError(f"auth route contract drifted for {key[0]} {key[1]}: {len(matches)} matches")
    return matches[0]


def bind_auth_router(module: ModuleType, application: FastAPI) -> AuthRouterBindingReport:
    """Replace legacy authentication APIRoutes in-place after auth-core rebinding."""
    existing = getattr(module, "MGC_AUTH_ROUTER_BINDING_REPORT", None)
    if isinstance(existing, AuthRouterBindingReport) and existing.ok:
        return existing

    required = (
        "AUTH_MODE",
        "REGISTRATION_ENABLED",
        "User",
        "LoginSession",
        "db_session",
        "current_user",
        "make_password_hash",
        "verify_password",
        "token_digest",
        "rate_limit",
        "audit_event",
        "create_login_session",
        "user_view",
        "_oidc_role",
        "OIDC_DISCOVERY_URL",
        "OIDC_CLIENT_ID",
        "OIDC_CLIENT_SECRET",
        "OIDC_SCOPE",
        "OIDC_USERNAME_CLAIM",
        "OIDC_DISPLAY_NAME_CLAIM",
        "OIDC_GROUPS_CLAIM",
        "OIDC_DEPARTMENT_CLAIM",
    )
    missing = [name for name in required if not hasattr(module, name)]
    if missing:
        raise RuntimeError(f"legacy auth router dependencies are incomplete: {missing}")

    if getattr(module.current_user, "__module__", "") != "mgc.auth_core":
        raise RuntimeError("auth router must bind after extracted current_user")
    if getattr(module.create_login_session, "__module__", "") != "mgc.auth_core":
        raise RuntimeError("auth router must bind after extracted session factory")

    extracted = build_auth_router(
        auth_mode=str(module.AUTH_MODE),
        registration_enabled=bool(module.REGISTRATION_ENABLED),
        user_model=module.User,
        login_session_model=module.LoginSession,
        db_session=module.db_session,
        current_user=module.current_user,
        make_password_hash=module.make_password_hash,
        verify_password=module.verify_password,
        token_digest=module.token_digest,
        rate_limit=module.rate_limit,
        audit_event=module.audit_event,
        create_login_session=module.create_login_session,
        user_view=module.user_view,
        oidc_role=module._oidc_role,
        oidc_discovery_url=str(module.OIDC_DISCOVERY_URL),
        oidc_client_id=str(module.OIDC_CLIENT_ID),
        oidc_client_secret=str(module.OIDC_CLIENT_SECRET),
        oidc_scope=str(module.OIDC_SCOPE),
        oidc_username_claim=str(module.OIDC_USERNAME_CLAIM),
        oidc_display_name_claim=str(module.OIDC_DISPLAY_NAME_CLAIM),
        oidc_groups_claim=str(module.OIDC_GROUPS_CLAIM),
        oidc_department_claim=str(module.OIDC_DEPARTMENT_CLAIM),
    )
    new_routes = {_key(route): route for route in extracted.routes if isinstance(route, APIRoute)}
    if set(new_routes) != AUTH_ROUTE_CONTRACT:
        raise RuntimeError(
            "extracted auth router contract drifted: "
            + str(sorted(set(new_routes) ^ AUTH_ROUTE_CONTRACT))
        )

    originals: dict[tuple[str, str], APIRoute] = {}
    replaced: dict[tuple[str, str], APIRoute] = {}
    route_names_preserved = True
    indexes: list[int] = []
    for key in sorted(AUTH_ROUTE_CONTRACT):
        index = _single_route_index(application, key)
        indexes.append(index)
        old_route = application.router.routes[index]
        assert isinstance(old_route, APIRoute)
        new_route = new_routes[key]
        route_names_preserved = route_names_preserved and old_route.name == new_route.name
        originals[key] = old_route
        application.router.routes[index] = new_route
        replaced[key] = new_route

    module.register = replaced[("POST", "/api/register")].endpoint
    module.login = replaced[("POST", "/api/login")].endpoint
    module.logout = replaced[("POST", "/api/logout")].endpoint
    module.oidc_login = replaced[("GET", "/api/auth/oidc/login")].endpoint
    module.oidc_callback = replaced[("GET", "/api/auth/oidc/callback")].endpoint
    module.me = replaced[("GET", "/api/me")].endpoint
    module.MGC_LEGACY_AUTH_ROUTES = originals
    module.MGC_AUTH_ROUTER = extracted

    mount_indices = [
        index
        for index, route in enumerate(application.router.routes)
        if isinstance(route, Mount) and getattr(route, "name", None) == "static"
    ]
    root_mount_order_preserved = bool(mount_indices) and all(index < mount_indices[0] for index in indexes)
    router_module_owned = all(
        route.endpoint.__module__ == "mgc.routers.auth" for route in replaced.values()
    )

    me_route = replaced[("GET", "/api/me")]
    current_user_dependency_is_extracted = any(
        getattr(dependency, "call", None) is module.current_user
        for dependency in (me_route.dependant.dependencies or [])
    )
    login_closure = inspect.getclosurevars(replaced[("POST", "/api/login")].endpoint)
    session_factory_is_extracted = (
        login_closure.nonlocals.get("create_login_session") is module.create_login_session
        and getattr(module.create_login_session, "__module__", "") == "mgc.auth_core"
    )

    local_count = sum(1 for key in replaced if key[1] in {"/api/register", "/api/login", "/api/logout", "/api/me"})
    oidc_count = sum(1 for key in replaced if key[1].startswith("/api/auth/oidc/"))
    report = AuthRouterBindingReport(
        ok=(
            len(replaced) == len(AUTH_ROUTE_CONTRACT)
            and route_names_preserved
            and root_mount_order_preserved
            and router_module_owned
            and current_user_dependency_is_extracted
            and session_factory_is_extracted
        ),
        auth_route_count=len(replaced),
        local_route_count=local_count,
        oidc_route_count=oidc_count,
        route_names_preserved=route_names_preserved,
        root_mount_order_preserved=root_mount_order_preserved,
        router_module_owned=router_module_owned,
        current_user_dependency_is_extracted=current_user_dependency_is_extracted,
        session_factory_is_extracted=session_factory_is_extracted,
    )
    if not report.ok:
        raise RuntimeError("v5.8.2 auth router binding failed closed")
    module.MGC_AUTH_ROUTER_BINDING_REPORT = report
    return report


__all__ = ["AUTH_ROUTE_CONTRACT", "AuthRouterBindingReport", "bind_auth_router"]
