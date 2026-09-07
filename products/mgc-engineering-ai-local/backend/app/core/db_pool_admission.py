from __future__ import annotations

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import get_settings
from app.core.production_certification import db_pool_capacity_snapshot

_MUTATING = {"POST", "PUT", "PATCH", "DELETE"}


class DbPoolAdmissionMiddleware(BaseHTTPMiddleware):
    """Protect PostgreSQL from new mutating HTTP load at critical pool saturation.

    Existing/read traffic is not fenced here. This is backpressure, not an availability claim.
    """

    async def dispatch(self, request: Request, call_next):
        cfg = get_settings()
        if bool(getattr(cfg, "db_pool_admission_control_enabled", True)) and request.method.upper() in _MUTATING:
            snap = db_pool_capacity_snapshot()
            if snap.get("status") == "CRITICAL":
                return JSONResponse(
                    status_code=503,
                    content={"detail": {
                        "code": "DB_POOL_SATURATED",
                        "message": "Database connection capacity is saturated. New mutating work is temporarily backpressured.",
                        "retryable": True,
                    }},
                    headers={"Retry-After": str(max(1, int(getattr(cfg, "db_pool_admission_retry_after_seconds", 3))))},
                )
        return await call_next(request)
