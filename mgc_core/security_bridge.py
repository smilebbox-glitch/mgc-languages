from __future__ import annotations

from dataclasses import dataclass
from types import ModuleType
from typing import Any

from mgc.security import (
    CSRF_EXEMPT_PATHS,
    client_fingerprint,
    make_password_hash,
    manager_target_allowed,
    oidc_role,
    token_digest,
    verify_password,
)


@dataclass(frozen=True)
class SecurityBindingReport:
    ok: bool
    bound_names: tuple[str, ...]
    csrf_policy_preserved: bool


def _request_client_key(request: Any) -> str:
    forwarded = request.headers.get("x-forwarded-for", "").split(",")[0].strip()
    raw = forwarded or (request.client.host if request.client else "unknown")
    return client_fingerprint(raw)


def bind_legacy_security(module: ModuleType) -> SecurityBindingReport:
    """Bind dependency-light security primitives into the legacy module at runtime.

    FastAPI endpoints resolve these module globals when requests execute, so this
    moves production ASGI traffic onto the extracted primitives without changing
    route objects, database models, cookies or public API contracts.
    """
    legacy_csrf = set(getattr(module, "CSRF_EXEMPT", set()))
    expected_csrf = set(CSRF_EXEMPT_PATHS)
    if legacy_csrf != expected_csrf:
        raise RuntimeError(f"legacy CSRF exemption policy drifted: {sorted(legacy_csrf)!r}")

    module.make_password_hash = make_password_hash
    module.verify_password = verify_password
    module.token_digest = token_digest
    module.CSRF_EXEMPT = expected_csrf
    module._client_key = _request_client_key

    def bound_oidc_role(groups: list[str]) -> str:
        return oidc_role(
            groups,
            admin_group=getattr(module, "OIDC_ADMIN_GROUP", ""),
            editor_group=getattr(module, "OIDC_EDITOR_GROUP", ""),
            manager_group=getattr(module, "OIDC_MANAGER_GROUP", ""),
        )

    def bound_manager_target_allowed(manager: Any, target: Any) -> bool:
        return manager_target_allowed(manager.role, manager.department, target.department)

    module._oidc_role = bound_oidc_role
    module._manager_target_allowed = bound_manager_target_allowed
    bound = (
        "make_password_hash",
        "verify_password",
        "token_digest",
        "CSRF_EXEMPT",
        "_client_key",
        "_oidc_role",
        "_manager_target_allowed",
    )
    report = SecurityBindingReport(ok=True, bound_names=bound, csrf_policy_preserved=True)
    module.MGC_SECURITY_BINDING_REPORT = report
    return report


__all__ = ["SecurityBindingReport", "bind_legacy_security"]
