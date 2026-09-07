"""Stable ASGI entrypoint for deployment.

v5.7.3-v5.7.9 established modular runtime, security, governance, learning,
service and workflow boundaries. v5.8.0 introduced the compatibility facade and
system router extraction; v5.8.1 moved observability, v5.8.2 moved auth, and
v5.8.3 moves active progress/course/SRS/gamification/preferences routes behind a
dedicated learning APIRouter.
"""

from mgc_core.runtime import (
    AUTH_BINDING_REPORT,
    AUTH_ROUTER_BINDING_REPORT,
    CONTRACT_REPORT,
    GOVERNANCE_BINDING_REPORT,
    LEARNING_BINDING_REPORT,
    LEARNING_ROUTER_BINDING_REPORT,
    OBSERVABILITY_ROUTER_BINDING_REPORT,
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
]
