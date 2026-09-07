from __future__ import annotations

import importlib
import os
from types import ModuleType

from fastapi import FastAPI

from .contracts import RouteContractReport, validate_route_contract


LEGACY_APP_MODULE = os.getenv("MGC_LEGACY_APP_MODULE", "app").strip() or "app"


def load_legacy_module(module_name: str = LEGACY_APP_MODULE) -> ModuleType:
    """Load the current application module behind a stable modular boundary."""
    return importlib.import_module(module_name)


def load_application(module_name: str = LEGACY_APP_MODULE) -> tuple[FastAPI, RouteContractReport]:
    module = load_legacy_module(module_name)
    application = getattr(module, "app", None)
    if not isinstance(application, FastAPI):
        raise RuntimeError(f"{module_name!r} does not expose a FastAPI instance named 'app'")
    report = validate_route_contract(application)
    return application, report


app, CONTRACT_REPORT = load_application()

__all__ = ["app", "CONTRACT_REPORT", "LEGACY_APP_MODULE", "load_application", "load_legacy_module"]
