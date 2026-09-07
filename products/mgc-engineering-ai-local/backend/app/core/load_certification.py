from __future__ import annotations

import copy
import hashlib
import json
import math
from dataclasses import asdict, dataclass
from typing import Any, Iterable

LOAD_EVIDENCE_SCHEMA = "mgc-production-load-evidence-v1"
LOAD_PLAN_SCHEMA = "mgc-production-load-plan-v1"
CANONICALIZATION = "mgc-json-sorted-utf8-v1"
REQUIRED_WORKLOAD_OPERATIONS = ("object_360", "bom_versions", "work_instructions", "rag_search", "rag_ask")


@dataclass(frozen=True)
class LoadProfile:
    code: str
    named_users: int
    concurrency: int
    min_requests: int
    warmup_requests: int
    p95_ms: float
    error_rate_max: float
    db_pool_hard_ratio: float
    queue_oldest_age_max_seconds: float


LOAD_PROFILES: dict[str, LoadProfile] = {
    "15": LoadProfile("15", 15, 15, 1_000, 50, 500.0, 0.010, 0.95, 300.0),
    "30": LoadProfile("30", 30, 30, 5_000, 100, 500.0, 0.010, 0.95, 180.0),
    "100": LoadProfile("100", 100, 100, 10_000, 200, 750.0, 0.005, 0.90, 120.0),
}


@dataclass(frozen=True)
class WorkloadOperation:
    code: str
    weight: int
    method: str
    path_template: str
    audited_read_semantics: bool = False


DEFAULT_WORKLOAD: tuple[WorkloadOperation, ...] = (
    WorkloadOperation("object_360", 25, "GET", "/api/v1/parts/{part_number}"),
    WorkloadOperation("bom_versions", 20, "GET", "/api/v1/projects/{project_code}/bom-versions?parent_part_number={part_number}"),
    WorkloadOperation("work_instructions", 20, "GET", "/api/v1/projects/{project_code}/work-instructions"),
    WorkloadOperation("digital_thread", 15, "GET", "/api/v1/projects/{project_code}/digital-thread?focus_part={part_number}&depth=2&max_nodes=120"),
    WorkloadOperation("rag_search", 12, "POST", "/api/v1/search", True),
    WorkloadOperation("rag_ask", 8, "POST", "/api/v1/ask", True),
)


def normalize_load_profile(value: str | int | None) -> str:
    raw = str(value or "30").strip().lower()
    aliases = {"pilot_15": "15", "pilot_30": "30", "enterprise_100": "100"}
    raw = aliases.get(raw, raw)
    if raw not in LOAD_PROFILES:
        raise ValueError("Unsupported load profile; expected 15, 30 or 100")
    return raw


def workload_contract() -> dict[str, Any]:
    return {
        "schema": LOAD_PLAN_SCHEMA,
        "operations": [asdict(x) for x in DEFAULT_WORKLOAD],
        "required_operations": list(REQUIRED_WORKLOAD_OPERATIONS),
        "governance": {
            "engineering_state_mutation_allowed": False,
            "audited_read_semantics_require_explicit_opt_in": True,
            "non_idempotent_business_write_replay_allowed": False,
        },
    }


def percentile(values: Iterable[float], pct: float) -> float | None:
    vals = sorted(float(x) for x in values)
    if not vals:
        return None
    if len(vals) == 1:
        return vals[0]
    rank = (len(vals) - 1) * float(pct) / 100.0
    low = math.floor(rank)
    high = math.ceil(rank)
    if low == high:
        return vals[low]
    frac = rank - low
    return vals[low] * (1.0 - frac) + vals[high] * frac


def _round_ms(value: float | None) -> float | None:
    return round(float(value), 3) if value is not None else None


