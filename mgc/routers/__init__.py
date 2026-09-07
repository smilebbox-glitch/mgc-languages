"""FastAPI router modules extracted from the historical monolith."""

from .auth import build_auth_router
from .learning import build_learning_router
from .observability import build_observability_router
from .practice_games import build_practice_games_router
from .system import build_system_router

__all__ = [
    "build_auth_router",
    "build_learning_router",
    "build_observability_router",
    "build_practice_games_router",
    "build_system_router",
]
