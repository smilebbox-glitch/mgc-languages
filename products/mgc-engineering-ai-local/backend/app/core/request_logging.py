from __future__ import annotations

import json
import logging
import re
import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from prometheus_client import Counter, Histogram
from app.core.db_performance import begin_request_budget, end_request_budget, set_request_route

log = logging.getLogger("mgc.ops.http")
HTTP_REQUESTS = Counter("mgc_http_requests_total", "HTTP requests by bounded route template/status class", ["method", "route", "status_class"])
HTTP_DURATION = Histogram("mgc_http_request_duration_seconds", "HTTP request latency by bounded route template", ["method", "route"], buckets=(0.01,0.025,0.05,0.1,0.25,0.5,1,2.5,5,10))
_SAFE_REQUEST_ID = re.compile(r"^[A-Za-z0-9._:-]{8,128}$")


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Emit privacy-minimized structured request logs.

    Only the resolved route template is logged (never query strings, request/response bodies,
    VINs/part numbers embedded in concrete URLs, auth headers, or user identity).
    """

    async def dispatch(self, request: Request, call_next):
        supplied = request.headers.get("X-Request-ID", "")
        request_id = supplied if _SAFE_REQUEST_ID.fullmatch(supplied) else str(uuid.uuid4())
        started = time.perf_counter()
        budget_token = begin_request_budget()
        status = 500
        route_template = "unresolved"
        db_summary = None
        try:
            response = await call_next(request)
            status = response.status_code
            route = request.scope.get("route")
            route_template = getattr(route, "path", "unresolved")
            set_request_route(route_template)
            response.headers["X-Request-ID"] = request_id
            return response
        finally:
            db_summary = end_request_budget(budget_token)
            duration_seconds = time.perf_counter() - started
            duration_ms = round(duration_seconds * 1000.0, 1)
            if route_template != "unresolved":
                status_class = f"{int(status)//100}xx" if isinstance(status, int) else "unknown"
                HTTP_REQUESTS.labels(request.method, route_template, status_class).inc()
                HTTP_DURATION.labels(request.method, route_template).observe(duration_seconds)
            # Health/metrics traffic is intentionally excluded from access-style logs.
            if route_template not in {"/health", "/health/live", "/health/ready", "/metrics"}:
                log.info(json.dumps({
                    "event": "http_request",
                    "request_id": request_id,
                    "method": request.method,
                    "route": route_template,
                    "status": status,
                    "duration_ms": duration_ms,
                    "db_statements": db_summary.statements if db_summary else 0,
                    "db_time_ms": db_summary.db_time_ms if db_summary else 0.0,
                    "db_budget_warning": bool(db_summary and (db_summary.statement_budget_exceeded or db_summary.time_budget_exceeded)),
                }, separators=(",", ":"), sort_keys=True))
