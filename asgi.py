"""Stable ASGI entrypoint for deployment.

v5.7.3 introduced the boundary so Docker/uvicorn no longer target the legacy
monolithic module directly. v5.7.4-v5.7.8 progressively bind security, auth,
governance, user/terminology and learning services. v5.7.9 moves practice/game
orchestration behind endpoint-compatible workflow services while preserving the
registered FastAPI dependency and OpenAPI contracts.
"""

from mgc_core.runtime import (
    AUTH_BINDING_REPORT,
    CONTRACT_REPORT,
    GOVERNANCE_BINDING_REPORT,
    LEARNING_BINDING_REPORT,
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
    "WORKFLOW_BINDING_REPORT",
    "AUTH_BINDING_REPORT",
]
