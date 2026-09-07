from __future__ import annotations

import copy
import hashlib
import json
from dataclasses import asdict, dataclass
from typing import Any, Iterable

from app.core.resilience_drill import EVIDENCE_SCHEMA as DRILL_EVIDENCE_SCHEMA, SCENARIOS
from app.core.runtime_contract import APP_VERSION, SCHEMA_VERSION

BASELINE_SCHEMA = "mgc.resilience-recovery-baseline.v1"
CAMPAIGN_SCHEMA = "mgc.resilience-drill-campaign.v1"
CERTIFICATION_SCHEMA = "mgc.resilience-certification.v1"
CANONICALIZATION = "mgc-json-sorted-utf8-v1"


@dataclass(frozen=True)
class RecoveryRegressionPolicy:
    max_rto_ratio: float = 1.20
    max_absolute_increase_seconds: float = 5.0
    rto_ceiling_seconds: float = 120.0


DEFAULT_POLICY = RecoveryRegressionPolicy()


def canonical_payload_bytes(document: dict[str, Any]) -> bytes:
    payload = copy.deepcopy(document)
    payload.pop("integrity", None)
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")


def canonical_sha256(document: dict[str, Any]) -> str:
    return hashlib.sha256(canonical_payload_bytes(document)).hexdigest()


def attach_integrity(document: dict[str, Any]) -> dict[str, Any]:
    out = copy.deepcopy(document)
    out["integrity"] = {
        "algorithm": "sha256",
        "canonicalization": CANONICALIZATION,
        "payload_sha256": canonical_sha256(out),
    }
    return out


def validate_integrity(document: dict[str, Any]) -> bool:
    integrity = document.get("integrity") or {}
    claimed = str(integrity.get("payload_sha256") or "")
    return bool(claimed) and str(integrity.get("algorithm") or "") == "sha256" and claimed == canonical_sha256(document)


def _version_tuple(value: str) -> tuple[int, int, int] | None:
    try:
        parts = tuple(int(x) for x in str(value).split("."))
        return parts if len(parts) == 3 else None
    except Exception:
        return None


def _is_adjacent_previous_release(current: str, baseline: str) -> bool:
    current_v, baseline_v = _version_tuple(current), _version_tuple(baseline)
    if not current_v or not baseline_v or current_v[:2] != baseline_v[:2]:
        return False
    return current_v[2] > 0 and baseline_v == (current_v[0], current_v[1], current_v[2] - 1)


def validate_drill_evidence_for_certification(report: dict[str, Any], *, expected_release: str | None = None) -> tuple[bool, list[str]]:
    errors: list[str] = []
    if report.get("schema") != DRILL_EVIDENCE_SCHEMA:
        errors.append("schema")
    if expected_release is not None and report.get("release") != expected_release:
        errors.append("release")
    if report.get("database_schema") != SCHEMA_VERSION:
        errors.append("database_schema")
    if report.get("live_execution") is not True:
        errors.append("live_execution")
    if report.get("decision") != "PASS":
        errors.append("decision")
    rows = report.get("results") or []
    if not rows:
        errors.append("results")
    seen: set[str] = set()
    for row in rows:
        scenario = str(row.get("scenario") or "")
        if scenario not in SCENARIOS:
            errors.append("unknown_scenario")
        if scenario in seen:
            errors.append("duplicate_scenario")
        seen.add(scenario)
        if row.get("status") != "PASS":
            errors.append(f"scenario_not_pass:{scenario or 'unknown'}")
        try:
            value = float(row.get("recovery_seconds"))
            if value < 0:
                raise ValueError
        except (TypeError, ValueError):
            errors.append(f"recovery_seconds:{scenario or 'unknown'}")
    gov = report.get("governance") or {}
    if gov.get("automatic_production_authorization") is not False:
        errors.append("automatic_production_authorization")
    if gov.get("automatic_root_cause_claimed") is not False:
        errors.append("automatic_root_cause_claimed")
    # v6.3.31 drill evidence uses sha256(payload-without-integrity) and is intentionally release-portable.
    integrity = report.get("integrity") or {}
    claimed = str(integrity.get("payload_sha256") or "")
    actual = hashlib.sha256(canonical_payload_bytes(report)).hexdigest()
    if integrity.get("algorithm") != "sha256" or not claimed or claimed != actual:
        errors.append("integrity")
    return not errors, sorted(set(errors))


