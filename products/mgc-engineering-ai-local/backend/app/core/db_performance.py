from __future__ import annotations

import contextvars
import re
import threading
import time
from collections import Counter, deque
from dataclasses import dataclass
from typing import Any

from prometheus_client import Counter as PromCounter, Gauge, Histogram
from sqlalchemy import event

from app.core.config import get_settings

DB_QUERY_DURATION = Histogram(
    "mgc_db_query_duration_seconds",
    "Database query latency by sanitized operation/table",
    ["operation", "table"],
    buckets=(0.001,0.0025,0.005,0.01,0.025,0.05,0.1,0.25,0.5,1,2.5,5),
)
DB_SLOW_QUERIES = PromCounter(
    "mgc_db_slow_queries_total",
    "Slow database statements by sanitized operation/table",
    ["operation", "table"],
)
DB_REQUEST_STATEMENTS = Histogram(
    "mgc_db_statements_per_request",
    "SQL statements executed per HTTP request",
    buckets=(1,2,3,5,8,13,21,34,55,89,144),
)
DB_REQUEST_TIME = Histogram(
    "mgc_db_time_per_request_seconds",
    "Cumulative database time per HTTP request",
    buckets=(0.001,0.005,0.01,0.025,0.05,0.1,0.25,0.5,1,2,5,10),
)
DB_QUERY_BUDGET_WARNINGS = PromCounter(
    "mgc_db_query_budget_warnings_total",
    "Requests exceeding configured DB statement/time budget",
    ["reason"],
)
DB_POOL_CHECKED_OUT = Gauge("mgc_db_pool_checked_out", "Checked-out DB pool connections")
DB_POOL_SIZE = Gauge("mgc_db_pool_size", "Configured/current SQLAlchemy pool size")

_request_state: contextvars.ContextVar[dict[str, Any] | None] = contextvars.ContextVar("mgc_db_request_state", default=None)
_slow_events: deque[dict[str, Any]] = deque(maxlen=200)
_aggregate_lock = threading.Lock()
_statement_counts: Counter[tuple[str,str]] = Counter()
_statement_time_ms: Counter[tuple[str,str]] = Counter()
_total_statements = 0
_total_time_ms = 0.0
_installed_engines: set[int] = set()

class QueryBudgetExceeded(RuntimeError):
    pass

@dataclass(frozen=True)
class RequestDbSummary:
    statements: int
    db_time_ms: float
    statement_budget_exceeded: bool
    time_budget_exceeded: bool

_SQL_TABLE = re.compile(r"\b(?:FROM|INTO|UPDATE|JOIN)\s+([\w\".]+)", re.I)
_SQL_OP = re.compile(r"^\s*(SELECT|INSERT|UPDATE|DELETE|WITH|CREATE|ALTER|DROP)", re.I)

def _sanitize_statement(statement: str) -> tuple[str, str]:
    op_m = _SQL_OP.search(statement or "")
    op = (op_m.group(1).upper() if op_m else "OTHER")[:16]
    table_m = _SQL_TABLE.search(statement or "")
    table = (table_m.group(1).strip('"').split('.')[-1] if table_m else "unknown")
    table = re.sub(r"[^A-Za-z0-9_]", "", table)[:64] or "unknown"
    return op, table

def begin_request_budget(route: str = "unresolved"):
    return _request_state.set({"route": route, "statements": 0, "db_time_ms": 0.0})

def set_request_route(route: str) -> None:
    state = _request_state.get()
    if state is not None:
        state["route"] = route

def end_request_budget(token=None) -> RequestDbSummary:
    cfg = get_settings()
    state = _request_state.get() or {"statements": 0, "db_time_ms": 0.0}
    statements = int(state.get("statements") or 0)
    db_time_ms = float(state.get("db_time_ms") or 0.0)
    statement_exceeded = statements > max(1, int(cfg.db_query_budget_max_statements))
    time_exceeded = db_time_ms > max(1.0, float(cfg.db_query_budget_max_ms))
    DB_REQUEST_STATEMENTS.observe(statements)
    DB_REQUEST_TIME.observe(db_time_ms / 1000.0)
    if statement_exceeded:
        DB_QUERY_BUDGET_WARNINGS.labels("statements").inc()
    if time_exceeded:
        DB_QUERY_BUDGET_WARNINGS.labels("time").inc()
    if token is not None:
        _request_state.reset(token)
    return RequestDbSummary(statements, round(db_time_ms, 3), statement_exceeded, time_exceeded)

