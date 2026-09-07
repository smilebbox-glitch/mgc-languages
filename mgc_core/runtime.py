from __future__ import annotations

import importlib
import os
from types import ModuleType

from fastapi import FastAPI

from .auth_bridge import AuthBindingReport, bind_legacy_auth
from .contracts import RouteContractReport, validate_route_contract
from .governance_bridge import GovernanceBindingReport, bind_legacy_governance
from .security_bridge import SecurityBindingReport, bind_legacy_security
from .service_bridge import ServiceBindingReport, bind_legacy_services


LEGACY_APP_MODULE = os.getenv("MGC_LEGACY_APP_MODULE", "app").strip() or "app"


def load_legacy_module(module_name: str = LEGACY_APP_MODULE) -> ModuleType:
    """Load the current application module behind a stable modular boundary."""
    module = importlib.import_module(module_name)
    # Ordering is intentional: governance consumes the extracted client fingerprint,
    # services consume governance-safe module state, and auth must capture both the
    # extracted RLS hook and extracted user_view before dependencies are rebound.
    bind_legacy_security(module)
    bind_legacy_governance(module)
    bind_legacy_services(module)
    return module


def load_application(module_name: str = LEGACY_APP_MODULE) -> tuple[FastAPI, RouteContractReport]:
    module = load_legacy_module(module_name)
    application = getattr(module, "app", None)
    if not isinstance(application, FastAPI):
        raise RuntimeError(f"{module_name!r} does not expose a FastAPI instance named 'app'")
    bind_legacy_auth(module, application)
    report = validate_route_contract(application)
    return application, report


app, CONTRACT_REPORT = load_application()
_legacy_module = importlib.import_module(LEGACY_APP_MODULE)
SECURITY_BINDING_REPORT: SecurityBindingReport = getattr(
    _legacy_module, "MGC_SECURITY_BINDING_REPORT"
)
GOVERNANCE_BINDING_REPORT: GovernanceBindingReport = getattr(
    _legacy_module, "MGC_GOVERNANCE_BINDING_REPORT"
)
SERVICE_BINDING_REPORT: ServiceBindingReport = getattr(
    _legacy_module, "MGC_SERVICE_BINDING_REPORT"
)
AUTH_BINDING_REPORT: AuthBindingReport = getattr(
    _legacy_module, "MGC_AUTH_BINDING_REPORT"
)

__all__ = [
    "app",
    "CONTRACT_REPORT",
    "SECURITY_BINDING_REPORT",
    "GOVERNANCE_BINDING_REPORT",
    "SERVICE_BINDING_REPORT",
    "AUTH_BINDING_REPORT",
    "LEGACY_APP_MODULE",
    "load_application",
    "load_legacy_module",
]