def _signature_ok(signature_verification: dict[str, Any] | None) -> bool:
    sig = signature_verification or {}
    return sig.get("verified") is True and str(sig.get("algorithm") or "") in {"openssl-sha256", "sha256-rsa", "sha256-ecdsa"} and bool(str(sig.get("public_key_sha256") or ""))


def _scenario_metrics(evidence: dict[str, Any]) -> dict[str, float]:
    return {str(row["scenario"]): round(float(row["recovery_seconds"]), 3) for row in (evidence.get("results") or [])}


def build_baseline(
    evidence: dict[str, Any], *, signature_verification: dict[str, Any], approval_reference: str,
    approved_at: str, approved_by_role: str, bootstrap: bool = False,
) -> dict[str, Any]:
    valid, errors = validate_drill_evidence_for_certification(evidence)
    if not valid:
        raise ValueError("invalid drill evidence: " + ", ".join(errors))
    if not _signature_ok(signature_verification):
        raise ValueError("detached drill evidence signature must be verified")
    if not str(approval_reference).strip() or not str(approved_at).strip() or not str(approved_by_role).strip():
        raise ValueError("human approval reference, timestamp and role are required")
    metrics = _scenario_metrics(evidence)
    body = {
        "schema": BASELINE_SCHEMA,
        "release": str(evidence.get("release")),
        "database_schema": str(evidence.get("database_schema")),
        "profile": str(evidence.get("profile")),
        "tier": str(evidence.get("tier")),
        "source_drill_evidence_sha256": str((evidence.get("integrity") or {}).get("payload_sha256") or ""),
        "source_signature": {
            "verified": True,
            "algorithm": str(signature_verification.get("algorithm")),
            "public_key_sha256": str(signature_verification.get("public_key_sha256")),
        },
        "metrics": {
            "per_scenario_rto_seconds": metrics,
            "aggregate_rto_seconds": round(max(metrics.values()), 3),
        },
        "approval": {
            "human_approved": True,
            "reference": str(approval_reference).strip()[:128],
            "approved_at": str(approved_at).strip()[:64],
            "approved_by_role": str(approved_by_role).strip()[:64],
        },
        "bootstrap": bool(bootstrap),
        "governance": {
            "simulation_allowed_as_baseline": False,
            "signed_live_evidence_required": True,
            "production_authorized": False,
        },
    }
    return attach_integrity(body)


