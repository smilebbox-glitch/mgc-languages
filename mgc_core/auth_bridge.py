from __future__ import annotations

import inspect
from dataclasses import dataclass
from types import ModuleType
from typing import Any, Iterator

from fastapi import FastAPI

from mgc.auth_core import AuthCoreBindings, build_auth_core


@dataclass(frozen=True)
class AuthBindingReport:
    ok: bool
    current_user_dependency_occurrences: int
    role_dependency_occurrences: int
    role_dependency_overrides: int
    role_sets: tuple[tuple[str, ...], ...]
    session_factory_bound: bool


def _walk_dependants(application: FastAPI) -> Iterator[Any]:
    seen: set[int] = set()

    def visit(node: Any) -> Iterator[Any]:
        if node is None or id(node) in seen:
            return
        seen.add(id(node))
        yield node
        for child in getattr(node, "dependencies", ()) or ():
            yield from visit(child)

    for route in application.routes:
        dependant = getattr(route, "dependant", None)
        if dependant is not None:
            yield from visit(dependant)


def _install_override(application: FastAPI, original: Any, replacement: Any) -> None:
    existing = application.dependency_overrides.get(original)
    if existing is not None and existing is not replacement:
        raise RuntimeError(
            f"dependency override conflict for {getattr(original, '__qualname__', repr(original))}"
        )
    application.dependency_overrides[original] = replacement


def bind_legacy_auth(module: ModuleType, application: FastAPI) -> AuthBindingReport:
    """Move production FastAPI auth/session execution onto mgc.auth_core.

    FastAPI captures Depends callables while routes are declared. Therefore a
    simple module-global replacement is insufficient for current_user and
    require_roles. We use FastAPI's supported dependency_overrides mechanism to
    rebind already-registered dependencies while preserving every route object,
    cookie contract and ORM model during the modular migration.
    """
    existing_report = getattr(module, "MGC_AUTH_BINDING_REPORT", None)
    if isinstance(existing_report, AuthBindingReport) and existing_report.ok:
        return existing_report

    legacy_current_user = getattr(module, "current_user", None)
    legacy_require_roles = getattr(module, "require_roles", None)
    legacy_create_login_session = getattr(module, "create_login_session", None)
    if not all(callable(x) for x in (legacy_current_user, legacy_require_roles, legacy_create_login_session)):
        raise RuntimeError("legacy auth/session functions are incomplete")

    bindings: AuthCoreBindings = build_auth_core(
        user_model=getattr(module, "User"),
        login_session_model=getattr(module, "LoginSession"),
        db_dependency=getattr(module, "db_session"),
        apply_rls_context=getattr(module, "apply_rls_context"),
        user_view=getattr(module, "user_view"),
        session_ttl_hours=int(getattr(module, "SESSION_TTL_HOURS")),
        cookie_samesite=str(getattr(module, "COOKIE_SAMESITE")),
        cookie_secure=bool(getattr(module, "COOKIE_SECURE")),
    )

    probe = legacy_require_roles("__mgc_auth_probe__")
    legacy_role_code = getattr(probe, "__code__", None)
    current_occurrences = 0
    role_occurrences = 0
    role_calls: dict[int, tuple[Any, tuple[str, ...]]] = {}

    for dependant in _walk_dependants(application):
        call = getattr(dependant, "call", None)
        if call is legacy_current_user:
            current_occurrences += 1
            continue
        if legacy_role_code is not None and getattr(call, "__code__", None) is legacy_role_code:
            closure = inspect.getclosurevars(call)
            roles_raw = closure.nonlocals.get("roles", ())
            roles = tuple(str(role) for role in roles_raw)
            if not roles:
                raise RuntimeError("legacy role dependency lost its role tuple")
            role_occurrences += 1
            role_calls[id(call)] = (call, roles)

    if current_occurrences < 1:
        raise RuntimeError("no current_user dependencies found for auth rebinding")
    if role_occurrences < 1:
        raise RuntimeError("no require_roles dependencies found for auth rebinding")

    _install_override(application, legacy_current_user, bindings.current_user)
    role_sets: set[tuple[str, ...]] = set()
    for original, roles in role_calls.values():
        _install_override(application, original, bindings.require_roles(*roles))
        role_sets.add(roles)

    module.current_user = bindings.current_user
    module.require_roles = bindings.require_roles
    module.create_login_session = bindings.create_login_session

    report = AuthBindingReport(
        ok=True,
        current_user_dependency_occurrences=current_occurrences,
        role_dependency_occurrences=role_occurrences,
        role_dependency_overrides=len(role_calls),
        role_sets=tuple(sorted(role_sets)),
        session_factory_bound=module.create_login_session is bindings.create_login_session,
    )
    module.MGC_AUTH_BINDING_REPORT = report
    return report


__all__ = ["AuthBindingReport", "bind_legacy_auth"]
