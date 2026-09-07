from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from statistics import median
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import PilotScenarioResult, PilotStudy, PilotTelemetryAggregate, PilotUsabilityIssue

PILOT_SCHEMA = "mgc-controlled-pilot-v1"
DEFAULT_REQUIRED_ROLES = ["rd", "manufacturing", "quality"]
DEFAULT_POLICY: dict[str, Any] = {
    "min_required_scenario_coverage": 1.0,
    "min_scenario_success_rate": 0.95,
    "min_evidence_coverage": 1.0,
    "min_median_time_reduction": 0.30,
    "min_usability_rating": 4.0,
    "max_error_rate": 0.02,
    "min_telemetry_sessions": 10,
    "required_external_gates": [
        "docker_runtime_acceptance",
        "cve_scan",
        "oidc_negative_tests",
        "backup_restore_drill",
        "performance_pilot",
    ],
}
FORBIDDEN_TELEMETRY_KEYS = {
    "user", "user_id", "username", "email", "ip", "ip_address", "query", "query_text",
    "vin", "vehicle_identifier", "document_id", "part_number", "employee", "person",
}


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def normalize_policy(policy: dict[str, Any] | None) -> dict[str, Any]:
    out = dict(DEFAULT_POLICY)
    if policy:
        out.update(policy)
    return out


def sanitize_telemetry_metadata(metadata: dict[str, Any] | None) -> dict[str, Any]:
    metadata = dict(metadata or {})
    forbidden = sorted(k for k in metadata if str(k).lower() in FORBIDDEN_TELEMETRY_KEYS)
    if forbidden:
        raise ValueError(f"Pilot telemetry must not contain participant/content identifiers: {', '.join(forbidden)}")
    # Keep only small categorical metadata; nested/raw payloads are not accepted.
    out: dict[str, Any] = {}
    for k, v in metadata.items():
        if isinstance(v, (str, int, float, bool)) and len(str(v)) <= 128:
            out[str(k)[:64]] = v
    return out


def _ratio(num: float, den: float) -> float | None:
    return None if den <= 0 else num / den


def _scenario_metrics(rows: list[PilotScenarioResult], required_roles: list[str]) -> dict[str, Any]:
    required = [x for x in rows if x.required]
    executed = [x for x in required if x.status in {"pass", "fail", "blocked"}]
    passed = [x for x in executed if x.status == "pass"]
    role_execution = {r: any(x.role == r and x.status in {"pass", "fail", "blocked"} for x in required) for r in required_roles}
    time_reductions = []
    usability = []
    evidence_expected = evidence_observed = 0
    critical_blockers = 0
    for x in executed:
        if x.baseline_seconds and x.baseline_seconds > 0 and x.mgc_seconds is not None and x.mgc_seconds >= 0:
            time_reductions.append((x.baseline_seconds - x.mgc_seconds) / x.baseline_seconds)
        if x.usability_rating is not None:
            usability.append(float(x.usability_rating))
        evidence_expected += max(int(x.expected_evidence_count or 0), 0)
        evidence_observed += min(max(int(x.evidence_count or 0), 0), max(int(x.expected_evidence_count or 0), 0))
        if str(x.blocker_severity or "").lower() in {"critical", "high"} or x.status == "blocked":
            critical_blockers += 1
    return {
        "required_scenarios": len(required),
        "executed_required": len(executed),
        "passed_required": len(passed),
        "required_scenario_coverage": _ratio(len(executed), len(required)) if required else 0.0,
        "scenario_success_rate": _ratio(len(passed), len(executed)) if executed else 0.0,
        "role_execution": role_execution,
        "all_required_roles_executed": all(role_execution.values()) if required_roles else True,
        "median_time_reduction": median(time_reductions) if time_reductions else None,
        "evidence_coverage": _ratio(evidence_observed, evidence_expected) if evidence_expected else (1.0 if executed else 0.0),
        "average_usability_rating": (sum(usability) / len(usability)) if usability else None,
        "critical_blockers": critical_blockers,
    }


def _telemetry_metrics(rows: list[PilotTelemetryAggregate]) -> dict[str, Any]:
    sessions = sum(max(int(x.sessions or 0), 0) for x in rows)
    completions = sum(max(int(x.completions or 0), 0) for x in rows)
    errors = sum(max(int(x.errors or 0), 0) for x in rows)
    duration = sum(max(float(x.total_duration_seconds or 0), 0.0) for x in rows)
    return {
        "sessions": sessions,
        "completions": completions,
        "errors": errors,
        "error_rate": _ratio(errors, sessions) if sessions else 0.0,
        "completion_rate": _ratio(completions, sessions) if sessions else 0.0,
        "average_session_seconds": _ratio(duration, sessions) if sessions else None,
        "privacy": "aggregate_only_no_user_ip_query_vin_or_document_tracking",
    }


def _check(code: str, passed: bool, actual: Any, required: Any, severity: str = "critical") -> dict[str, Any]:
    return {"code": code, "pass": bool(passed), "actual": actual, "required": required, "severity": severity}


