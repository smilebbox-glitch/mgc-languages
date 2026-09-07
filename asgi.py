"""Stable ASGI entrypoint for deployment.

v5.7.3 introduces this boundary so Docker/uvicorn no longer target the legacy
monolithic module directly. The underlying FastAPI object remains identical,
which preserves all existing routes and middleware while modular extraction
continues safely.
"""

from mgc_core.runtime import CONTRACT_REPORT, app

__all__ = ["app", "CONTRACT_REPORT"]
