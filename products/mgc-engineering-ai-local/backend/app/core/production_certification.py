from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from prometheus_client import Gauge
from sqlalchemy import select
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session

from app.core.authoritative_ha import authoritative_ha_snapshot
from app.core.config import get_settings
from app.core.multi_host_topology import multi_host_topology_snapshot
from app.db.models import OperationalHealthSample, ProductionIncident
from app.db.session import engine
from app.services.performance_governance import performance_governance_snapshot
from app.core.load_certification import LOAD_EVIDENCE_SCHEMA, load_acceptance_checks

CERTIFICATION_SCHEMA = "mgc-production-certification-v1"
EVIDENCE_SCHEMA = "mgc-production-acceptance-evidence-v1"

CERT_DECISION = Gauge("mgc_production_certification_decision", "Production certification decision: GO=1, CONDITIONAL=0.5, NO_GO=0", ["profile"])
DB_POOL_SATURATION = Gauge("mgc_db_pool_saturation_ratio", "Current SQLAlchemy DB pool checked-out ratio")
DB_POOL_ADMISSION = Gauge("mgc_db_pool_admission_open", "1 when new mutating HTTP work may be admitted")


@dataclass(frozen=True)
class CertificationProfile:
    code: str
    named_users: int
    target_concurrent_users: int
    min_failure_domains: int
    min_api_failure_domains: int
    min_worker_failure_domains: int
    dependency_availability_target: float
    api_p95_ms: float
    error_rate_max: float
    min_http_requests: int
    pool_warn_ratio: float
    pool_hard_ratio: float
    rto_seconds: int
    rpo_seconds: int


PROFILES: dict[str, CertificationProfile] = {
    "15": CertificationProfile("15", 15, 5, 2, 2, 2, 0.995, 500.0, 0.010, 1_000, 0.80, 0.95, 300, 300),
    "30": CertificationProfile("30", 30, 10, 2, 2, 2, 0.997, 500.0, 0.010, 5_000, 0.80, 0.95, 180, 120),
    "100": CertificationProfile("100", 100, 30, 3, 3, 2, 0.999, 750.0, 0.005, 10_000, 0.75, 0.90, 120, 60),
}


def normalize_profile(value: str | int | None) -> str:
    raw = str(value or "30").strip().lower()
    aliases = {"pilot_15": "15", "pilot_30": "30", "enterprise_100": "100"}
    raw = aliases.get(raw, raw)
    if raw not in PROFILES:
        raise ValueError("Unsupported certification profile; expected 15, 30 or 100")
    return raw


def profile_contract(profile: str | int | None) -> dict[str, Any]:
    return asdict(PROFILES[normalize_profile(profile)])


def _pool_numbers() -> tuple[int | None, int | None, int | None, int | None]:
    pool = engine.pool
    def safe(name: str) -> int | None:
        fn = getattr(pool, name, None)
        try:
            return int(fn()) if callable(fn) else None
        except Exception:
            return None
    max_overflow = getattr(pool, "_max_overflow", None)
    try:
        max_overflow = int(max_overflow) if max_overflow is not None else None
    except Exception:
        max_overflow = None
    return safe("size"), safe("checkedout"), safe("overflow"), max_overflow


def db_pool_capacity_snapshot(*, profile: str | int | None = None) -> dict[str, Any]:
    cfg = get_settings()
    p = PROFILES[normalize_profile(profile or getattr(cfg, "production_certification_profile", "30"))]
    size, checked, overflow, actual_max_overflow = _pool_numbers()
    # SQLAlchemy QueuePool capacity includes max_overflow; prefer the actual pool contract.
    max_overflow = max(0, int(actual_max_overflow if actual_max_overflow is not None else getattr(cfg, "db_max_overflow", 0)))
    capacity = (size + max_overflow) if size is not None else None
    ratio = (float(checked) / float(capacity)) if capacity and checked is not None else None
    warn = min(max(float(getattr(cfg, "db_pool_saturation_warn_ratio", p.pool_warn_ratio)), 0.01), 1.0)
    hard = min(max(float(getattr(cfg, "db_pool_saturation_hard_ratio", p.pool_hard_ratio)), warn), 1.0)
    if ratio is None:
        state = "UNKNOWN"
        admission_open = True
    elif ratio >= hard:
        state = "CRITICAL"
        admission_open = False
    elif ratio >= warn:
        state = "WARN"
        admission_open = True
    else:
        state = "OK"
        admission_open = True
    DB_POOL_SATURATION.set(float(ratio or 0.0))
    DB_POOL_ADMISSION.set(1 if admission_open else 0)
    return {
        "schema": "mgc-db-pool-capacity-v1",
        "profile": p.code,
        "size": size,
        "max_overflow": max_overflow,
        "observed_overflow": overflow,
        "checked_out": checked,
        "effective_capacity": capacity,
        "saturation_ratio": round(ratio, 4) if ratio is not None else None,
        "warn_ratio": warn,
        "hard_ratio": hard,
        "status": state,
        "admission_open": admission_open,
        "policy": {"read_traffic_fenced_on_saturation": False, "new_mutating_http_fenced_at_hard_ratio": True},
    }


