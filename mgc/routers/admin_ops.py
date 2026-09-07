from __future__ import annotations

from typing import Any, Callable, Mapping

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session


class AlertAckPayload(BaseModel):
    note: str = Field(default="", max_length=500)


ADMIN_OPS_HANDLER_NAMES = (
    "admin_slo",
    "admin_alerts",
    "admin_alert_ack",
    "learning_error_telemetry",
    "pilot_telemetry",
    "admin_analytics",
    "admin_audit",
    "admin_database_telemetry",
    "admin_recovery_evidence",
    "admin_it_dashboard",
    "admin_maintenance_cleanup",
    "admin_operational_events",
    "admin_system_summary",
)


def build_admin_ops_router(
    *,
    db_session: Callable[..., Any],
    require_roles: Callable[..., Callable[..., Any]],
    handlers: Mapping[str, Callable[..., Any]],
) -> APIRouter:
    """Build admin-only observability, recovery and operations HTTP routes."""
    missing = [name for name in ADMIN_OPS_HANDLER_NAMES if not callable(handlers.get(name))]
    if missing:
        raise RuntimeError(f"admin ops router handlers are incomplete: {missing}")

    router = APIRouter()

    @router.get("/api/admin/slo")
    def admin_slo(user: Any = Depends(require_roles("admin"))):
        return handlers["admin_slo"](user=user)

    @router.get("/api/admin/alerts")
    def admin_alerts(
        status: str | None = Query(default=None, pattern="^(open|acknowledged|resolved)$"),
        user: Any = Depends(require_roles("admin")),
        db: Session = Depends(db_session),
    ):
        return handlers["admin_alerts"](status=status, user=user, db=db)

    @router.patch("/api/admin/alerts/{alert_id}/ack")
    def admin_alert_ack(
        alert_id: int,
        payload: AlertAckPayload,
        request: Request,
        user: Any = Depends(require_roles("admin")),
        db: Session = Depends(db_session),
    ):
        return handlers["admin_alert_ack"](
            alert_id=alert_id, payload=payload, request=request, user=user, db=db
        )

    @router.get("/api/admin/learning-error-telemetry")
    def learning_error_telemetry(
        days: int = Query(default=7, ge=1, le=90),
        user: Any = Depends(require_roles("admin")),
        db: Session = Depends(db_session),
    ):
        return handlers["learning_error_telemetry"](days=days, user=user, db=db)

    @router.get("/api/admin/pilot-telemetry")
    def pilot_telemetry(
        user: Any = Depends(require_roles("admin")),
        db: Session = Depends(db_session),
    ):
        return handlers["pilot_telemetry"](user=user, db=db)

    @router.get("/api/admin/analytics")
    def admin_analytics(
        user: Any = Depends(require_roles("admin")),
        db: Session = Depends(db_session),
    ):
        return handlers["admin_analytics"](user=user, db=db)

    @router.get("/api/admin/audit")
    def admin_audit(
        limit: int = Query(default=100, ge=1, le=500),
        event_type: str | None = None,
        user: Any = Depends(require_roles("admin")),
        db: Session = Depends(db_session),
    ):
        return handlers["admin_audit"](
            limit=limit, event_type=event_type, user=user, db=db
        )

    @router.get("/api/admin/database/telemetry")
    def admin_database_telemetry(user: Any = Depends(require_roles("admin"))):
        return handlers["admin_database_telemetry"](user=user)

    @router.get("/api/admin/recovery/evidence")
    def admin_recovery_evidence(user: Any = Depends(require_roles("admin"))):
        return handlers["admin_recovery_evidence"](user=user)

    @router.get("/api/admin/it-dashboard")
    def admin_it_dashboard(
        user: Any = Depends(require_roles("admin")),
        db: Session = Depends(db_session),
    ):
        return handlers["admin_it_dashboard"](user=user, db=db)

    @router.post("/api/admin/maintenance/cleanup")
    def admin_maintenance_cleanup(
        request: Request,
        dry_run: bool = Query(default=True),
        user: Any = Depends(require_roles("admin")),
        db: Session = Depends(db_session),
    ):
        return handlers["admin_maintenance_cleanup"](
            request=request, dry_run=dry_run, user=user, db=db
        )

    @router.get("/api/admin/operational-events")
    def admin_operational_events(
        limit: int = Query(default=100, ge=1, le=500),
        severity: str | None = None,
        component: str | None = None,
        user: Any = Depends(require_roles("admin")),
        db: Session = Depends(db_session),
    ):
        return handlers["admin_operational_events"](
            limit=limit, severity=severity, component=component, user=user, db=db
        )

    @router.get("/api/admin/system/summary")
    def admin_system_summary(
        user: Any = Depends(require_roles("admin")),
        db: Session = Depends(db_session),
    ):
        return handlers["admin_system_summary"](user=user, db=db)

    return router


__all__ = [
    "ADMIN_OPS_HANDLER_NAMES",
    "AlertAckPayload",
    "build_admin_ops_router",
]
