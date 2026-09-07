"""Stable ASGI entrypoint for deployment.

v5.7.3 introduced the boundary so Docker/uvicorn no longer target the legacy
monolithic module directly. v5.7.4 binds dependency-light security primitives.
v5.7.5 binds the model-aware auth/session core through FastAPI dependency
overrides. v5.7.6 binds RLS identity and audit-chain execution before auth is
constructed. v5.7.7 inserts the user/terminology service layer before auth so
business helpers execute from modular services while route objects stay stable.
"""

from mgc_core.runtime import (
    AUTH_BINDING_REPORT,
    CONTRACT_REPORT,
    GOVERNANCE_BINDING_REPORT,
    SECURITY_BINDING_REPORT,
    SERVICE_BINDING_REPORT,
    app,
)

__all__ = [
    "app",
    "CONTRACT_REPORT",
    "SECURITY_BINDING_REPORT",
    "GOVERNANCE_BINDING_REPORT",
    "SERVICE_BINDING_REPORT",
    "AUTH_BINDING_REPORT",
]
