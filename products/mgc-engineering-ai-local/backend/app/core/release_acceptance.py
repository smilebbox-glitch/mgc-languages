from __future__ import annotations

import copy
import hashlib
import json
from dataclasses import asdict, dataclass
from typing import Any

from app.core.runtime_contract import APP_VERSION, SCHEMA_VERSION

RELEASE_ACCEPTANCE_SCHEMA = "mgc-release-acceptance-evidence-v1"
APPROVED_BASELINE_SCHEMA = "mgc-approved-release-baseline-v1"
ACCEPTANCE_CHAIN_SCHEMA = "mgc-release-acceptance-chain-v1"
CANONICALIZATION = "mgc-json-sorted-utf8-v1"


@dataclass(frozen=True)
class RegressionPolicy:
    p95_max_ratio: float = 1.15
    p99_max_ratio: float = 1.20
    error_rate_max_absolute_increase: float = 0.002
    throughput_min_ratio: float = 0.90
    db_pool_max_absolute_increase: float = 0.10
    rto_max_ratio: float = 1.20
    rpo_max_ratio: float = 1.20


DEFAULT_REGRESSION_POLICY = RegressionPolicy()


def canonical_payload_bytes(document: dict[str, Any]) -> bytes:
    payload = copy.deepcopy(document)
    payload.pop("integrity", None)
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")


def canonical_sha256(document: dict[str, Any]) -> str:
    return hashlib.sha256(canonical_payload_bytes(document)).hexdigest()


def attach_integrity(document: dict[str, Any], *, detached_signature_verified: bool = False, signature_algorithm: str | None = None) -> dict[str, Any]:
    out = copy.deepcopy(document)
    out["integrity"] = {
        "canonicalization": CANONICALIZATION,
        "canonical_sha256": canonical_sha256(out),
        "detached_signature_verified": bool(detached_signature_verified),
        "signature_algorithm": signature_algorithm,
        "signing_contract": "Sign canonical payload bytes (document with integrity removed); retain detached signature and public key with acceptance records.",
    }
    return out


def validate_integrity(document: dict[str, Any]) -> tuple[bool | None, str | None, str]:
    integrity = document.get("integrity") or {}
    claimed = integrity.get("canonical_sha256")
    actual = canonical_sha256(document)
    if not claimed:
        return None, None, actual
    return str(claimed).lower() == actual.lower(), str(claimed), actual


def _version_tuple(value: str) -> tuple[int, int, int] | None:
    try:
        parts = [int(x) for x in str(value).split(".")]
        if len(parts) != 3:
            return None
        return parts[0], parts[1], parts[2]
    except Exception:
        return None