def validate_baseline(baseline: dict[str, Any]) -> tuple[bool, list[str]]:
    errors: list[str] = []
    if baseline.get("schema") != BASELINE_SCHEMA: errors.append("schema")
    if baseline.get("database_schema") != SCHEMA_VERSION: errors.append("database_schema")
    if not _version_tuple(str(baseline.get("release") or "")): errors.append("release")
    if baseline.get("profile") not in {"core", "ai", "advanced"}: errors.append("profile")
    if baseline.get("tier") not in {"staging", "production"}: errors.append("tier")
    if not validate_integrity(baseline): errors.append("integrity")
    if ((baseline.get("approval") or {}).get("human_approved")) is not True: errors.append("human_approved")
    if not str((baseline.get("approval") or {}).get("reference") or "").strip(): errors.append("approval_reference")
    if not str((baseline.get("approval") or {}).get("approved_at") or "").strip(): errors.append("approved_at")
    if not str((baseline.get("approval") or {}).get("approved_by_role") or "").strip(): errors.append("approved_by_role")
    if not _signature_ok({**(baseline.get("source_signature") or {}), "verified": (baseline.get("source_signature") or {}).get("verified")}): errors.append("source_signature")
    source_digest = str(baseline.get("source_drill_evidence_sha256") or "")
    if len(source_digest) != 64 or any(c not in "0123456789abcdef" for c in source_digest.lower()): errors.append("source_drill_evidence_sha256")
    metrics = ((baseline.get("metrics") or {}).get("per_scenario_rto_seconds") or {})
    if not metrics: errors.append("metrics")
    numeric_metrics: list[float] = []
    for code, value in metrics.items():
        if code not in SCENARIOS: errors.append("unknown_scenario")
        try:
            numeric = float(value)
            if numeric < 0: raise ValueError
            numeric_metrics.append(numeric)
        except (TypeError, ValueError): errors.append(f"metric:{code}")
    if numeric_metrics:
        try:
            aggregate = float((baseline.get("metrics") or {}).get("aggregate_rto_seconds"))
            if abs(aggregate - max(numeric_metrics)) > 0.001: errors.append("aggregate_rto_seconds")
        except (TypeError, ValueError): errors.append("aggregate_rto_seconds")
    gov = baseline.get("governance") or {}
    if gov.get("simulation_allowed_as_baseline") is not False: errors.append("simulation_allowed_as_baseline")
    if gov.get("signed_live_evidence_required") is not True: errors.append("signed_live_evidence_required")
    if gov.get("production_authorized") is not False: errors.append("production_authorized")
    return not errors, sorted(set(errors))


def build_campaign(
    *, campaign_id: str, baseline: dict[str, Any], scenarios: Iterable[str], profile: str, tier: str,
    approval_reference: str, approved_at: str, approved_by_role: str,
    policy: RecoveryRegressionPolicy = DEFAULT_POLICY,
) -> dict[str, Any]:
    valid, errors = validate_baseline(baseline)
    if not valid:
        raise ValueError("invalid recovery baseline: " + ", ".join(errors))
    selected = []
    seen: set[str] = set()
    baseline_metrics = ((baseline.get("metrics") or {}).get("per_scenario_rto_seconds") or {})
    for raw in scenarios:
        code = str(raw).strip()
        if not code or code in seen: continue
        if code not in SCENARIOS: raise ValueError(f"unknown drill scenario: {code}")
        if code not in baseline_metrics: raise ValueError(f"baseline has no recovery metric for required scenario: {code}")
        selected.append(code); seen.add(code)
    if not selected: raise ValueError("campaign requires at least one scenario")
    if profile not in {"core", "ai", "advanced"}: raise ValueError("invalid profile")
    if tier not in {"staging", "production"}: raise ValueError("invalid tier")
    if profile != baseline.get("profile") or tier != baseline.get("tier"):
        raise ValueError("campaign profile/tier must match baseline")
    if not str(campaign_id).strip() or not str(approval_reference).strip() or not str(approved_at).strip() or not str(approved_by_role).strip():
        raise ValueError("campaign id and human approval metadata are required")
    if policy.max_rto_ratio < 1.0 or policy.max_absolute_increase_seconds < 0 or policy.rto_ceiling_seconds <= 0:
        raise ValueError("invalid recovery regression policy")
    body = {
        "schema": CAMPAIGN_SCHEMA,
        "campaign_id": str(campaign_id).strip()[:128],
        "target_release": APP_VERSION,
        "database_schema": SCHEMA_VERSION,
        "profile": profile,
        "tier": tier,
        "baseline_release": baseline.get("release"),
        "baseline_sha256": (baseline.get("integrity") or {}).get("payload_sha256"),
        "required_scenarios": selected,
        "policy": asdict(policy),
        "approval": {
            "human_approved": True,
            "reference": str(approval_reference).strip()[:128],
            "approved_at": str(approved_at).strip()[:64],
            "approved_by_role": str(approved_by_role).strip()[:64],
        },
        "governance": {
            "all_required_scenarios_must_pass": True,
            "signed_current_evidence_required": True,
            "approved_baseline_required": True,
            "automatic_threshold_relaxation_allowed": False,
            "production_authorized": False,
        },
    }
    return attach_integrity(body)