def _check(code: str, ok: bool | None, actual: Any, expected: Any, *, required: bool = True) -> dict[str, Any]:
    status = "PASS" if ok is True else ("FAIL" if ok is False else "NO_DATA")
    return {"code": code, "status": status, "required": required, "actual": actual, "expected": expected}


def _runtime_dependency_slo(db: Session, p: CertificationProfile) -> dict[str, Any]:
    cfg = get_settings()
    now = datetime.now(timezone.utc)
    minutes = max(1, min(int(getattr(cfg, "operations_default_window_minutes", 60)), 60 * 24 * 30))
    since = now - timedelta(minutes=minutes)
    rows = db.scalars(select(OperationalHealthSample).where(
        OperationalHealthSample.captured_at >= since,
        OperationalHealthSample.required == True,  # noqa: E712
    )).all()
    total = len(rows)
    good = sum(1 for r in rows if r.status == "ok")
    observed = (good / total) if total else None
    allowed_bad = total * (1.0 - p.dependency_availability_target)
    bad = total - good
    if not total:
        remaining = None
    elif allowed_bad <= 0:
        remaining = 1.0 if bad == 0 else 0.0
    else:
        remaining = max(0.0, 1.0 - (bad / allowed_bad))
    return {
        "window_minutes": minutes,
        "samples": total,
        "availability": round(observed, 6) if observed is not None else None,
        "target": p.dependency_availability_target,
        "error_budget_remaining_ratio": round(remaining, 4) if remaining is not None else None,
        "status": "NO_DATA" if observed is None else ("PASS" if observed >= p.dependency_availability_target else "BURNING"),
    }


def runtime_acceptance_snapshot(db: Session, *, profile: str | int | None = None) -> dict[str, Any]:
    p = PROFILES[normalize_profile(profile or getattr(get_settings(), "production_certification_profile", "30"))]
    topology = multi_host_topology_snapshot()
    authority = authoritative_ha_snapshot()
    perf = performance_governance_snapshot(engine)
    pool = db_pool_capacity_snapshot(profile=p.code)
    dependency_slo = _runtime_dependency_slo(db, p)
    critical_incidents = db.scalars(select(ProductionIncident).where(ProductionIncident.status != "resolved", ProductionIncident.severity == "critical")).all()
    checks = [
        _check("TOPOLOGY_HEALTHY", topology.get("status") == "HEALTHY", topology.get("status"), "HEALTHY"),
        _check("FAILURE_DOMAIN_CAPACITY", int(topology.get("failure_domain_count") or 0) >= p.min_failure_domains, topology.get("failure_domain_count"), f">={p.min_failure_domains}"),
        _check("API_FAILURE_DOMAIN_CAPACITY", int(topology.get("api_failure_domain_count") or 0) >= p.min_api_failure_domains, topology.get("api_failure_domain_count"), f">={p.min_api_failure_domains}"),
        _check("AUTHORITATIVE_DATA_WRITE_SAFE", bool(authority.get("write_safe")), authority.get("status"), "write_safe=true"),
        _check("DB_POOL_HEADROOM", pool.get("status") != "CRITICAL", pool.get("saturation_ratio"), f"<{pool.get('hard_ratio')}"),
        _check("DEPENDENCY_SLO", None if dependency_slo.get("availability") is None else dependency_slo.get("status") == "PASS", dependency_slo.get("availability"), f">={p.dependency_availability_target}"),
        _check("NO_CRITICAL_INCIDENTS", len(critical_incidents) == 0, len(critical_incidents), 0),
    ]
    hard_fail = any(x["required"] and x["status"] == "FAIL" for x in checks)
    decision = "NO_GO" if hard_fail else "CONDITIONAL"
    CERT_DECISION.labels(p.code).set(0.0 if decision == "NO_GO" else 0.5)
    return {
        "schema": CERTIFICATION_SCHEMA,
        "profile": asdict(p),
        "decision": decision,
        "production_authorized": False,
        "human_approval_required": True,
        "checks": checks,
        "topology": topology,
        "authoritative_data_ha": authority,
        "database_pool": pool,
        "dependency_slo": dependency_slo,
        "database_performance": perf,
        "live_evidence": {"present": False, "reason": "Target-host load/failover evidence is not stored as authoritative application state."},
        "policy": {"slo_failure_blocks_new_rollout": True, "slo_failure_blocks_existing_lb_readiness": False, "packaging_environment_can_issue_go": False},
    }