def evaluate_pilot(
    db: Session,
    pilot: PilotStudy,
    *,
    reconciliation_report: dict[str, Any] | None = None,
    security_posture: dict[str, Any] | None = None,
) -> dict[str, Any]:
    policy = normalize_policy(pilot.gate_policy_json)
    roles = pilot.required_roles or list(DEFAULT_REQUIRED_ROLES)
    scenarios = db.scalars(select(PilotScenarioResult).where(PilotScenarioResult.pilot_id == pilot.id)).all()
    telemetry = db.scalars(select(PilotTelemetryAggregate).where(PilotTelemetryAggregate.pilot_id == pilot.id)).all()
    ux_issues = db.scalars(select(PilotUsabilityIssue).where(PilotUsabilityIssue.pilot_id == pilot.id)).all()
    sm = _scenario_metrics(scenarios, roles)
    tm = _telemetry_metrics(telemetry)
    open_ux = [x for x in ux_issues if x.status not in {"verified", "closed"}]
    uxm = {
        "open": len(open_ux),
        "critical": sum(str(x.severity).lower() == "critical" for x in open_ux),
        "high": sum(str(x.severity).lower() == "high" for x in open_ux),
        "verified_or_closed": sum(x.status in {"verified", "closed"} for x in ux_issues),
        "employee_performance_scoring": False,
    }

    checks: list[dict[str, Any]] = []
    checks.append(_check("required_scenario_coverage", sm["required_scenario_coverage"] >= float(policy["min_required_scenario_coverage"]), sm["required_scenario_coverage"], policy["min_required_scenario_coverage"]))
    checks.append(_check("required_role_coverage", sm["all_required_roles_executed"], sm["role_execution"], roles))
    checks.append(_check("scenario_success_rate", sm["scenario_success_rate"] >= float(policy["min_scenario_success_rate"]), sm["scenario_success_rate"], policy["min_scenario_success_rate"]))
    checks.append(_check("evidence_coverage", sm["evidence_coverage"] >= float(policy["min_evidence_coverage"]), sm["evidence_coverage"], policy["min_evidence_coverage"]))
    checks.append(_check("critical_blockers", sm["critical_blockers"] == 0, sm["critical_blockers"], 0))

    # KPI/usability misses are conditional-go items; they are not allowed to hide functional/safety failures.
    tr = sm["median_time_reduction"]
    checks.append(_check("median_time_reduction", tr is not None and tr >= float(policy["min_median_time_reduction"]), tr, policy["min_median_time_reduction"], "warning"))
    ur = sm["average_usability_rating"]
    checks.append(_check("usability_rating", ur is not None and ur >= float(policy["min_usability_rating"]), ur, policy["min_usability_rating"], "warning"))
    checks.append(_check("ux_telemetry_sessions", tm["sessions"] >= int(policy["min_telemetry_sessions"]), tm["sessions"], policy["min_telemetry_sessions"]))
    checks.append(_check("ux_error_rate", tm["error_rate"] <= float(policy["max_error_rate"]), tm["error_rate"], policy["max_error_rate"], "warning"))
    checks.append(_check("critical_usability_issues", uxm["critical"] == 0, uxm["critical"], 0, "critical"))
    checks.append(_check("high_usability_issues", uxm["high"] == 0, uxm["high"], 0, "warning"))

    if pilot.mode == "controlled":
        rec_status = ((reconciliation_report or {}).get("pilot_acceptance") or {}).get("status")
        checks.append(_check("data_reconciliation", rec_status == "READY_FOR_CONTROLLED_PILOT", rec_status or "NOT_EVALUATED", "READY_FOR_CONTROLLED_PILOT"))
        sec_status = (security_posture or {}).get("status")
        checks.append(_check("security_posture", sec_status == "PASS", sec_status or "NOT_EVALUATED", "PASS"))
        external = pilot.external_gate_evidence_json or {}
        for gate in policy.get("required_external_gates", []):
            value = str((external.get(gate) or {}).get("status") if isinstance(external.get(gate), dict) else external.get(gate) or "NOT_RUN").upper()
            checks.append(_check(f"external:{gate}", value == "PASS", value, "PASS"))

    critical_failed = [x for x in checks if not x["pass"] and x["severity"] == "critical"]
    warning_failed = [x for x in checks if not x["pass"] and x["severity"] == "warning"]
    if pilot.mode != "controlled":
        decision = "PRECHECK_PASS" if not critical_failed else "PRECHECK_FAIL"
    elif critical_failed:
        decision = "NO_GO"
    elif warning_failed:
        decision = "CONDITIONAL_GO"
    else:
        decision = "GO"

    return {
        "schema": PILOT_SCHEMA,
        "pilot": {"id": pilot.id, "code": pilot.code, "project_code": pilot.project_code, "name": pilot.name, "mode": pilot.mode, "status": pilot.status},
        "decision": decision,
        "human_go_live_required": True,
        "scenario_metrics": sm,
        "ux_telemetry": tm,
        "usability_issue_closure": uxm,
        "checks": checks,
        "blockers": [x for x in checks if not x["pass"]],
        "governance": {
            "synthetic_data_can_authorize_go": False,
            "employee_performance_scoring": False,
            "raw_query_or_vin_telemetry": False,
            "note": "Pilot evidence supports a human deployment decision; MGC never approves production go-live automatically.",
        },
    }
