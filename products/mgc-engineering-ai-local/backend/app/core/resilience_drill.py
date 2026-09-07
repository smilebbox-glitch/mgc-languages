from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any, Iterable

from app.core.runtime_contract import APP_VERSION, SCHEMA_VERSION

PLAN_SCHEMA = "mgc.resilience-drill-plan.v1"
EVIDENCE_SCHEMA = "mgc.resilience-drill-evidence.v1"
INTEGRITY_ALGORITHM = "sha256"

SCENARIOS: dict[str, dict[str, Any]] = {
    "api_instance_loss": {
        "service": "api",
        "compose_files": ["docker-compose.yml", "docker-compose.ha.yml"],
        "production_default_allowed": True,
        "profiles": ["core", "ai", "advanced"],
        "blast_radius": "single_api_replica",
        "expected_continuity": True,
        "expected_signal_codes": ["APPLICATION_HA_UNSAFE"],
    },
    "worker_cpu_loss": {
        "service": "worker-cpu",
        "compose_files": ["docker-compose.yml", "docker-compose.ha.yml"],
        "production_default_allowed": True,
        "profiles": ["core", "ai", "advanced"],
        "blast_radius": "single_cpu_worker",
        "expected_continuity": True,
        "expected_signal_codes": ["WORKLOAD_RECOVERY_REQUIRED"],
    },
    "redis_brownout": {
        "service": "redis",
        "compose_files": ["docker-compose.yml"],
        "production_default_allowed": False,
        "profiles": ["core", "ai", "advanced"],
        "blast_radius": "ephemeral_coordination_and_queue_dependency",
        "expected_continuity": True,
        "expected_signal_codes": ["REQUIRED_DEPENDENCY_NOT_READY", "OPTIONAL_DEPENDENCY_BROWNOUT"],
    },
    "qdrant_brownout": {
        "service": "qdrant",
        "compose_files": ["docker-compose.yml"],
        "production_default_allowed": False,
        "profiles": ["ai", "advanced"],
        "blast_radius": "semantic_search_enrichment_only",
        "expected_continuity": True,
        "expected_signal_codes": ["OPTIONAL_DEPENDENCY_BROWNOUT"],
    },
    "integration_gateway_timeout": {
        "service": "integration-simulator",
        "compose_files": ["docker-compose.yml", "docker-compose.integration-demo.yml"],
        "production_default_allowed": False,
        "profiles": ["core", "ai", "advanced"],
        "blast_radius": "single_external_integration_gateway",
        "expected_continuity": True,
        "expected_signal_codes": ["INTEGRATION_FRESHNESS_BREACH"],
    },
}


def _canonical(data: dict[str, Any]) -> bytes:
    return json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _integrity(body: dict[str, Any]) -> dict[str, str]:
    return {"algorithm": INTEGRITY_ALGORITHM, "payload_sha256": hashlib.sha256(_canonical(body)).hexdigest()}


def catalog() -> dict[str, Any]:
    return {
        "schema": "mgc.resilience-drill-catalog.v1",
        "release": APP_VERSION,
        "database_schema": SCHEMA_VERSION,
        "scenarios": {k: dict(v) for k, v in sorted(SCENARIOS.items())},
        "governance": {
            "arbitrary_shell_injection_allowed": False,
            "default_execution": "plan_only",
            "production_dependency_faults_require_override": True,
            "recovery_step_mandatory": True,
            "production_authorized": False,
        },
    }


