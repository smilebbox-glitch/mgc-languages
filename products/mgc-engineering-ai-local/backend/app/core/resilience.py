from __future__ import annotations

import threading
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Iterator

from prometheus_client import Counter, Gauge

from app.core.config import get_settings


CIRCUIT_STATE = Gauge(
    "mgc_resilience_circuit_state",
    "Circuit state: 0=closed, 1=half_open, 2=open",
    ["dependency"],
)
CIRCUIT_FAILURES = Gauge(
    "mgc_resilience_consecutive_failures",
    "Consecutive dependency failures observed by this process",
    ["dependency"],
)
CIRCUIT_TRIPS = Counter(
    "mgc_resilience_circuit_trips_total",
    "Circuit breaker trips by dependency",
    ["dependency"],
)
BROWNOUT = Gauge("mgc_resilience_brownout", "1 when optional capabilities are in brownout")

STATE_VALUE = {"closed": 0, "half_open": 1, "open": 2}
OPTIONAL_DEPENDENCIES = frozenset({"qdrant", "local_ai", "vlm", "native_cad"})
CAPABILITY_DEPENDENCY = {
    "semantic_search": "qdrant",
    "qdrant": "qdrant",
    "embeddings": "qdrant",
    "local_llm": "local_ai",
    "reranker": "local_ai",
    "local_vlm": "vlm",
    "native_cad_gateway": "native_cad",
}


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class Circuit:
    dependency: str
    state: str = "closed"
    consecutive_failures: int = 0
    opened_monotonic: float | None = None
    last_success_at: str | None = None
    last_failure_at: str | None = None
    last_failure_kind: str | None = None
    half_open_probe_in_flight: bool = False
    lock: threading.RLock = field(default_factory=threading.RLock, repr=False)

    def snapshot(self) -> dict:
        with self.lock:
            return {
                "dependency": self.dependency,
                "state": self.state,
                "consecutive_failures": self.consecutive_failures,
                "last_success_at": self.last_success_at,
                "last_failure_at": self.last_failure_at,
                "last_failure_kind": self.last_failure_kind,
                "half_open_probe_in_flight": self.half_open_probe_in_flight,
            }


class CircuitOpenError(RuntimeError):
    def __init__(self, dependency: str):
        super().__init__(f"Dependency circuit is open: {dependency}")
        self.dependency = dependency


class ResilienceRegistry:
    """Process-local dependency protection.

    It is deliberately non-authoritative: restarting a process resets breaker state. PostgreSQL
    and evidence storage remain the engineering sources of truth. The breaker only suppresses
    repeated calls to degraded optional infrastructure and allows deterministic Core fallbacks.
    """

    def __init__(self) -> None:
        self._circuits: dict[str, Circuit] = {}
        self._lock = threading.RLock()

    def circuit(self, dependency: str) -> Circuit:
        dependency = dependency.strip().lower()
        with self._lock:
            return self._circuits.setdefault(dependency, Circuit(dependency))

    def allows(self, dependency: str) -> bool:
        cfg = get_settings()
        if not cfg.resilience_enabled:
            return True
        c = self.circuit(dependency)
        with c.lock:
            if c.state == "closed":
                return True
            if c.state == "open":
                opened = c.opened_monotonic or time.monotonic()
                if time.monotonic() - opened < max(1.0, float(cfg.resilience_open_seconds)):
                    return False
                c.state = "half_open"
                c.half_open_probe_in_flight = False
            if c.state == "half_open":
                if c.half_open_probe_in_flight:
                    return False
                c.half_open_probe_in_flight = True
                self._publish(c)
                return True
            return False

    def success(self, dependency: str) -> None:
        c = self.circuit(dependency)
        with c.lock:
            c.state = "closed"
            c.consecutive_failures = 0
            c.opened_monotonic = None
            c.last_success_at = _iso_now()
            c.last_failure_kind = None
            c.half_open_probe_in_flight = False
            self._publish(c)

    def failure(self, dependency: str, exc: BaseException | None = None) -> None:
        cfg = get_settings()
        c = self.circuit(dependency)
        with c.lock:
            c.consecutive_failures += 1
            c.last_failure_at = _iso_now()
            c.last_failure_kind = type(exc).__name__ if exc is not None else "DependencyFailure"
            threshold = max(1, int(cfg.resilience_failure_threshold))
            should_open = c.state == "half_open" or c.consecutive_failures >= threshold
            if should_open:
                was_open = c.state == "open"
                c.state = "open"
                c.opened_monotonic = time.monotonic()
                c.half_open_probe_in_flight = False
                if not was_open:
                    CIRCUIT_TRIPS.labels(dependency).inc()
            self._publish(c)

    def reset(self, dependency: str) -> None:
        c = self.circuit(dependency)
        with c.lock:
            c.state = "closed"
            c.consecutive_failures = 0
            c.opened_monotonic = None
            c.last_success_at = None
            c.last_failure_at = None
            c.last_failure_kind = None
            c.half_open_probe_in_flight = False
            self._publish(c)

    def _publish(self, c: Circuit) -> None:
        CIRCUIT_STATE.labels(c.dependency).set(STATE_VALUE[c.state])
        CIRCUIT_FAILURES.labels(c.dependency).set(c.consecutive_failures)

    def snapshot(self) -> dict:
        cfg = get_settings()
        names = sorted(set(self._circuits) | set(OPTIONAL_DEPENDENCIES) | {"redis"})
        circuits = {name: self.circuit(name).snapshot() for name in names}
        optional_open = sorted(name for name in OPTIONAL_DEPENDENCIES if circuits[name]["state"] == "open")
        brownout = bool(optional_open)
        BROWNOUT.set(1 if brownout else 0)
        return {
            "enabled": bool(cfg.resilience_enabled),
            "mode": "BROWNOUT" if brownout else "NORMAL",
            "optional_dependencies_open": optional_open,
            "circuits": circuits,
            "policy": {
                "postgresql_authoritative": True,
                "evidence_storage_authoritative": True,
                "breaker_state_authoritative": False,
                "optional_failure_blocks_engineering_core": False,
                "ai_failure_allows_evidence_only_answer": True,
                "qdrant_failure_allows_lexical_fallback": True,
                "cad_failure_does_not_disable_documents_bom_wi": True,
            },
        }


REGISTRY = ResilienceRegistry()


def circuit_allows(dependency: str) -> bool:
    return REGISTRY.allows(dependency)


def record_success(dependency: str) -> None:
    REGISTRY.success(dependency)


def record_failure(dependency: str, exc: BaseException | None = None) -> None:
    REGISTRY.failure(dependency, exc)


def reset_circuit(dependency: str) -> None:
    REGISTRY.reset(dependency)


def resilience_snapshot() -> dict:
    return REGISTRY.snapshot()


def capability_available(capability: str) -> bool:
    dep = CAPABILITY_DEPENDENCY.get(capability.strip().lower())
    return True if dep is None else circuit_allows(dep)


@contextmanager
def protected_dependency(dependency: str) -> Iterator[None]:
    if not circuit_allows(dependency):
        raise CircuitOpenError(dependency)
    try:
        yield
    except Exception as exc:
        record_failure(dependency, exc)
        raise
    else:
        record_success(dependency)