def validate_campaign(campaign: dict[str, Any], baseline: dict[str, Any] | None = None) -> tuple[bool, list[str]]:
    errors: list[str] = []
    if campaign.get("schema") != CAMPAIGN_SCHEMA: errors.append("schema")
    if campaign.get("target_release") != APP_VERSION: errors.append("target_release")
    if campaign.get("database_schema") != SCHEMA_VERSION: errors.append("database_schema")
    if not validate_integrity(campaign): errors.append("integrity")
    if ((campaign.get("approval") or {}).get("human_approved")) is not True: errors.append("human_approved")
    if not str((campaign.get("approval") or {}).get("reference") or "").strip(): errors.append("approval_reference")
    if not str((campaign.get("approval") or {}).get("approved_at") or "").strip(): errors.append("approved_at")
    if not str((campaign.get("approval") or {}).get("approved_by_role") or "").strip(): errors.append("approved_by_role")
    if campaign.get("profile") not in {"core", "ai", "advanced"}: errors.append("profile")
    if campaign.get("tier") not in {"staging", "production"}: errors.append("tier")
    required = campaign.get("required_scenarios") or []
    if not required: errors.append("required_scenarios")
    if len(required) != len(set(required)): errors.append("duplicate_scenario")
    if any(code not in SCENARIOS for code in required): errors.append("unknown_scenario")
    policy = campaign.get("policy") or {}
    try:
        if float(policy.get("max_rto_ratio")) < 1.0: errors.append("max_rto_ratio")
        if float(policy.get("max_absolute_increase_seconds")) < 0: errors.append("max_absolute_increase_seconds")
        if float(policy.get("rto_ceiling_seconds")) <= 0: errors.append("rto_ceiling_seconds")
    except (TypeError, ValueError): errors.append("policy")
    gov = campaign.get("governance") or {}
    if gov.get("all_required_scenarios_must_pass") is not True: errors.append("all_required_scenarios_must_pass")
    if gov.get("signed_current_evidence_required") is not True: errors.append("signed_current_evidence_required")
    if gov.get("approved_baseline_required") is not True: errors.append("approved_baseline_required")
    if gov.get("automatic_threshold_relaxation_allowed") is not False: errors.append("automatic_threshold_relaxation_allowed")
    if gov.get("production_authorized") is not False: errors.append("production_authorized")
    if baseline is not None:
        bv, be = validate_baseline(baseline)
        if not bv: errors += [f"baseline:{x}" for x in be]
        if campaign.get("baseline_sha256") != (baseline.get("integrity") or {}).get("payload_sha256"): errors.append("baseline_sha256")
        if campaign.get("baseline_release") != baseline.get("release"): errors.append("baseline_release")
        if campaign.get("profile") != baseline.get("profile"): errors.append("baseline_profile")
        if campaign.get("tier") != baseline.get("tier"): errors.append("baseline_tier")
    return not errors, sorted(set(errors))


def _check(code: str, status: str, actual: Any, expected: Any) -> dict[str, Any]:
    return {"code": code, "status": status, "actual": actual, "expected": expected}


