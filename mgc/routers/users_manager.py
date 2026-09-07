from __future__ import annotations

from typing import Any, Callable, Mapping

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session


class UserRolePayload(BaseModel):
    role: str = Field(pattern="^(user|manager|editor|admin)$")


class UserDepartmentPayload(BaseModel):
    department: str = Field(min_length=1, max_length=160)


USER_MANAGER_HANDLER_NAMES = (
    "admin_users",
    "admin_user_learning_stats",
    "admin_set_role",
    "admin_set_department",
    "manager_team",
    "manager_user_learning_stats",
)


def build_user_manager_router(
    *,
    db_session: Callable[..., Any],
    current_user: Callable[..., Any],
    require_roles: Callable[..., Callable[..., Any]],
    handlers: Mapping[str, Callable[..., Any]],
) -> APIRouter:
    """Build user administration and manager-team HTTP routes."""
    missing = [name for name in USER_MANAGER_HANDLER_NAMES if not callable(handlers.get(name))]
    if missing:
        raise RuntimeError(f"user/manager router handlers are incomplete: {missing}")

    admin_users_handler = handlers["admin_users"]
    admin_user_learning_stats_handler = handlers["admin_user_learning_stats"]
    admin_set_role_handler = handlers["admin_set_role"]
    admin_set_department_handler = handlers["admin_set_department"]
    manager_team_handler = handlers["manager_team"]
    manager_user_learning_stats_handler = handlers["manager_user_learning_stats"]

    router = APIRouter()

    @router.get("/api/admin/users")
    def admin_users(
        user: Any = Depends(require_roles("admin")),
        db: Session = Depends(db_session),
    ):
        return admin_users_handler(user=user, db=db)

    @router.get("/api/admin/users/{user_id}/learning-stats")
    def admin_user_learning_stats(
        user_id: int,
        user: Any = Depends(require_roles("admin")),
        db: Session = Depends(db_session),
    ):
        return admin_user_learning_stats_handler(user_id=user_id, user=user, db=db)

    @router.patch("/api/admin/users/{user_id}/role")
    def admin_set_role(
        user_id: int,
        payload: UserRolePayload,
        request: Request,
        user: Any = Depends(require_roles("admin")),
        db: Session = Depends(db_session),
    ):
        return admin_set_role_handler(
            user_id=user_id,
            payload=payload,
            request=request,
            user=user,
            db=db,
        )

    @router.patch("/api/admin/users/{user_id}/department")
    def admin_set_department(
        user_id: int,
        payload: UserDepartmentPayload,
        request: Request,
        user: Any = Depends(require_roles("admin")),
        db: Session = Depends(db_session),
    ):
        return admin_set_department_handler(
            user_id=user_id,
            payload=payload,
            request=request,
            user=user,
            db=db,
        )

    @router.get("/api/manager/team")
    def manager_team(
        user: Any = Depends(require_roles("manager", "admin")),
        db: Session = Depends(db_session),
    ):
        return manager_team_handler(user=user, db=db)

    @router.get("/api/manager/team/{user_id}/learning-stats")
    def manager_user_learning_stats(
        user_id: int,
        user: Any = Depends(require_roles("manager", "admin")),
        db: Session = Depends(db_session),
    ):
        return manager_user_learning_stats_handler(user_id=user_id, user=user, db=db)

    return router


__all__ = [
    "USER_MANAGER_HANDLER_NAMES",
    "UserDepartmentPayload",
    "UserRolePayload",
    "build_user_manager_router",
]
