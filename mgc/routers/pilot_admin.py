from __future__ import annotations

from datetime import datetime
from typing import Any, Callable, Mapping

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session


class PilotGroupPayload(BaseModel):
    name: str = Field(min_length=2, max_length=160)
    department: str = Field(default="General", min_length=1, max_length=160)
    description: str = Field(default="", max_length=2000)
    status: str = Field(default="draft", pattern="^(draft|active|paused|completed)$")
    wave: int = Field(default=1, ge=1, le=100)
    starts_at: datetime | None = None
    ends_at: datetime | None = None


class PilotGroupUpdatePayload(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=160)
    department: str | None = Field(default=None, min_length=1, max_length=160)
    description: str | None = Field(default=None, max_length=2000)
    status: str | None = Field(default=None, pattern="^(draft|active|paused|completed)$")
    wave: int | None = Field(default=None, ge=1, le=100)
    starts_at: datetime | None = None
    ends_at: datetime | None = None


class PilotGroupStatusPayload(BaseModel):
    status: str = Field(pattern="^(draft|active|paused|completed)$")


class PilotFeaturePayload(BaseModel):
    enabled: bool


class FeatureFlagPayload(BaseModel):
    flag_key: str = Field(pattern=r"^[a-z0-9_\-]{2,80}$")
    title: str = Field(min_length=2, max_length=160)
    description: str = Field(default="", max_length=2000)
    default_enabled: bool = True


class TrackAssignmentPayload(BaseModel):
    language: str
    track_name: str = Field(min_length=2, max_length=180)
    topic: str = Field(default="", max_length=180)
    target_level: str = Field(default="A1", pattern="^(A1|A2|B1|B2|C1)$")
    due_date: str = Field(default="", pattern=r"^$|^\d{4}-\d{2}-\d{2}$")


PILOT_ADMIN_HANDLER_NAMES = (
    "admin_pilot_groups",
    "admin_create_pilot_group",
    "admin_pilot_group_status",
    "admin_update_pilot_group",
    "admin_pilot_add_member",
    "admin_pilot_remove_member",
    "admin_pilot_features",
    "admin_create_feature",
    "admin_group_feature",
    "admin_group_assignment",
    "admin_delete_group_assignment",
    "admin_pilot_export_csv",
    "admin_governance_summary",
)


