"""Stable ASGI entrypoint for deployment.

v5.7.3 introduced the boundary so Docker/uvicorn no longer target the legacy
monolithic module directly. v5.7.4 binds dependency-light security primitives.
v5.7.5 additionally binds the model-aware auth/session core through FastAPI's
supported dependency override mechanism.
"""

from mgc_core.runtime import (
    AUTH_BINDING_REPORT,
    CONTRACT_REPORT,
    SECURITY_BINDING_REPORT,
    app,
)

__all__ = [
    "app",
    "CONTRACT_REPORT",
    "SECURITY_BINDING_REPORT",
    "AUTH_BINDING_REPORT",
]
