from __future__ import annotations

import importlib
import os
from types import ModuleType

from fastapi import FastAPI

from .auth_bridge import AuthBindingReport, bind_legacy_auth
from .auth_router_bridge import AuthRouterBindingReport, bind_auth_router
from .contracts import RouteContractReport, validate_route_contract
from .governance_bridge import GovernanceBindingReport, bind_legacy_governance
from .learning_bridge import LearningBindingReport, bind_legacy_learning
from .learning_router_bridge import LearningRouterBindingReport, bind_learning_router
from .observability_bridge import ObservabilityRouterBindingReport, bind_observability_router
from .practice_games_router_bridge import (
    PracticeGamesRouterBindingReport,
    bind_practice_games_router,
)
from .pronunciation_router_bridge import (
    PronunciationRouterBindingReport,
    bind_pronunciation_router,
)
from .router_bridge import RouterBindingReport, bind_system_router
from .security_bridge import SecurityBindingReport, bind_legacy_security
from .service_bridge import ServiceBindingReport, bind_legacy_services
from .terminology_admin_router_bridge import (
    TerminologyAdminRouterBindingReport,
    bind_terminology_admin_router,
)
from .workflow_bridge import WorkflowBindingReport, bind_legacy_workflows


LEGACY_APP_MODULE = os.getenv("MGC_LEGACY_APP_MODULE", "mgc.legacy_app").strip() or "mgc.legacy_app"


def load_legacy_module(module_name: str = LEGACY_APP_MODULE) -> ModuleType:
    """Load the historical implementation behind the stable modular boundary."""
    module = importlib.import_module(module_name)
    # Ordering is intentional: governance consumes the extracted client fingerprint;
    # learning binds before user services; services bind before workflows. Active
    # routers are replaced only after the FastAPI object exists. Auth core binds
    # before auth/learning/practice-game/terminology/pronunciation routers.
    # Terminology admin also requires extracted terminology and governance services.
    bind_legacy_security(module)
    bind_legacy_governance(module)
    bind_legacy_learning(module)
    bind_legacy_services(module)
    return module


def load_application(module_name: str = LEGACY_APP_MODULE) -> tuple[FastAPI, RouteContractReport]:
    module = load_legacy_module(module_name)
    application = getattr(module, "app", None)
    if not isinstance(application, FastAPI):
        raise RuntimeError(f"{module_name!r} does not expose a FastAPI instance named 'app'")
    bind_system_router(module, application)
    bind_observability_router(module, application)
    bind_legacy_workflows(module, application)
    bind_legacy_auth(module, application)
    bind_auth_router(module, application)
    bind_learning_router(module, application)
    bind_practice_games_router(module, application)
    bind_terminology_admin_router(module, application)
    bind_pronunciation_router(module, application)
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
LEARNING_BINDING_REPORT: LearningBindingReport = getattr(
    _legacy_module, "MGC_LEARNING_BINDING_REPORT"
)
SERVICE_BINDING_REPORT: ServiceBindingReport = getattr(
    _legacy_module, "MGC_SERVICE_BINDING_REPORT"
)
ROUTER_BINDING_REPORT: RouterBindingReport = getattr(
    _legacy_module, "MGC_ROUTER_BINDING_REPORT"
)
OBSERVABILITY_ROUTER_BINDING_REPORT: ObservabilityRouterBindingReport = getattr(
    _legacy_module, "MGC_OBSERVABILITY_ROUTER_BINDING_REPORT"
)
WORKFLOW_BINDING_REPORT: WorkflowBindingReport = getattr(
    _legacy_module, "MGC_WORKFLOW_BINDING_REPORT"
)
AUTH_BINDING_REPORT: AuthBindingReport = getattr(
    _legacy_module, "MGC_AUTH_BINDING_REPORT"
)
AUTH_ROUTER_BINDING_REPORT: AuthRouterBindingReport = getattr(
    _legacy_module, "MGC_AUTH_ROUTER_BINDING_REPORT"
)
LEARNING_ROUTER_BINDING_REPORT: LearningRouterBindingReport = getattr(
    _legacy_module, "MGC_LEARNING_ROUTER_BINDING_REPORT"
)
PRACTICE_GAMES_ROUTER_BINDING_REPORT: PracticeGamesRouterBindingReport = getattr(
    _legacy_module, "MGC_PRACTICE_GAMES_ROUTER_BINDING_REPORT"
)
TERMINOLOGY_ADMIN_ROUTER_BINDING_REPORT: TerminologyAdminRouterBindingReport = getattr(
    _legacy_module, "MGC_TERMINOLOGY_ADMIN_ROUTER_BINDING_REPORT"
)
PRONUNCIATION_ROUTER_BINDING_REPORT: PronunciationRouterBindingReport = getattr(
    _legacy_module, "MGC_PRONUNCIATION_ROUTER_BINDING_REPORT"
)

__all__ = [
    "app",
    "CONTRACT_REPORT",
    "SECURITY_BINDING_REPORT",
    "GOVERNANCE_BINDING_REPORT",
    "LEARNING_BINDING_REPORT",
    "SERVICE_BINDING_REPORT",
    "ROUTER_BINDING_REPORT",
    "OBSERVABILITY_ROUTER_BINDING_REPORT",
    "WORKFLOW_BINDING_REPORT",
    "AUTH_BINDING_REPORT",
    "AUTH_ROUTER_BINDING_REPORT",
    "LEARNING_ROUTER_BINDING_REPORT",
    "PRACTICE_GAMES_ROUTER_BINDING_REPORT",
    "TERMINOLOGY_ADMIN_ROUTER_BINDING_REPORT",
    "PRONUNCIATION_ROUTER_BINDING_REPORT",
    "LEGACY_APP_MODULE",
    "load_application",
    "load_legacy_module",
]
