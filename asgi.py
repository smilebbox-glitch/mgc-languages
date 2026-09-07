"""Stable ASGI entrypoint for deployment.

v5.7.3-v5.7.9 established modular runtime, security, governance, learning,
service and workflow boundaries. v5.8.0-v5.8.3 extracted system, observability,
auth and learning route ownership. v5.8.4 moves practice, question-attempt and
game lifecycle HTTP routes behind a dedicated APIRouter over the v5.7.9
workflow service.
"""

from mgc_core.runtime import (
    AUTH_BINDING_REPORT,
    AUTH_ROUTER_BINDING_REPORT,
    CONTRACT_REPORT,
    GOVERNANCE_BINDING_REPORT,
    LEARNING_BINDING_REPORT,
    LEARNING_ROUTER_BINDING_REPORT,
    OBSERVABILITY_ROUTER_BINDING_REPORT,
    PRACTICE_GAMES_ROUTER_BINDING_REPORT,
    ROUTER_BINDING_REPORT,
    SECURITY_BINDING_REPORT,
    SERVICE_BINDING_REPORT,
    WORKFLOW_BINDING_REPORT,
    app,
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
]
