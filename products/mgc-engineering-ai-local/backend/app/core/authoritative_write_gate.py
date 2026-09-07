from __future__ import annotations

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.authoritative_ha import AuthoritativeWriteFence, assert_authoritative_write_safe, should_fence_http_method


class AuthoritativeWriteGateMiddleware(BaseHTTPMiddleware):
    """Fail closed before mutating HTTP requests when DB/evidence authority is not proven safe."""

    async def dispatch(self, request: Request, call_next):
        if should_fence_http_method(request.method):
            try:
                assert_authoritative_write_safe()
            except AuthoritativeWriteFence:
                return JSONResponse(
                    status_code=503,
                    content={"detail": {
                        "code": "AUTHORITATIVE_WRITE_FENCED",
                        "message": "Authoritative writes are temporarily fenced while database/evidence ownership is not proven safe.",
                        "retryable": True,
                    }},
                    headers={"Retry-After": "5"},
                )
        return await call_next(request)
