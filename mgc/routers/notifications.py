from __future__ import annotations

from typing import Any, Callable, Mapping

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session


class NotificationSettingsPayload(BaseModel):
    mode: str = Field(pattern="^(off|minimal|normal|active)$")
    window_start: str = Field(pattern=r"^([01]\d|2[0-3]):[0-5]\d$")
    window_end: str = Field(pattern=r"^([01]\d|2[0-3]):[0-5]\d$")
    browser_enabled: bool = False


NOTIFICATION_HANDLER_NAMES = (
    "get_notification_settings",
    "set_notification_settings",
    "pending_notifications",
    "read_notification",
)


def build_notifications_router(
    *,
    db_session: Callable[..., Any],
    current_user: Callable[..., Any],
    handlers: Mapping[str, Callable[..., Any]],
) -> APIRouter:
    """Build user notification-settings and learning-nudge HTTP routes."""
    missing = [name for name in NOTIFICATION_HANDLER_NAMES if not callable(handlers.get(name))]
    if missing:
        raise RuntimeError(f"notification router handlers are incomplete: {missing}")

    router = APIRouter()

    @router.get("/api/notifications/settings")
    def get_notification_settings(
        user: Any = Depends(current_user),
        db: Session = Depends(db_session),
    ):
        return handlers["get_notification_settings"](user=user, db=db)

    @router.put("/api/notifications/settings")
    def set_notification_settings(
        payload: NotificationSettingsPayload,
        user: Any = Depends(current_user),
        db: Session = Depends(db_session),
    ):
        return handlers["set_notification_settings"](payload=payload, user=user, db=db)

    @router.get("/api/notifications/pending")
    def pending_notifications(
        user: Any = Depends(current_user),
        db: Session = Depends(db_session),
    ):
        return handlers["pending_notifications"](user=user, db=db)

    @router.post("/api/notifications/{nudge_id}/read")
    def read_notification(
        nudge_id: int,
        user: Any = Depends(current_user),
        db: Session = Depends(db_session),
    ):
        return handlers["read_notification"](nudge_id=nudge_id, user=user, db=db)

    return router


__all__ = [
    "NOTIFICATION_HANDLER_NAMES",
    "NotificationSettingsPayload",
    "build_notifications_router",
]