def evaluate_target_host_evidence(*, profile: str | int, topology: dict[str, Any], evidence: dict[str, Any]) -> dict[str, Any]:
    p = PROFILES[normalize_profile(profile)]
    checks: list[dict[str, Any]] = []
    topo_nodes = topology.get("nodes") or []
    domains = {str(n.get("failure_domain") or "") for n in topo_nodes if str(n.get("failure_domain") or "")}
    api_domains = {str(n.get("failure_domain") or "") for n in topo_nodes if "api" in set(n.get("roles") or []) and str(n.get("failure_domain") or "")}
    checks += [
        _check("TOPOLOGY_SCHEMA", topology.get("schema") == "mgc-multihost-topology-v1", topology.get("schema"), "mgc-multihost-topology-v1"),
        _check("TOPOLOGY_PROFILE", str(topology.get("profile")) == p.code, topology.get("profile"), p.code),
        _check("FAILURE_DOMAINS", len(domains) >= p.min_failure_domains, len(domains), f">={p.min_failure_domains}"),
        _check("API_FAILURE_DOMAINS", len(api_domains) >= p.min_api_failure_domains, len(api_domains), f">={p.min_api_failure_domains}"),
    ]
    http = evidence.get("http") or {}
    dep = evidence.get("dependencies") or {}
    pool = evidence.get("database_pool") or {}
    dr = evidence.get("failover") or {}
    lb = evidence.get("external_load_balancer") or {}

    def numeric_check(code: str, obj: dict[str, Any], key: str, predicate, expected: Any):
        raw = obj.get(key)
        if raw is None:
            checks.append(_check(code, None, None, expected))
            return
        try:
            value = float(raw)
        except (TypeError, ValueError):
            checks.append(_check(code, False, raw, expected))
            return
        checks.append(_check(code, bool(predicate(value)), raw, expected))

    def boolean_check(code: str, obj: dict[str, Any], key: str, expected: bool = True):
        if key not in obj:
            checks.append(_check(code, None, None, expected))
        else:
            checks.append(_check(code, obj.get(key) is expected, obj.get(key), expected))

    checks.append(_check("EVIDENCE_SCHEMA", evidence.get("schema") == EVIDENCE_SCHEMA, evidence.get("schema"), EVIDENCE_SCHEMA))
    load_evidence = evidence.get("load_certification")
    for item in load_acceptance_checks(load_evidence if isinstance(load_evidence, dict) else None, profile=p.code):
        checks.append({"code": item["code"], "status": item["status"], "required": True, "actual": item.get("actual"), "expected": item.get("expected")})
    numeric_check("NAMED_USERS", evidence, "named_users", lambda v: v >= p.named_users, f">={p.named_users}")
    numeric_check("HTTP_REQUEST_VOLUME", http, "requests", lambda v: v >= p.min_http_requests, f">={p.min_http_requests}")
    numeric_check("HTTP_P95", http, "p95_ms", lambda v: v <= p.api_p95_ms, f"<={p.api_p95_ms}ms")
    numeric_check("HTTP_ERROR_RATE", http, "error_rate", lambda v: v <= p.error_rate_max, f"<={p.error_rate_max}")
    numeric_check("DEPENDENCY_AVAILABILITY", dep, "availability", lambda v: v >= p.dependency_availability_target, f">={p.dependency_availability_target}")
    numeric_check("DB_POOL_MAX_SATURATION", pool, "max_saturation_ratio", lambda v: v < p.pool_hard_ratio, f"<{p.pool_hard_ratio}")
    numeric_check("LB_CONSECUTIVE_PROBES", lb, "successful_probes", lambda v: v >= 20, ">=20")
    boolean_check("LB_NON_IDEMPOTENT_REPLAY", lb, "non_idempotent_replay_detected", False)
    boolean_check("HOST_LOSS_DRILL", dr, "host_loss_passed", True)
    boolean_check("AUTHORITATIVE_FAILOVER_DRILL", dr, "authoritative_failover_passed", True)
    boolean_check("EVIDENCE_FAILOVER_INTEGRITY", dr, "evidence_integrity_passed", True)
    numeric_check("RTO", dr, "rto_seconds", lambda v: v <= p.rto_seconds, f"<={p.rto_seconds}s")
    numeric_check("RPO", dr, "rpo_seconds", lambda v: v <= p.rpo_seconds, f"<={p.rpo_seconds}s")
    missing = [x["code"] for x in checks if x["status"] == "NO_DATA"]
    failed = [x["code"] for x in checks if x["status"] == "FAIL"]
    decision = "GO" if not missing and not failed else ("NO_GO" if failed else "CONDITIONAL")
    CERT_DECISION.labels(p.code).set(1.0 if decision == "GO" else (0.5 if decision == "CONDITIONAL" else 0.0))
    return {
        "schema": CERTIFICATION_SCHEMA,
        "profile": asdict(p),
        "decision": decision,
        "production_authorized": False,
        "human_approval_required": True,
        "checks": checks,
        "failed_checks": failed,
        "missing_checks": missing,
        "policy": {
            "go_means_technical_acceptance_not_business_authorization": True,
            "human_change_approval_required": True,
            "source_evidence_must_be_retained_by_operator": True,
            "packaging_synthetic_benchmark_is_not_live_capacity_evidence": True,
            "v6322_load_evidence_and_verified_detached_signature_required_for_go": True,
        },
    }