def summarize_request_records(records: list[dict[str, Any]], *, wall_seconds: float, profile: str | int) -> dict[str, Any]:
    code = normalize_load_profile(profile)
    p = LOAD_PROFILES[code]
    total = len(records)
    errors = sum(1 for r in records if not bool(r.get("ok")))
    all_lat = [float(r.get("latency_ms") or 0.0) for r in records]
    error_rate = (errors / total) if total else 1.0
    allowed_errors = total * p.error_rate_max
    burn = (errors / allowed_errors) if allowed_errors > 0 else (0.0 if errors == 0 else math.inf)
    remaining = max(0.0, 1.0 - burn) if math.isfinite(burn) else 0.0
    by_op: dict[str, dict[str, Any]] = {}
    for op in sorted({str(r.get("operation") or "unknown") for r in records}):
        subset = [r for r in records if str(r.get("operation") or "unknown") == op]
        lat = [float(r.get("latency_ms") or 0.0) for r in subset]
        op_errors = sum(1 for r in subset if not bool(r.get("ok")))
        statuses: dict[str, int] = {}
        for r in subset:
            key = str(r.get("status") if r.get("status") is not None else "transport_error")
            statuses[key] = statuses.get(key, 0) + 1
        by_op[op] = {
            "requests": len(subset),
            "errors": op_errors,
            "error_rate": round(op_errors / len(subset), 6) if subset else None,
            "p50_ms": _round_ms(percentile(lat, 50)),
            "p95_ms": _round_ms(percentile(lat, 95)),
            "p99_ms": _round_ms(percentile(lat, 99)),
            "max_ms": _round_ms(max(lat) if lat else None),
            "statuses": statuses,
        }
    return {
        "requests": total,
        "errors": errors,
        "error_rate": round(error_rate, 6),
        "p50_ms": _round_ms(percentile(all_lat, 50)),
        "p95_ms": _round_ms(percentile(all_lat, 95)),
        "p99_ms": _round_ms(percentile(all_lat, 99)),
        "max_ms": _round_ms(max(all_lat) if all_lat else None),
        "wall_seconds": round(max(float(wall_seconds), 0.0), 3),
        "requests_per_second": round(total / max(float(wall_seconds), 0.001), 3),
        "error_budget": {
            "allowed_errors": round(allowed_errors, 3),
            "consumed_ratio": round(burn, 4) if math.isfinite(burn) else None,
            "remaining_ratio": round(remaining, 4),
            "status": "PASS" if error_rate <= p.error_rate_max else "BURNING",
        },
        "operations": by_op,
    }


def summarize_saturation(samples: list[dict[str, Any]]) -> dict[str, Any]:
    pool_ratios: list[float] = []
    queue_depths: list[int] = []
    oldest_ages: list[float] = []
    dlq: list[int] = []
    orphaned: list[int] = []
    expired: list[int] = []
    for item in samples:
        pool = ((item.get("production_certification") or {}).get("database_pool") or {})
        ratio = pool.get("saturation_ratio")
        if ratio is not None:
            try: pool_ratios.append(float(ratio))
            except (TypeError, ValueError): pass
        queue = item.get("queue") or {}
        age = queue.get("oldest_job_age_seconds")
        if age is not None:
            try: oldest_ages.append(float(age))
            except (TypeError, ValueError): pass
        for q in queue.get("queues") or []:
            depth = q.get("depth")
            if depth is not None:
                try: queue_depths.append(int(depth))
                except (TypeError, ValueError): pass
        workload = item.get("workload") or {}
        for key, target in (("dead_letter_jobs", dlq), ("orphaned_jobs", orphaned), ("expired_running_leases", expired)):
            try: target.append(int(workload.get(key) or 0))
            except (TypeError, ValueError): pass
    return {
        "samples": len(samples),
        "db_pool": {"max_saturation_ratio": round(max(pool_ratios), 4) if pool_ratios else None},
        "queue": {
            "max_depth": max(queue_depths) if queue_depths else None,
            "max_oldest_job_age_seconds": round(max(oldest_ages), 3) if oldest_ages else None,
        },
        "workload": {
            "max_dead_letter_jobs": max(dlq) if dlq else None,
            "max_orphaned_jobs": max(orphaned) if orphaned else None,
            "max_expired_running_leases": max(expired) if expired else None,
        },
    }


def canonical_payload_bytes(evidence: dict[str, Any]) -> bytes:
    payload = copy.deepcopy(evidence)
    payload.pop("integrity", None)
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")


def canonical_sha256(evidence: dict[str, Any]) -> str:
    return hashlib.sha256(canonical_payload_bytes(evidence)).hexdigest()


def attach_integrity(evidence: dict[str, Any], *, detached_signature_verified: bool = False, signature_algorithm: str | None = None) -> dict[str, Any]:
    out = copy.deepcopy(evidence)
    out["integrity"] = {
        "canonicalization": CANONICALIZATION,
        "canonical_sha256": canonical_sha256(out),
        "detached_signature_verified": bool(detached_signature_verified),
        "signature_algorithm": signature_algorithm,
        "signing_contract": "Sign canonical payload bytes (evidence with integrity removed); retain detached signature and public key with acceptance records.",
    }
    return out


def validate_integrity(evidence: dict[str, Any]) -> tuple[bool | None, str | None, str | None]:
    integrity = evidence.get("integrity") or {}
    claimed = integrity.get("canonical_sha256")
    if not claimed:
        return None, None, canonical_sha256(evidence)
    actual = canonical_sha256(evidence)
    return str(claimed).lower() == actual.lower(), str(claimed), actual