def _pool_snapshot(engine) -> dict[str, Any]:
    pool = engine.pool
    def safe(name: str):
        fn = getattr(pool, name, None)
        try:
            return int(fn()) if callable(fn) else None
        except Exception:
            return None
    size = safe("size")
    checkedout = safe("checkedout")
    if size is not None: DB_POOL_SIZE.set(size)
    if checkedout is not None: DB_POOL_CHECKED_OUT.set(checkedout)
    return {"size": size, "checked_out": checkedout, "overflow": safe("overflow"), "checked_in": safe("checkedin")}

def performance_snapshot(engine=None) -> dict[str, Any]:
    with _aggregate_lock:
        top = [
            {"operation": op, "table": table, "statements": count, "total_ms": round(float(_statement_time_ms[(op,table)]), 3)}
            for (op,table), count in _statement_counts.most_common(12)
        ]
        totals = {"statements": int(_total_statements), "db_time_ms": round(float(_total_time_ms), 3)}
        slow = list(_slow_events)[-20:]
    cfg = get_settings()
    return {
        "schema": "mgc-db-performance-v1",
        "slow_query_threshold_ms": float(cfg.db_slow_query_ms),
        "request_budget": {
            "max_statements": int(cfg.db_query_budget_max_statements),
            "max_db_time_ms": float(cfg.db_query_budget_max_ms),
            "hard_enforcement": bool(cfg.db_query_budget_enforcement_enabled),
        },
        "totals_since_process_start": totals,
        "top_statement_groups": top,
        "recent_slow_query_groups": slow,
        "pool": _pool_snapshot(engine) if engine is not None else {},
        "privacy": {"sql_text_stored": False, "bind_values_stored": False},
    }

def install_db_performance_instrumentation(engine) -> None:
    global _total_statements, _total_time_ms
    if id(engine) in _installed_engines:
        return
    _installed_engines.add(id(engine))

    @event.listens_for(engine, "before_cursor_execute")
    def _before(conn, cursor, statement, parameters, context, executemany):
        cfg = get_settings()
        state = _request_state.get()
        if state is not None and cfg.db_query_budget_enforcement_enabled:
            if int(state.get("statements") or 0) >= int(cfg.db_query_budget_max_statements):
                raise QueryBudgetExceeded("Database statement budget exceeded")
            if float(state.get("db_time_ms") or 0.0) >= float(cfg.db_query_budget_max_ms):
                raise QueryBudgetExceeded("Database time budget exceeded")
        context._mgc_query_started = time.perf_counter()

    @event.listens_for(engine, "after_cursor_execute")
    def _after(conn, cursor, statement, parameters, context, executemany):
        global _total_statements, _total_time_ms
        started = getattr(context, "_mgc_query_started", None)
        if started is None:
            return
        elapsed_ms = (time.perf_counter() - started) * 1000.0
        op, table = _sanitize_statement(statement)
        DB_QUERY_DURATION.labels(op, table).observe(elapsed_ms / 1000.0)
        cfg = get_settings()
        if elapsed_ms >= float(cfg.db_slow_query_ms):
            DB_SLOW_QUERIES.labels(op, table).inc()
            with _aggregate_lock:
                _slow_events.append({"operation": op, "table": table, "duration_ms": round(elapsed_ms, 3), "at_monotonic": round(time.monotonic(), 3)})
        state = _request_state.get()
        if state is not None:
            state["statements"] = int(state.get("statements") or 0) + 1
            state["db_time_ms"] = float(state.get("db_time_ms") or 0.0) + elapsed_ms
        with _aggregate_lock:
            _total_statements += 1
            _total_time_ms += elapsed_ms
            _statement_counts[(op,table)] += 1
            _statement_time_ms[(op,table)] += elapsed_ms