def certify_recovery(
    *, current_evidence: dict[str, Any], signature_verification: dict[str, Any],
    baseline: dict[str, Any], campaign: dict[str, Any],
) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []
    ev_ok, ev_errors = validate_drill_evidence_for_certification(current_evidence, expected_release=APP_VERSION)
    base_ok, base_errors = validate_baseline(baseline)
    campaign_ok, campaign_errors = validate_campaign(campaign, baseline)
    checks += [
        _check("CURRENT_DRILL_EVIDENCE", "PASS" if ev_ok else "FAIL", ev_errors, []),
        _check("CURRENT_EVIDENCE_SIGNATURE", "PASS" if _signature_ok(signature_verification) else "FAIL", bool(_signature_ok(signature_verification)), True),
        _check("APPROVED_BASELINE", "PASS" if base_ok else "FAIL", base_errors, []),
        _check("APPROVED_CAMPAIGN", "PASS" if campaign_ok else "FAIL", campaign_errors, []),
    ]
    previous_release = _is_adjacent_previous_release(APP_VERSION, str(baseline.get("release") or ""))
    checks.append(_check("BASELINE_RELEASE_ORDER", "PASS" if previous_release and not baseline.get("bootstrap") else "FAIL", baseline.get("release"), f"adjacent previous release of {APP_VERSION}"))
    profile_tier_match = bool(
        ev_ok and base_ok and campaign_ok
        and current_evidence.get("profile") == baseline.get("profile") == campaign.get("profile")
        and current_evidence.get("tier") == baseline.get("tier") == campaign.get("tier")
    )
    checks.append(_check(
        "PROFILE_TIER_MATCH", "PASS" if profile_tier_match else "FAIL",
        {"current": [current_evidence.get("profile"), current_evidence.get("tier")], "baseline": [baseline.get("profile"), baseline.get("tier")], "campaign": [campaign.get("profile"), campaign.get("tier")]},
        "current evidence, baseline and campaign must use identical profile/tier",
    ))
    current = _scenario_metrics(current_evidence) if ev_ok else {}
    base = ((baseline.get("metrics") or {}).get("per_scenario_rto_seconds") or {}) if base_ok else {}
    required = list(campaign.get("required_scenarios") or []) if campaign_ok else []
    policy = campaign.get("policy") or asdict(DEFAULT_POLICY)
    ratio_limit = float(policy.get("max_rto_ratio", DEFAULT_POLICY.max_rto_ratio))
    abs_limit = float(policy.get("max_absolute_increase_seconds", DEFAULT_POLICY.max_absolute_increase_seconds))
    ceiling = float(policy.get("rto_ceiling_seconds", DEFAULT_POLICY.rto_ceiling_seconds))
    comparisons: list[dict[str, Any]] = []
    for code in required:
        cur = current.get(code); old = base.get(code)
        if cur is None or old is None:
            status = "FAIL"; ratio = None; delta = None
        else:
            cur_f, old_f = float(cur), float(old)
            ratio = None if old_f == 0 else cur_f / old_f
            delta = cur_f - old_f
            ratio_ok = cur_f <= old_f if old_f == 0 else ratio <= ratio_limit
            status = "PASS" if ratio_ok and delta <= abs_limit and cur_f <= ceiling else "FAIL"
        comparisons.append({
            "scenario": code,
            "status": status,
            "baseline_rto_seconds": old,
            "current_rto_seconds": cur,
            "ratio": None if ratio is None else round(ratio, 6),
            "absolute_delta_seconds": None if delta is None else round(delta, 3),
            "limits": {"max_rto_ratio": ratio_limit, "max_absolute_increase_seconds": abs_limit, "rto_ceiling_seconds": ceiling},
        })
    required_present = bool(required) and all(code in current for code in required) and all(code in base for code in required)
    checks.append(_check("REQUIRED_SCENARIOS", "PASS" if required_present else "FAIL", sorted(current), required))
    checks.append(_check("RTO_REGRESSION_GATE", "PASS" if comparisons and all(x["status"] == "PASS" for x in comparisons) else "FAIL", comparisons, "all required scenarios within approved recovery policy"))
    failed = [x["code"] for x in checks if x["status"] == "FAIL"]
    decision = "GO" if not failed else "NO_GO"
    aggregate_current = max(current.values()) if current else None
    aggregate_baseline = max(float(v) for v in base.values()) if base else None
    body = {
        "schema": CERTIFICATION_SCHEMA,
        "release": APP_VERSION,
        "database_schema": SCHEMA_VERSION,
        "profile": current_evidence.get("profile"),
        "tier": current_evidence.get("tier"),
        "decision": decision,
        "production_authorized": False,
        "human_release_approval_required": True,
        "campaign_id": campaign.get("campaign_id"),
        "baseline_release": baseline.get("release"),
        "current_drill_evidence_sha256": (current_evidence.get("integrity") or {}).get("payload_sha256"),
        "current_signature": {
            "verified": bool(_signature_ok(signature_verification)),
            "algorithm": signature_verification.get("algorithm"),
            "public_key_sha256": signature_verification.get("public_key_sha256"),
        },
        "baseline_sha256": (baseline.get("integrity") or {}).get("payload_sha256"),
        "campaign_sha256": (campaign.get("integrity") or {}).get("payload_sha256"),
        "aggregate_rto": {"baseline_seconds": aggregate_baseline, "current_seconds": aggregate_current},
        "scenario_comparisons": comparisons,
        "checks": checks,
        "failed_checks": failed,
        "governance": {
            "signed_live_drill_required": True,
            "approved_campaign_required": True,
            "approved_previous_release_baseline_required": True,
            "automatic_regression_detection": True,
            "automatic_threshold_relaxation_allowed": False,
            "automatic_production_authorization": False,
            "human_release_approval_required": True,
        },
    }
    return attach_integrity(body)


