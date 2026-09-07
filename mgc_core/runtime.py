from __future__ import annotations

import importlib
import os
from types import ModuleType

from fastapi import FastAPI

from .auth_bridge import AuthBindingReport, bind_legacy_auth
from .contracts import RouteContractReport, validate_route_contract
from .security_bridge import SecurityBindingReport, bind_legacy_security


LEGACY_APP_MODULE = os.getenv("MGC_LEGACY_APP_MODULE", "app").strip() or "app"


def load_legacy_module(module_name: str = LEGACY_APP_MODULE) -> ModuleType:
    """Load the current application module behind a stable modular boundary."""
    module = importlib.import_module(module_name)
    bind_legacy_security(module)
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
AUTH_BINDING_REPORT: AuthBindingReport = getattr(
    _legacy_module, "MGC_AUTH_BINDING_REPORT"
)

__all__ = [
    "app",
    "CONTRACT_REPORT",
    "SECURITY_BINDING_REPORT",
    "AUTH_BINDING_REPORT",
    "LEGACY_APP_MODULE",
    "load_application",
    "load_legacy_module",
]
