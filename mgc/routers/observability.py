from __future__ import annotations

import hmac
from collections.abc import Callable

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import PlainTextResponse


def build_observability_router(
    *,
    metrics_enabled: bool,
    metrics_token: str,
    metrics_text: Callable[[], str],
) -> APIRouter:
    """Build the Prometheus endpoint without importing the historical app module."""
    router = APIRouter()

    @router.get("/metrics", response_class=PlainTextResponse)
    def metrics(request: Request):
        if not metrics_enabled:
            raise HTTPException(404, "Metrics disabled")
        if metrics_token:
            supplied = request.headers.get("authorization", "")
            expected = f"Bearer {metrics_token}"
            if not hmac.compare_digest(supplied, expected):
                raise HTTPException(
                    401,
                    "Metrics authentication required",
                    headers={"WWW-Authenticate": "Bearer"},
                )
        return metrics_text()

    return router


__all__ = ["build_observability_router"]