def validate_certification(report: dict[str, Any], *, require_go: bool = False) -> tuple[bool, list[str]]:
    errors: list[str] = []
    if report.get("schema") != CERTIFICATION_SCHEMA: errors.append("schema")
    if report.get("release") != APP_VERSION: errors.append("release")
    if report.get("database_schema") != SCHEMA_VERSION: errors.append("database_schema")
    if report.get("decision") not in {"GO", "NO_GO"}: errors.append("decision")
    if require_go and report.get("decision") != "GO": errors.append("require_go")
    if report.get("production_authorized") is not False: errors.append("production_authorized")
    gov = report.get("governance") or {}
    if gov.get("automatic_production_authorization") is not False: errors.append("automatic_production_authorization")
    if gov.get("human_release_approval_required") is not True: errors.append("human_release_approval_required")
    if not _signature_ok({**(report.get("current_signature") or {}), "verified": (report.get("current_signature") or {}).get("verified")}): errors.append("current_signature")
    required_check_codes = {"CURRENT_DRILL_EVIDENCE", "CURRENT_EVIDENCE_SIGNATURE", "APPROVED_BASELINE", "APPROVED_CAMPAIGN", "BASELINE_RELEASE_ORDER", "PROFILE_TIER_MATCH", "REQUIRED_SCENARIOS", "RTO_REGRESSION_GATE"}
    check_codes = {str(x.get("code") or "") for x in (report.get("checks") or [])}
    if not required_check_codes.issubset(check_codes): errors.append("required_checks")
    if not validate_integrity(report): errors.append("integrity")
    if report.get("decision") == "GO" and any(x.get("status") != "PASS" for x in (report.get("checks") or [])): errors.append("go_with_failed_check")
    return not errors, sorted(set(errors))


def validate_release_bundle(
    report: dict[str, Any], *, current_evidence: dict[str, Any], signature_verification: dict[str, Any],
    baseline: dict[str, Any], campaign: dict[str, Any], require_go: bool = True,
) -> tuple[bool, list[str]]:
    """Recompute certification from signed source artifacts instead of trusting a standalone GO JSON."""
    errors: list[str] = []
    valid, report_errors = validate_certification(report, require_go=require_go)
    if not valid:
        errors.extend(report_errors)
    recomputed = certify_recovery(
        current_evidence=current_evidence, signature_verification=signature_verification,
        baseline=baseline, campaign=campaign,
    )
    if canonical_sha256(report) != canonical_sha256(recomputed):
        errors.append("certification_recompute_mismatch")
    return not errors, sorted(set(errors))
