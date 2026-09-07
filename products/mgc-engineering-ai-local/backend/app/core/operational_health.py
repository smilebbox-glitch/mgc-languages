from __future__ import annotations

import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from prometheus_client import Gauge
from sqlalchemy import text

from app.core.config import get_settings
from app.core.runtime_contract import APP_VERSION, SCHEMA_VERSION
from app.db.session import engine, SessionLocal
from app.services.projection_outbox import projection_health
from app.core.resilience import record_failure, record_success, resilience_snapshot
from app.core.deployment_safety import deployment_safety_snapshot
from app.core.authoritative_ha import authoritative_ha_snapshot

EXPECTED_SCHEMA_VERSION = SCHEMA_VERSION

READINESS = Gauge("mgc_operational_readiness", "1 when all required MGC readiness checks pass")
DEPENDENCY_UP = Gauge("mgc_dependency_up", "Dependency health state (1/0)", ["dependency"])
DEPENDENCY_LATENCY_MS = Gauge("mgc_dependency_check_latency_ms", "Dependency check latency in milliseconds", ["dependency"])


@dataclass(frozen=True)
class Check:
    name: str
    required: bool
    ok: bool
    latency_ms: float
    detail: str

    def public(self) -> dict:
        # Never expose endpoint URLs, credentials, database names, host paths or exception text.
        return {
            "name": self.name,
            "required": self.required,
            "status": "ok" if self.ok else "failed",
            "latency_ms": round(self.latency_ms, 1),
            "detail": self.detail,
        }


def _run(name: str, required: bool, fn: Callable[[], None]) -> Check:
    started = time.perf_counter()
    ok = True
    detail = "available"
    try:
        fn()
        record_success(name)
    except Exception as exc:
        ok = False
        detail = "unavailable"
        record_failure(name, exc)
    latency = (time.perf_counter() - started) * 1000.0
    DEPENDENCY_UP.labels(name).set(1 if ok else 0)
    DEPENDENCY_LATENCY_MS.labels(name).set(latency)
    return Check(name, required, ok, latency, detail)


def _database() -> None:
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
        actual = conn.execute(text("SELECT schema_version FROM mgc_schema_state WHERE id=1")).scalar_one()
    if actual != EXPECTED_SCHEMA_VERSION:
        raise RuntimeError("schema version mismatch")


def _storage() -> None:
    cfg = get_settings()
    path = Path(cfg.storage_dir)
    if not path.is_dir() or not os.access(path, os.R_OK | os.W_OK | os.X_OK):
        raise RuntimeError("storage path is not read/write accessible")


def _redis() -> None:
    import redis
    cfg = get_settings()
    client = redis.Redis.from_url(
        cfg.redis_url,
        socket_connect_timeout=cfg.health_timeout_seconds,
        socket_timeout=cfg.health_timeout_seconds,
    )
    if client.ping() is not True:
        raise RuntimeError("redis ping failed")


def _qdrant() -> None:
    from app.adapters.health import probe_qdrant
    probe_qdrant()


def _neo4j() -> None:
    from app.adapters.health import probe_neo4j
    probe_neo4j()


def _minio() -> None:
    from app.adapters.health import probe_object_store
    probe_object_store()


def readiness_snapshot() -> dict:
    cfg = get_settings()
    qdrant_configured = getattr(cfg, "runtime_qdrant_required", getattr(cfg, "readiness_require_qdrant", True))
    graph_configured = getattr(cfg, "runtime_graph_enabled", getattr(cfg, "graph_enabled", False))
    object_store_configured = getattr(cfg, "runtime_object_store_enabled", getattr(cfg, "object_store_enabled", False))
    runtime_profile = getattr(cfg, "runtime_profile", "legacy")
    strict_optional = bool(getattr(cfg, "resilience_strict_dependency_readiness", True))
    checks = [
        _run("database_schema", True, _database),
        _run("evidence_storage", True, _storage),
        _run("redis", bool(cfg.readiness_require_redis and strict_optional), _redis),
        _run("qdrant", bool(qdrant_configured and strict_optional), _qdrant),
    ]
    if graph_configured:
        checks.append(_run("neo4j", strict_optional, _neo4j))
    if object_store_configured:
        checks.append(_run("object_store", strict_optional, _minio))

    authoritative_ha = authoritative_ha_snapshot()
    if authoritative_ha.get("enabled"):
        authority_ok = bool(authoritative_ha.get("write_safe"))
        checks.append(Check(
            "authoritative_data_ha", True, authority_ok, 0.0,
            "write_authority_confirmed" if authority_ok else "authoritative_write_fenced",
        ))

    deployment = deployment_safety_snapshot(touch_api=True)
    if deployment.get("registry_status") == "available":
        skew_ok = int(deployment.get("incompatible_components") or 0) == 0
        checks.append(Check(
            "deployment_version_skew", True, skew_ok, 0.0,
            "compatible" if skew_ok else "incompatible_runtime_detected",
        ))
    else:
        # Redis/component-registry loss does not block deterministic Core. Known skew does.
        checks.append(Check("deployment_version_skew", False, True, 0.0, "registry_unavailable"))

    ready = all(c.ok for c in checks if c.required)
    READINESS.set(1 if ready else 0)
    try:
        with SessionLocal() as projection_db:
            projection = projection_health(projection_db)
    except Exception:
        # Readiness can be evaluated during schema bootstrap/legacy migration tests before
        # v6.3.2 tables exist. Projection telemetry is explicitly non-gating.
        projection = {
            "status": "unavailable", "backlog": None, "dead_letter": None,
            "policy": {"postgresql_authoritative": True, "optional_projection_failure_blocks_core": False},
        }
    return {
        "status": "ready" if ready else "not_ready",
        "service": cfg.app_name,
        "version": APP_VERSION,
        "air_gapped_mode": cfg.air_gapped_mode,
        "checks": [c.public() for c in checks],
        "projection_pipeline": projection,
        "resilience": resilience_snapshot(),
        "deployment_safety": deployment,
        "authoritative_data_ha": authoritative_ha,
        "policy": {
            "local_ai_is_readiness_gate": False,
            "deployment_profile": runtime_profile,
            "qdrant_required": bool(qdrant_configured and strict_optional),
            "neo4j_projection_required": bool(graph_configured and strict_optional),
            "strict_optional_dependency_readiness": strict_optional,
            "known_runtime_version_skew_blocks_core": True,
            "component_registry_outage_blocks_core": False,
            "unsafe_database_or_evidence_authority_blocks_core": True,
            "reason": "PostgreSQL and evidence storage gate Core; when authoritative HA is enabled, writes are exposed only from a proven PostgreSQL primary plus active evidence generation",
        },
    }
