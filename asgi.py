"""Stable ASGI entrypoint for deployment.

v5.7.3 introduced the boundary so Docker/uvicorn no longer target the legacy
monolithic module directly. v5.7.4 additionally binds extracted security
primitives before production traffic reaches the application.
"""

from mgc_core.runtime import CONTRACT_REPORT, SECURITY_BINDING_REPORT, app

__all__ = ["app", "CONTRACT_REPORT", "SECURITY_BINDING_REPORT"]