def build_plan(
    scenarios: Iterable[str], *, tier: str = "staging", profile: str = "core",
    maintenance_window_ref: str = "", allow_production_dependency_drill: bool = False,
    max_fault_seconds: int = 30,
) -> dict[str, Any]:
    tier = str(tier).strip().lower()
    profile = str(profile).strip().lower()
    if tier not in {"staging", "production"}:
        raise ValueError("tier must be staging or production")
    if profile not in {"core", "ai", "advanced"}:
        raise ValueError("profile must be core, ai or advanced")
    if not 1 <= int(max_fault_seconds) <= 120:
        raise ValueError("max_fault_seconds must be between 1 and 120")

    selected: list[dict[str, Any]] = []
    seen: set[str] = set()
    for raw in scenarios:
        code = str(raw).strip()
        if not code or code in seen:
            continue
        if code not in SCENARIOS:
            raise ValueError(f"unknown drill scenario: {code}")
        spec = SCENARIOS[code]
        if profile not in spec["profiles"]:
            raise ValueError(f"scenario {code} is not valid for profile {profile}")
        if tier == "production" and not spec["production_default_allowed"]:
            if not allow_production_dependency_drill:
                raise ValueError(f"scenario {code} requires explicit production dependency-drill override")
            if not str(maintenance_window_ref).strip():
                raise ValueError("production dependency drills require maintenance_window_ref")
        selected.append({
            "scenario": code,
            "service": spec["service"],
            "compose_files": list(spec["compose_files"]),
            "blast_radius": spec["blast_radius"],
            "expected_continuity": bool(spec["expected_continuity"]),
            "expected_signal_codes": list(spec["expected_signal_codes"]),
            "fault_action": "compose_stop_service",
            "recovery_action": "compose_start_service",
        })
        seen.add(code)
    if not selected:
        raise ValueError("at least one drill scenario is required")

    body: dict[str, Any] = {
        "schema": PLAN_SCHEMA,
        "release": APP_VERSION,
        "database_schema": SCHEMA_VERSION,
        "tier": tier,
        "profile": profile,
        "maintenance_window_ref": str(maintenance_window_ref).strip()[:128],
        "max_fault_seconds": int(max_fault_seconds),
        "scenarios": selected,
        "governance": {
            "execution_default": "plan_only",
            "explicit_confirm_required": True,
            "arbitrary_shell_injection_allowed": False,
            "recovery_step_mandatory": True,
            "production_dependency_override": bool(allow_production_dependency_drill),
            "database_mutation_allowed": False,
            "engineering_data_mutation_allowed": False,
            "production_authorized": False,
            "human_operator_required": True,
        },
    }
    body["integrity"] = _integrity(body)
    return body


def validate_plan(plan: dict[str, Any]) -> tuple[bool, list[str]]:
    errors: list[str] = []
    if plan.get("schema") != PLAN_SCHEMA: errors.append("schema")
    if plan.get("release") != APP_VERSION: errors.append("release")
    if plan.get("database_schema") != SCHEMA_VERSION: errors.append("database_schema")
    if plan.get("tier") not in {"staging", "production"}: errors.append("tier")
    gov = plan.get("governance") or {}
    if gov.get("arbitrary_shell_injection_allowed") is not False: errors.append("arbitrary_shell_injection_allowed")
    if gov.get("recovery_step_mandatory") is not True: errors.append("recovery_step_mandatory")
    if gov.get("production_authorized") is not False: errors.append("production_authorized")
    rows = plan.get("scenarios") or []
    if not rows: errors.append("scenarios")
    for row in rows:
        code = str(row.get("scenario") or "")
        spec = SCENARIOS.get(code)
        if not spec or row.get("service") != spec["service"]:
            errors.append(f"scenario:{code or 'unknown'}")
    integ = plan.get("integrity") or {}
    body = dict(plan); body.pop("integrity", None)
    if integ.get("algorithm") != INTEGRITY_ALGORITHM or integ.get("payload_sha256") != hashlib.sha256(_canonical(body)).hexdigest():
        errors.append("integrity")
    return not errors, sorted(set(errors))


def build_evidence(plan: dict[str, Any], observations: list[dict[str, Any]], *, live_execution: bool, generated_at: datetime | None = None) -> dict[str, Any]:
    valid, errors = validate_plan(plan)
    if not valid:
        raise ValueError("invalid plan: " + ", ".join(errors))
    by_code = {str(o.get("scenario")): o for o in observations}
    results: list[dict[str, Any]] = []
    for row in plan["scenarios"]:
        code = row["scenario"]
        obs = by_code.get(code) or {}
        result = {
            "scenario": code,
            "service": row["service"],
            "fault_injected": bool(obs.get("fault_injected")),
            "continuity_passed": bool(obs.get("continuity_passed")),
            "recovery_attempted": bool(obs.get("recovery_attempted")),
            "recovery_passed": bool(obs.get("recovery_passed")),
            "recovery_seconds": None if obs.get("recovery_seconds") is None else round(float(obs.get("recovery_seconds")), 3),
            "expected_signal_codes": list(row.get("expected_signal_codes") or []),
            "notes_code": str(obs.get("notes_code") or "")[:64],
        }
        result["status"] = "PASS" if all((result["fault_injected"], result["continuity_passed"], result["recovery_attempted"], result["recovery_passed"])) else "FAIL"
        results.append(result)
    generated = generated_at or datetime.now(timezone.utc)
    if generated.tzinfo is None: generated = generated.replace(tzinfo=timezone.utc)
    overall = "PASS" if live_execution and results and all(r["status"] == "PASS" for r in results) else ("SIMULATED" if not live_execution else "FAIL")
    body: dict[str, Any] = {
        "schema": EVIDENCE_SCHEMA,
        "release": APP_VERSION,
        "database_schema": SCHEMA_VERSION,
        "generated_at": generated.astimezone(timezone.utc).isoformat(),
        "tier": plan["tier"],
        "profile": plan["profile"],
        "plan_sha256": (plan.get("integrity") or {}).get("payload_sha256"),
        "live_execution": bool(live_execution),
        "decision": overall,
        "results": results,
        "governance": {
            "contains_raw_logs": False,
            "contains_credentials": False,
            "contains_engineering_document_content": False,
            "arbitrary_shell_injection_used": False,
            "automatic_production_authorization": False,
            "automatic_root_cause_claimed": False,
            "human_operator_required": True,
        },
    }
    body["integrity"] = _integrity(body)
    return body


