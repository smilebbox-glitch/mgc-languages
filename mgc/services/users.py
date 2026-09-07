from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from sqlalchemy import select
from sqlalchemy.orm import Session


@dataclass(frozen=True)
class UserServiceBindings:
    user_view: Callable[[Any], dict[str, Any]]
    user_admin_stats: Callable[[Session, Any], dict[str, Any]]
    manager_target_allowed: Callable[[Any, Any], bool]


def build_user_service(
    *,
    term_progress_model: Any,
    exam_result_model: Any,
    gamification_view: Callable[[Session, int], dict[str, Any]],
    notification_pref: Callable[[Session, int], Any],
) -> UserServiceBindings:
    """Build user/admin business helpers without importing the legacy app module."""

    def user_view(user: Any) -> dict[str, Any]:
        return {
            "id": user.id,
            "username": user.username,
            "display_name": user.display_name,
            "role": user.role,
            "department": user.department,
            "preferred_language": user.preferred_language,
        }

    user_view.__name__ = "user_view"
    user_view.__qualname__ = "user_view"

    def user_admin_stats(db: Session, row: Any) -> dict[str, Any]:
        profile = gamification_view(db, row.id)
        progress = db.scalars(
            select(term_progress_model).where(term_progress_model.user_id == row.id)
        ).all()
        known = sum(1 for item in progress if item.status == "known")
        exams = db.scalars(
            select(exam_result_model).where(exam_result_model.user_id == row.id)
        ).all()
        last = profile.get("last_activity_at")
        pref = notification_pref(db, row.id)
        return {
            "id": row.id,
            "username": row.username,
            "display_name": row.display_name,
            "role": row.role,
            "department": row.department,
            "preferred_language": row.preferred_language,
            "level": profile["level"],
            "level_title": profile["title"],
            "lifetime_xp": profile["lifetime_xp"],
            "spendable_xp": profile["spendable_xp"],
            "weekly_xp": profile["weekly_xp"],
            "terms_known": known,
            "terms_touched": len(progress),
            "best_exam": max((item.score for item in exams), default=0),
            "last_activity_at": last,
            "notification_mode": pref.mode,
            "created_at": row.created_at.isoformat(),
        }

    user_admin_stats.__name__ = "user_admin_stats"
    user_admin_stats.__qualname__ = "user_admin_stats"

    def manager_target_allowed(manager: Any, target: Any) -> bool:
        return manager.role == "admin" or (
            manager.role == "manager" and manager.department == target.department
        )

    manager_target_allowed.__name__ = "_manager_target_allowed"
    manager_target_allowed.__qualname__ = "_manager_target_allowed"

    return UserServiceBindings(
        user_view=user_view,
        user_admin_stats=user_admin_stats,
        manager_target_allowed=manager_target_allowed,
    )


__all__ = ["UserServiceBindings", "build_user_service"]