def load_acceptance_checks(evidence: dict[str, Any] | None, *, profile: str | int) -> list[dict[str, Any]]:
    code = normalize_load_profile(profile)
    p = LOAD_PROFILES[code]
    if not evidence:
        return [{"code": "LOAD_EVIDENCE", "status": "NO_DATA", "actual": None, "expected": LOAD_EVIDENCE_SCHEMA}]

    def check(name: str, ok: bool | None, actual: Any, expected: Any) -> dict[str, Any]:
        return {"code": name, "status": "PASS" if ok is True else ("FAIL" if ok is False else "NO_DATA"), "actual": actual, "expected": expected}

    summary = evidence.get("summary") or {}
    saturation = evidence.get("saturation") or {}
    governance = evidence.get("governance") or {}
    operations = summary.get("operations") or {}
    integrity_ok, claimed, actual_digest = validate_integrity(evidence)
    checks = [
        check("LOAD_EVIDENCE_SCHEMA", evidence.get("schema") == LOAD_EVIDENCE_SCHEMA, evidence.get("schema"), LOAD_EVIDENCE_SCHEMA),
        check("LOAD_PROFILE", str(evidence.get("profile")) == code, evidence.get("profile"), code),
        check("LOAD_LIVE_TARGET", governance.get("live_target_measurement") is True, governance.get("live_target_measurement"), True),
        check("LOAD_NOT_SYNTHETIC", governance.get("synthetic") is False, governance.get("synthetic"), False),
        check("LOAD_ENGINEERING_MUTATION_DISABLED", governance.get("engineering_state_mutation_allowed") is False, governance.get("engineering_state_mutation_allowed"), False),
        check("LOAD_CANONICAL_DIGEST", integrity_ok, claimed, actual_digest),
        check(
            "LOAD_DETACHED_SIGNATURE",
            True if (evidence.get("integrity") or {}).get("detached_signature_verified") is True else (False if (evidence.get("integrity") or {}).get("signature_verification_failed") is True else None),
            (evidence.get("integrity") or {}).get("detached_signature_verified"),
            True,
        ),
    ]
    for op in REQUIRED_WORKLOAD_OPERATIONS:
        requests = (operations.get(op) or {}).get("requests")
        checks.append(check(f"LOAD_COVERAGE_{op.upper()}", None if requests is None else int(requests) > 0, requests, ">0"))

    def numeric(name: str, value: Any, predicate, expected: Any):
        if value is None:
            checks.append(check(name, None, None, expected)); return
        try: val = float(value)
        except (TypeError, ValueError): checks.append(check(name, False, value, expected)); return
        checks.append(check(name, bool(predicate(val)), value, expected))

    numeric("LOAD_REQUEST_VOLUME", summary.get("requests"), lambda v: v >= p.min_requests, f">={p.min_requests}")
    numeric("LOAD_P95", summary.get("p95_ms"), lambda v: v <= p.p95_ms, f"<={p.p95_ms}ms")
    numeric("LOAD_ERROR_RATE", summary.get("error_rate"), lambda v: v <= p.error_rate_max, f"<={p.error_rate_max}")
    numeric("LOAD_ERROR_BUDGET_BURN", (summary.get("error_budget") or {}).get("consumed_ratio"), lambda v: v <= 1.0, "<=1.0")
    numeric("LOAD_DB_POOL_SATURATION", ((saturation.get("db_pool") or {}).get("max_saturation_ratio")), lambda v: v < p.db_pool_hard_ratio, f"<{p.db_pool_hard_ratio}")
    numeric("LOAD_QUEUE_OLDEST_AGE", ((saturation.get("queue") or {}).get("max_oldest_job_age_seconds")), lambda v: v <= p.queue_oldest_age_max_seconds, f"<={p.queue_oldest_age_max_seconds}s")
    for name, key in (("LOAD_DLQ", "max_dead_letter_jobs"), ("LOAD_ORPHANED", "max_orphaned_jobs"), ("LOAD_EXPIRED_LEASES", "max_expired_running_leases")):
        value = (saturation.get("workload") or {}).get(key)
        checks.append(check(name, None if value is None else int(value) == 0, value, 0))
    return checks


def load_decision(evidence: dict[str, Any] | None, *, profile: str | int) -> dict[str, Any]:
    checks = load_acceptance_checks(evidence, profile=profile)
    missing = [x["code"] for x in checks if x["status"] == "NO_DATA"]
    failed = [x["code"] for x in checks if x["status"] == "FAIL"]
    decision = "GO" if not missing and not failed else ("NO_GO" if failed else "CONDITIONAL")
    return {"decision": decision, "checks": checks, "failed_checks": failed, "missing_checks": missing}
