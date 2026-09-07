"""FastAPI router modules extracted from the historical monolith."""

from .admin_ops import build_admin_ops_router
from .auth import build_auth_router
from .learning import build_learning_router
from .notifications import build_notifications_router
from .observability import build_observability_router
from .pilot_admin import build_pilot_admin_router
from .practice_games import build_practice_games_router
from .pronunciation import build_pronunciation_router
from .system import build_system_router
from .terminology_admin import build_terminology_admin_router
from .users_manager import build_user_manager_router

__all__ = [
    "build_admin_ops_router",
    "build_auth_router",
    "build_learning_router",
    "build_notifications_router",
    "build_observability_router",
    "build_pilot_admin_router",
    "build_practice_games_router",
    "build_pronunciation_router",
    "build_system_router",
    "build_terminology_admin_router",
    "build_user_manager_router",
]
