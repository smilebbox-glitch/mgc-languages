"""Stable ASGI entrypoint for deployment.

v5.7.3-v5.7.9 established modular runtime, security, governance, learning,
service and workflow boundaries. v5.8.0-v5.8.4 extracted system, observability,
auth, learning and practice/game route ownership. v5.8.5 moves public
terminology and corporate terminology administration behind a dedicated
APIRouter. v5.8.6 moves pronunciation/TTS HTTP ownership behind a dedicated
router. v5.8.7 moves synthesis/cache/health/circuit-breaker state into a
standalone TTS core while preserving observability and pronunciation contracts.
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
    PRONUNCIATION_ROUTER_BINDING_REPORT,
    ROUTER_BINDING_REPORT,
    SECURITY_BINDING_REPORT,
    SERVICE_BINDING_REPORT,
    TERMINOLOGY_ADMIN_ROUTER_BINDING_REPORT,
    TTS_BINDING_REPORT,
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
    "TTS_BINDING_REPORT",
    "ROUTER_BINDING_REPORT",
    "OBSERVABILITY_ROUTER_BINDING_REPORT",
    "WORKFLOW_BINDING_REPORT",
    "AUTH_BINDING_REPORT",
    "AUTH_ROUTER_BINDING_REPORT",
    "LEARNING_ROUTER_BINDING_REPORT",
    "PRACTICE_GAMES_ROUTER_BINDING_REPORT",
    "TERMINOLOGY_ADMIN_ROUTER_BINDING_REPORT",
    "PRONUNCIATION_ROUTER_BINDING_REPORT",
]
