from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Iterable

from fastapi import FastAPI


CRITICAL_ROUTE_CONTRACT = frozenset({
    ("GET", "/health"),
    ("GET", "/health/live"),
    ("GET", "/ready"),
    ("GET", "/health/ready"),
    ("GET", "/metrics"),
    ("GET", "/api/meta"),
    ("POST", "/api/login"),
    ("POST", "/api/logout"),
    ("GET", "/api/me"),
    ("POST", "/api/shift-simulations"),
    ("GET", "/api/shift-simulations/history"),
    ("GET", "/api/manager/shift-analytics"),
    ("GET", "/api/leaderboards/games/{game_type}"),
    ("GET", "/api/leaderboards/shifts"),
})


class RuntimeContractError(RuntimeError):
    """Raised when the deployed FastAPI application violates its stable contract."""


@dataclass(frozen=True)
class RouteContractReport:
    route_count: int
    unique_route_count: int
    missing_required: tuple[tuple[str, str], ...]
    duplicate_routes: tuple[tuple[str, str], ...]

    @property
    def ok(self) -> bool:
        return not self.missing_required and not self.duplicate_routes


def route_inventory(application: FastAPI) -> tuple[tuple[str, str], ...]:
    """Return deterministic HTTP method/path pairs, excluding Starlette mounts."""
    rows: list[tuple[str, str]] = []
    for route in application.routes:
        path = getattr(route, "path", None)
        methods = getattr(route, "methods", None)
        if not path or not methods:
            continue
        for method in methods:
            rows.append((str(method).upper(), str(path)))
    return tuple(sorted(rows))


def inspect_route_contract(
    application: FastAPI,
    required: Iterable[tuple[str, str]] = CRITICAL_ROUTE_CONTRACT,
) -> RouteContractReport:
    inventory = route_inventory(application)
    counts = Counter(inventory)
    inventory_set = set(inventory)
    required_set = {(str(method).upper(), str(path)) for method, path in required}
    missing = tuple(sorted(required_set - inventory_set))
    duplicates = tuple(sorted(key for key, count in counts.items() if count > 1))
    return RouteContractReport(
        route_count=len(inventory),
        unique_route_count=len(inventory_set),
        missing_required=missing,
        duplicate_routes=duplicates,
    )


def validate_route_contract(
    application: FastAPI,
    required: Iterable[tuple[str, str]] = CRITICAL_ROUTE_CONTRACT,
) -> RouteContractReport:
    report = inspect_route_contract(application, required)
    if report.ok:
        return report
    details: list[str] = []
    if report.missing_required:
        details.append("missing=" + ",".join(f"{method} {path}" for method, path in report.missing_required))
    if report.duplicate_routes:
        details.append("duplicates=" + ",".join(f"{method} {path}" for method, path in report.duplicate_routes))
    raise RuntimeContractError("FastAPI runtime contract violation: " + "; ".join(details))