def build_pilot_admin_router(
    *,
    db_session: Callable[..., Any],
    require_roles: Callable[..., Callable[..., Any]],
    handlers: Mapping[str, Callable[..., Any]],
) -> APIRouter:
    """Build admin-only pilot rollout/governance HTTP routes."""
    missing = [name for name in PILOT_ADMIN_HANDLER_NAMES if not callable(handlers.get(name))]
    if missing:
        raise RuntimeError(f"pilot admin router handlers are incomplete: {missing}")

    router = APIRouter()

    @router.get("/api/admin/pilot/groups")
    def admin_pilot_groups(
        user: Any = Depends(require_roles("admin")),
        db: Session = Depends(db_session),
    ):
        return handlers["admin_pilot_groups"](user=user, db=db)

    @router.post("/api/admin/pilot/groups")
    def admin_create_pilot_group(
        payload: PilotGroupPayload,
        request: Request,
        user: Any = Depends(require_roles("admin")),
        db: Session = Depends(db_session),
    ):
        return handlers["admin_create_pilot_group"](
            payload=payload, request=request, user=user, db=db
        )

    @router.patch("/api/admin/pilot/groups/{group_id}/status")
    def admin_pilot_group_status(
        group_id: int,
        payload: PilotGroupStatusPayload,
        request: Request,
        user: Any = Depends(require_roles("admin")),
        db: Session = Depends(db_session),
    ):
        return handlers["admin_pilot_group_status"](
            group_id=group_id, payload=payload, request=request, user=user, db=db
        )

    @router.patch("/api/admin/pilot/groups/{group_id}")
    def admin_update_pilot_group(
        group_id: int,
        payload: PilotGroupUpdatePayload,
        request: Request,
        user: Any = Depends(require_roles("admin")),
        db: Session = Depends(db_session),
    ):
        return handlers["admin_update_pilot_group"](
            group_id=group_id, payload=payload, request=request, user=user, db=db
        )

    @router.post("/api/admin/pilot/groups/{group_id}/members/{user_id}")
    def admin_pilot_add_member(
        group_id: int,
        user_id: int,
        request: Request,
        user: Any = Depends(require_roles("admin")),
        db: Session = Depends(db_session),
    ):
        return handlers["admin_pilot_add_member"](
            group_id=group_id, user_id=user_id, request=request, user=user, db=db
        )

    @router.delete("/api/admin/pilot/groups/{group_id}/members/{user_id}")
    def admin_pilot_remove_member(
        group_id: int,
        user_id: int,
        request: Request,
        user: Any = Depends(require_roles("admin")),
        db: Session = Depends(db_session),
    ):
        return handlers["admin_pilot_remove_member"](
            group_id=group_id, user_id=user_id, request=request, user=user, db=db
        )

    @router.get("/api/admin/pilot/features")
    def admin_pilot_features(
        user: Any = Depends(require_roles("admin")),
        db: Session = Depends(db_session),
    ):
        return handlers["admin_pilot_features"](user=user, db=db)

    @router.post("/api/admin/pilot/features")
    def admin_create_feature(
        payload: FeatureFlagPayload,
        request: Request,
        user: Any = Depends(require_roles("admin")),
        db: Session = Depends(db_session),
    ):
        return handlers["admin_create_feature"](
            payload=payload, request=request, user=user, db=db
        )

    @router.put("/api/admin/pilot/groups/{group_id}/features/{flag_key}")
    def admin_group_feature(
        group_id: int,
        flag_key: str,
        payload: PilotFeaturePayload,
        request: Request,
        user: Any = Depends(require_roles("admin")),
        db: Session = Depends(db_session),
    ):
        return handlers["admin_group_feature"](
            group_id=group_id,
            flag_key=flag_key,
            payload=payload,
            request=request,
            user=user,
            db=db,
        )

    @router.post("/api/admin/pilot/groups/{group_id}/assignments")
    def admin_group_assignment(
        group_id: int,
        payload: TrackAssignmentPayload,
        request: Request,
        user: Any = Depends(require_roles("admin")),
        db: Session = Depends(db_session),
    ):
        return handlers["admin_group_assignment"](
            group_id=group_id, payload=payload, request=request, user=user, db=db
        )

    @router.delete("/api/admin/pilot/groups/{group_id}/assignments/{assignment_id}")
    def admin_delete_group_assignment(
        group_id: int,
        assignment_id: int,
        request: Request,
        user: Any = Depends(require_roles("admin")),
        db: Session = Depends(db_session),
    ):
        return handlers["admin_delete_group_assignment"](
            group_id=group_id,
            assignment_id=assignment_id,
            request=request,
            user=user,
            db=db,
        )

    @router.get("/api/admin/pilot/export.csv")
    def admin_pilot_export_csv(
        group_id: int | None = Query(default=None),
        user: Any = Depends(require_roles("admin")),
        db: Session = Depends(db_session),
    ):
        return handlers["admin_pilot_export_csv"](group_id=group_id, user=user, db=db)

    @router.get("/api/admin/pilot/governance-summary")
    def admin_governance_summary(
        user: Any = Depends(require_roles("admin")),
        db: Session = Depends(db_session),
    ):
        return handlers["admin_governance_summary"](user=user, db=db)

    return router


__all__ = [
    "FeatureFlagPayload",
    "PILOT_ADMIN_HANDLER_NAMES",
    "PilotFeaturePayload",
    "PilotGroupPayload",
    "PilotGroupStatusPayload",
    "PilotGroupUpdatePayload",
    "TrackAssignmentPayload",
    "build_pilot_admin_router",
]
