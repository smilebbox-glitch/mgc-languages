from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Iterable

PERFORMANCE_SCHEMA = "mgc-performance-certification-v1"


@dataclass(frozen=True)
class PerformanceProfile:
    name: str
    parts: int
    bom_edges: int
    vins: int
    genealogy_rows: int
    quality_observations: int
    concurrent_users: int
    api_p95_ms: float
    reconciliation_p95_ms: float
    error_rate_max: float


PROFILES: dict[str, PerformanceProfile] = {
    "ci": PerformanceProfile("ci", 5_000, 25_000, 2_000, 20_000, 50_000, 4, 750.0, 5_000.0, 0.01),
    "pilot": PerformanceProfile("pilot", 100_000, 1_000_000, 100_000, 2_000_000, 2_000_000, 25, 500.0, 10_000.0, 0.01),
    "enterprise": PerformanceProfile("enterprise", 250_000, 5_000_000, 500_000, 10_000_000, 10_000_000, 75, 750.0, 20_000.0, 0.01),
}



def percentile(values: Iterable[float], p: float) -> float | None:
    data = sorted(float(x) for x in values)
    if not data:
        return None
    if p <= 0:
        return data[0]
    if p >= 100:
        return data[-1]
    rank = (len(data) - 1) * (p / 100.0)
    lo = math.floor(rank)
    hi = math.ceil(rank)
    if lo == hi:
        return data[lo]
    weight = rank - lo
    return data[lo] * (1.0 - weight) + data[hi] * weight


def summarize_latencies(latencies_ms: Iterable[float], *, errors: int = 0, total_requests: int | None = None) -> dict:
    data = [float(x) for x in latencies_ms]
    total = int(total_requests if total_requests is not None else len(data) + errors)
    return {
        "requests": total,
        "successful": len(data),
        "errors": int(errors),
        "error_rate": round((errors / total) if total else 0.0, 6),
        "p50_ms": round(percentile(data, 50) or 0.0, 3),
        "p95_ms": round(percentile(data, 95) or 0.0, 3),
        "p99_ms": round(percentile(data, 99) or 0.0, 3),
        "max_ms": round(max(data), 3) if data else None,
    }


def evaluate_http_result(summary: dict, profile: PerformanceProfile) -> dict:
    checks = [
        {
            "code": "HTTP_P95",
            "pass": float(summary.get("p95_ms") or 0.0) <= profile.api_p95_ms,
            "actual": summary.get("p95_ms"),
            "expected": f"<={profile.api_p95_ms:.0f}ms",
        },
        {
            "code": "HTTP_ERROR_RATE",
            "pass": float(summary.get("error_rate") or 0.0) <= profile.error_rate_max,
            "actual": summary.get("error_rate"),
            "expected": f"<={profile.error_rate_max:.2%}",
        },
    ]
    return {"status": "PASS" if all(x["pass"] for x in checks) else "FAIL", "checks": checks}


def evaluate_reconciliation_latency(latency_ms: float, profile: PerformanceProfile) -> dict:
    ok = float(latency_ms) <= profile.reconciliation_p95_ms
    return {
        "status": "PASS" if ok else "FAIL",
        "checks": [{
            "code": "RECONCILIATION_LATENCY",
            "pass": ok,
            "actual": round(float(latency_ms), 3),
            "expected": f"<={profile.reconciliation_p95_ms:.0f}ms",
        }],
    }


def capacity_envelope(*, logical_cpus: int, ram_gib: float | None, profile: str) -> dict:
    p = PROFILES[profile]
    ram = float(ram_gib) if ram_gib is not None else None
    if logical_cpus < 8 or (ram is not None and ram < 16):
        host_class = "developer"
        max_users = min(p.concurrent_users, 5)
        note = "Suitable for engineering evaluation/CI only; not a production pilot capacity claim."
    elif logical_cpus < 24 or (ram is not None and ram < 48):
        host_class = "pilot-cpu"
        max_users = min(p.concurrent_users, 20)
        note = "Candidate CPU pilot host. Run live HTTP/DB benchmarks before go-live."
    else:
        host_class = "production-candidate"
        max_users = p.concurrent_users
        note = "Capacity candidate only; certification still requires real PostgreSQL/Qdrant/Redis measurements."
    return {
        "schema": PERFORMANCE_SCHEMA,
        "profile": profile,
        "host_class": host_class,
        "logical_cpus": int(logical_cpus),
        "ram_gib": round(ram, 1) if ram is not None else None,
        "recommended_max_concurrent_users_before_live_test": int(max_users),
        "dataset_target": {
            "parts": p.parts,
            "bom_edges": p.bom_edges,
            "vins": p.vins,
            "genealogy_rows": p.genealogy_rows,
            "quality_observations": p.quality_observations,
        },
        "note": note,
    }