def _metric(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def extract_metrics(*, production_report: dict[str, Any], load_evidence: dict[str, Any], source_evidence: dict[str, Any]) -> dict[str, float | None]:
    summary = load_evidence.get("summary") or {}
    saturation = load_evidence.get("saturation") or {}
    failover = source_evidence.get("failover") or {}
    return {
        "p95_ms": _metric(summary.get("p95_ms")),
        "p99_ms": _metric(summary.get("p99_ms")),
        "error_rate": _metric(summary.get("error_rate")),
        "requests_per_second": _metric(summary.get("requests_per_second")),
        "db_pool_max_saturation_ratio": _metric(((saturation.get("db_pool") or {}).get("max_saturation_ratio"))),
        "rto_seconds": _metric(failover.get("rto_seconds")),
        "rpo_seconds": _metric(failover.get("rpo_seconds")),
    }


def _check(code: str, status: str, actual: Any, expected: Any) -> dict[str, Any]:
    return {"code": code, "status": status, "actual": actual, "expected": expected}


def _ratio_check(code: str, current: float | None, baseline: float | None, max_ratio: float) -> dict[str, Any]:
    if current is None or baseline is None:
        return _check(code, "NO_DATA", {"current": current, "baseline": baseline}, f"current/baseline <= {max_ratio}")
    if baseline <= 0:
        return _check(code, "PASS" if current <= baseline else "FAIL", {"current": current, "baseline": baseline, "ratio": None}, f"current <= {baseline}")
    ratio = current / baseline
    return _check(code, "PASS" if ratio <= max_ratio else "FAIL", {"current": current, "baseline": baseline, "ratio": round(ratio, 6)}, f"<= {max_ratio}")


def evaluate_regression(*, current_metrics: dict[str, Any], baseline: dict[str, Any] | None, profile: str, policy: RegressionPolicy = DEFAULT_REGRESSION_POLICY) -> dict[str, Any]:
    if not baseline:
        return {
            "decision": "CONDITIONAL",
            "checks": [_check("APPROVED_BASELINE", "NO_DATA", None, APPROVED_BASELINE_SCHEMA)],
            "failed_checks": [],
            "missing_checks": ["APPROVED_BASELINE"],
            "baseline_release": None,
            "policy": asdict(policy),
        }

    checks: list[dict[str, Any]] = []
    valid_integrity, claimed, actual = validate_integrity(baseline)
    current_v = _version_tuple(APP_VERSION)
    base_v = _version_tuple(str(baseline.get("release") or ""))
    checks += [
        _check("BASELINE_SCHEMA", "PASS" if baseline.get("schema") == APPROVED_BASELINE_SCHEMA else "FAIL", baseline.get("schema"), APPROVED_BASELINE_SCHEMA),
        _check("BASELINE_DIGEST", "PASS" if valid_integrity is True else ("FAIL" if valid_integrity is False else "NO_DATA"), claimed, actual),
        _check("BASELINE_SIGNATURE", "PASS" if (baseline.get("integrity") or {}).get("detached_signature_verified") is True else ("FAIL" if (baseline.get("integrity") or {}).get("signature_verification_failed") is True else "NO_DATA"), (baseline.get("integrity") or {}).get("detached_signature_verified"), True),
        _check("BASELINE_HUMAN_APPROVED", "PASS" if baseline.get("human_approved") is True else "FAIL", baseline.get("human_approved"), True),
        _check("BASELINE_TECHNICAL_GO", "PASS" if baseline.get("technical_decision") == "GO" else "FAIL", baseline.get("technical_decision"), "GO"),
        _check("BASELINE_PROFILE", "PASS" if str(baseline.get("profile")) == str(profile) else "FAIL", baseline.get("profile"), str(profile)),
        _check("BASELINE_SCHEMA_VERSION", "PASS" if baseline.get("schema_version") == SCHEMA_VERSION else "FAIL", baseline.get("schema_version"), SCHEMA_VERSION),
    ]
    if current_v and base_v:
        same_line = current_v[:2] == base_v[:2]
        older = base_v < current_v
        same_release_bootstrap = bool(baseline.get("bootstrap")) and base_v == current_v and int(baseline.get("source_chain_sequence") or 0) == 1
        release_order_ok = same_line and (older or same_release_bootstrap)
        checks.append(_check("BASELINE_RELEASE_ORDER", "PASS" if release_order_ok else "FAIL", baseline.get("release"), f"older than {APP_VERSION}, or same-release explicit sequence-1 bootstrap"))
    else:
        checks.append(_check("BASELINE_RELEASE_ORDER", "FAIL", baseline.get("release"), f"semantic version older than {APP_VERSION}, or explicit bootstrap"))
    approval_ref = ((baseline.get("approval") or {}).get("reference"))
    checks.append(_check("BASELINE_APPROVAL_REFERENCE", "PASS" if bool(str(approval_ref or "").strip()) else "FAIL", approval_ref, "non-empty change/approval reference"))

    bm = baseline.get("metrics") or {}
    checks += [
        _ratio_check("REGRESSION_P95", _metric(current_metrics.get("p95_ms")), _metric(bm.get("p95_ms")), policy.p95_max_ratio),
        _ratio_check("REGRESSION_P99", _metric(current_metrics.get("p99_ms")), _metric(bm.get("p99_ms")), policy.p99_max_ratio),
        _ratio_check("REGRESSION_RTO", _metric(current_metrics.get("rto_seconds")), _metric(bm.get("rto_seconds")), policy.rto_max_ratio),
        _ratio_check("REGRESSION_RPO", _metric(current_metrics.get("rpo_seconds")), _metric(bm.get("rpo_seconds")), policy.rpo_max_ratio),
    ]
    cur_err, base_err = _metric(current_metrics.get("error_rate")), _metric(bm.get("error_rate"))
    checks.append(_check("REGRESSION_ERROR_RATE", "NO_DATA" if cur_err is None or base_err is None else ("PASS" if cur_err - base_err <= policy.error_rate_max_absolute_increase else "FAIL"), {"current": cur_err, "baseline": base_err, "absolute_increase": None if cur_err is None or base_err is None else round(cur_err-base_err, 8)}, f"absolute increase <= {policy.error_rate_max_absolute_increase}"))
    cur_rps, base_rps = _metric(current_metrics.get("requests_per_second")), _metric(bm.get("requests_per_second"))
    rps_ratio = None if cur_rps is None or base_rps in (None, 0) else cur_rps / base_rps
    checks.append(_check("REGRESSION_THROUGHPUT", "NO_DATA" if cur_rps is None or base_rps in (None, 0) else ("PASS" if rps_ratio >= policy.throughput_min_ratio else "FAIL"), {"current": cur_rps, "baseline": base_rps, "ratio": None if rps_ratio is None else round(rps_ratio, 6)}, f">= {policy.throughput_min_ratio}"))
    cur_pool, base_pool = _metric(current_metrics.get("db_pool_max_saturation_ratio")), _metric(bm.get("db_pool_max_saturation_ratio"))
    delta = None if cur_pool is None or base_pool is None else cur_pool - base_pool
    checks.append(_check("REGRESSION_DB_POOL", "NO_DATA" if delta is None else ("PASS" if delta <= policy.db_pool_max_absolute_increase else "FAIL"), {"current": cur_pool, "baseline": base_pool, "absolute_increase": None if delta is None else round(delta, 6)}, f"absolute increase <= {policy.db_pool_max_absolute_increase}"))

    failed = [x["code"] for x in checks if x["status"] == "FAIL"]
    missing = [x["code"] for x in checks if x["status"] == "NO_DATA"]
    decision = "NO_GO" if failed else ("CONDITIONAL" if missing else "GO")
    return {
        "decision": decision,
        "checks": checks,
        "failed_checks": failed,
        "missing_checks": missing,
        "baseline_release": baseline.get("release"),
        "baseline_source_acceptance_sha256": baseline.get("source_acceptance_sha256"),
        "policy": asdict(policy),
    }


def build_release_acceptance(*, profile: str, production_report: dict[str, Any], load_evidence: dict[str, Any], source_evidence: dict[str, Any], baseline: dict[str, Any] | None) -> dict[str, Any]:
    metrics = extract_metrics(production_report=production_report, load_evidence=load_evidence, source_evidence=source_evidence)
    regression = evaluate_regression(current_metrics=metrics, baseline=baseline, profile=profile)
    technical = str(production_report.get("decision") or "CONDITIONAL")
    if technical == "NO_GO" or regression["decision"] == "NO_GO":
        decision = "NO_GO"
    elif technical == "GO" and regression["decision"] == "GO":
        decision = "GO"
    else:
        decision = "CONDITIONAL"
    parent = baseline.get("source_acceptance_sha256") if baseline else None
    parent_seq = int(baseline.get("source_chain_sequence") or 0) if baseline else 0
    out = {
        "schema": RELEASE_ACCEPTANCE_SCHEMA,
        "release": APP_VERSION,
        "schema_version": SCHEMA_VERSION,
        "profile": str(profile),
        "decision": decision,
        "technical_decision": technical,
        "production_authorized": False,
        "human_approval_required": True,
        "metrics": metrics,
        "technical_certification": production_report,
        "baseline_regression": regression,
        "chain": {
            "schema": ACCEPTANCE_CHAIN_SCHEMA,
            "sequence": parent_seq + 1,
            "parent_acceptance_sha256": parent,
        },
        "source_digests": {
            "load_evidence_sha256": canonical_sha256(load_evidence),
            "target_host_evidence_sha256": hashlib.sha256(json.dumps(source_evidence, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")).hexdigest(),
        },
        "policy": {
            "approved_baseline_required_for_release_go": True,
            "absolute_slo_and_relative_regression_gates_both_required": True,
            "technical_go_is_not_production_authorization": True,
            "human_change_control_required": True,
            "baseline_must_be_signed_and_human_approved": True,
        },
    }
    return attach_integrity(out)


def baseline_from_acceptance(*, acceptance: dict[str, Any], approval_reference: str, approved_at: str, bootstrap: bool = False) -> dict[str, Any]:
    integrity_ok, _claimed, actual = validate_integrity(acceptance)
    if acceptance.get("schema") != RELEASE_ACCEPTANCE_SCHEMA:
        raise ValueError("acceptance schema mismatch")
    if integrity_ok is not True:
        raise ValueError("acceptance canonical digest is missing or invalid")
    if (acceptance.get("integrity") or {}).get("detached_signature_verified") is not True:
        raise ValueError("acceptance detached signature is not verified")
    technical = acceptance.get("technical_decision")
    decision = acceptance.get("decision")
    if technical != "GO":
        raise ValueError("baseline source must have technical_decision=GO")
    if decision != "GO":
        only_missing_baseline = bootstrap and decision == "CONDITIONAL" and (acceptance.get("baseline_regression") or {}).get("missing_checks") == ["APPROVED_BASELINE"]
        if not only_missing_baseline:
            raise ValueError("baseline source must have release decision GO; bootstrap only permits the missing-baseline CONDITIONAL state")
    if not str(approval_reference or "").strip():
        raise ValueError("approval reference is required")
    baseline = {
        "schema": APPROVED_BASELINE_SCHEMA,
        "release": acceptance.get("release"),
        "schema_version": acceptance.get("schema_version"),
        "profile": acceptance.get("profile"),
        "technical_decision": "GO",
        "human_approved": True,
        "bootstrap": bool(bootstrap),
        "approval": {"reference": str(approval_reference).strip(), "approved_at": approved_at},
        "metrics": copy.deepcopy(acceptance.get("metrics") or {}),
        "source_acceptance_sha256": actual,
        "source_chain_sequence": int(((acceptance.get("chain") or {}).get("sequence") or 0)),
        "source_parent_acceptance_sha256": (acceptance.get("chain") or {}).get("parent_acceptance_sha256"),
        "governance": {"promoted_from_signed_acceptance": True, "production_authorization_not_embedded": True},
    }
    return attach_integrity(baseline)