def validate_evidence(report: dict[str, Any]) -> tuple[bool, list[str]]:
    errors: list[str] = []
    if report.get("schema") != EVIDENCE_SCHEMA: errors.append("schema")
    if report.get("release") != APP_VERSION: errors.append("release")
    if report.get("database_schema") != SCHEMA_VERSION: errors.append("database_schema")
    if report.get("decision") not in {"PASS", "FAIL", "SIMULATED"}: errors.append("decision")
    if report.get("decision") == "PASS" and report.get("live_execution") is not True: errors.append("pass_requires_live_execution")
    gov = report.get("governance") or {}
    if gov.get("arbitrary_shell_injection_used") is not False: errors.append("arbitrary_shell_injection_used")
    if gov.get("automatic_production_authorization") is not False: errors.append("automatic_production_authorization")
    if gov.get("automatic_root_cause_claimed") is not False: errors.append("automatic_root_cause_claimed")
    for row in report.get("results") or []:
        if row.get("scenario") not in SCENARIOS: errors.append("unknown_scenario")
        if row.get("status") == "PASS" and not all(bool(row.get(k)) for k in ("fault_injected","continuity_passed","recovery_attempted","recovery_passed")):
            errors.append("invalid_pass_result")
    integ = report.get("integrity") or {}
    body = dict(report); body.pop("integrity", None)
    if integ.get("algorithm") != INTEGRITY_ALGORITHM or integ.get("payload_sha256") != hashlib.sha256(_canonical(body)).hexdigest():
        errors.append("integrity")
    return not errors, sorted(set(errors))


def bind_incident_evidence(report: dict[str, Any], incident_report: dict[str, Any]) -> dict[str, Any]:
    """Bind privacy-safe observability evidence by digest + bounded signal codes only.

    This is correlation evidence, not root-cause attribution. Raw signal payloads are never copied.
    """
    valid, errors = validate_evidence(report)
    if not valid:
        raise ValueError("invalid resilience evidence: " + ", ".join(errors))
    from app.core.incident_evidence import validate_incident_evidence
    iv, ie = validate_incident_evidence(incident_report)
    if not iv:
        raise ValueError("invalid incident evidence: " + ", ".join(ie))
    observed = sorted({str(x.get("code")) for x in (incident_report.get("signals") or []) if x.get("code")})
    expected = sorted({str(code) for row in (report.get("results") or []) for code in (row.get("expected_signal_codes") or [])})
    matched = sorted(set(observed) & set(expected))
    out = json.loads(json.dumps(report))
    out["incident_evidence_binding"] = {
        "schema": incident_report.get("schema"),
        "payload_sha256": (incident_report.get("integrity") or {}).get("payload_sha256"),
        "incident_status": incident_report.get("status"),
        "signal_count": int(incident_report.get("signal_count") or 0),
        "observed_signal_codes": observed[:64],
        "matched_expected_signal_codes": matched[:64],
        "correlation_status": "OBSERVED" if matched else "NOT_OBSERVED",
        "raw_signal_payloads_copied": False,
        "automatic_root_cause_claimed": False,
    }
    out.pop("integrity", None)
    out["integrity"] = _integrity(out)
    return out
