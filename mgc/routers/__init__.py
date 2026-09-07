"""FastAPI router modules extracted from the historical monolith."""

from .observability import build_observability_router
from .system import build_system_router

__all__ = ["build_observability_router", "build_system_router"]
