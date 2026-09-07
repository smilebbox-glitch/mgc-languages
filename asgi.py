"""Stable ASGI entrypoint for deployment.

v5.7.3-v5.7.9 established modular runtime, security, governance, learning,
service and workflow boundaries. v5.8.0 moves the historical implementation to
``mgc.legacy_app``, keeps ``app.py`` as a compatibility facade and transfers the
first active system endpoints to a real APIRouter module.
"""

from mgc_core.runtime import (
    AUTH_BINDING_REPORT,
    CONTRACT_REPORT,
    GOVERNANCE_BINDING_REPORT,
    LEARNING_BINDING_REPORT,
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
    "WORKFLOW_BINDING_REPORT",
    "AUTH_BINDING_REPORT",
]
