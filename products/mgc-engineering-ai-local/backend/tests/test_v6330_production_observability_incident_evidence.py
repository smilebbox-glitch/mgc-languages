from __future__ import annotations

import io
import json
import zipfile
from datetime import datetime, timezone

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.core.incident_evidence import build_incident_evidence, validate_incident_evidence
from app.db.models import Base, ProductionIncident
from app.services.production_support import reconcile_automated_incident_evidence


def db_session():
    eng = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(eng)
    return sessionmaker(bind=eng)()


def base_operations() -> dict:
    return {
        "dependency_sli": {"required_dependency_slo": {"status": "PASS", "observed": 1.0, "target": 0.995, "budget_remaining_ratio": 1.0}, "window_minutes": 60},
        "queue": {"status": "OK", "oldest_job_age_seconds": 0, "policy_max_age_seconds": 300},
        "integrations": {"status": "PASS", "freshness_compliance": 1.0, "target": 0.95, "systems": []},
        "projections": {"status": "healthy"},
        "workload": {"dead_letter_jobs": 0, "orphaned_jobs": 0, "expired_running_leases": 0},
        "resilience": {"mode": "NORMAL", "open_circuits": 0},
        "deployment_safety": {"incompatible_components": 0},
        "high_availability": {"enabled": True, "status": "HEALTHY"},
        "authoritative_data_ha": {"enabled": True, "status": "HEALTHY"},
        "multi_host_topology": {"enabled": True, "status": "HEALTHY"},
    }


def test_clear_report_is_canonical_and_non_authorizing():
    report = build_incident_evidence(
        base_operations(),
        readiness={"status": "ready", "checks": []},
        generated_at=datetime(2026, 9, 6, 10, 0, tzinfo=timezone.utc),
    )
    assert report["status"] == "CLEAR"
    assert report["signal_count"] == 0
    assert report["governance"]["production_authorized"] is False
    assert report["governance"]["automatic_incident_resolution"] is False
    assert validate_incident_evidence(report) == (True, [])


def test_runtime_failures_create_bounded_privacy_safe_signals():
    ops = base_operations()
    ops["dependency_sli"]["required_dependency_slo"].update(status="BURNING", observed=0.90, budget_remaining_ratio=0.0)
    ops["queue"].update(status="WARN", oldest_job_age_seconds=900)
    ops["integrations"] = {
        "status": "BURNING", "freshness_compliance": 0.5, "target": 0.95,
        "systems": [
            {"source_domain": "plm", "freshness_compliant": False, "secret": "DO-NOT-LEAK"},
            {"source_domain": "mes", "freshness_compliant": True},
        ],
    }
    ops["authoritative_data_ha"] = {"enabled": True, "status": "UNSAFE", "raw_error": "password=secret"}
    report = build_incident_evidence(
        ops,
        readiness={"status": "not_ready", "checks": [{"name": "database_schema", "required": True, "status": "failed", "detail": "token=secret"}]},
        generated_at=datetime(2026, 9, 6, 10, 1, tzinfo=timezone.utc),
    )
    codes = {s["code"] for s in report["signals"]}
    assert {"REQUIRED_DEPENDENCY_NOT_READY", "DEPENDENCY_ERROR_BUDGET_BURN", "QUEUE_AGE_BREACH", "INTEGRATION_FRESHNESS_BREACH", "AUTHORITATIVE_DATA_HA_UNSAFE"} <= codes
    assert report["highest_severity"] == "critical"
    blob = json.dumps(report, sort_keys=True).lower()
    for forbidden in ("do-not-leak", "password=secret", "token=secret"):
        assert forbidden not in blob
    assert validate_incident_evidence(report) == (True, [])


def test_tampered_report_fails_integrity():
    report = build_incident_evidence(base_operations(), readiness={"status": "ready", "checks": []})
    report["status"] = "INCIDENT_SIGNALS"
    valid, errors = validate_incident_evidence(report)
    assert valid is False
    assert "integrity" in errors


def test_reconcile_evidence_only_does_not_write():
    db = db_session()
    ops = base_operations()
    ops["queue"].update(status="WARN", oldest_job_age_seconds=600)
    report = build_incident_evidence(ops, readiness={"status": "ready", "checks": []})
    result = reconcile_automated_incident_evidence(db, report, materialize=False)
    assert result["materialization_enabled"] is False
    assert result["actions"][0]["action"] == "EVIDENCE_ONLY"
    assert db.scalars(select(ProductionIncident)).all() == []


def test_materialization_deduplicates_and_never_auto_resolves():
    db = db_session()
    ops = base_operations()
    ops["workload"].update(dead_letter_jobs=2, orphaned_jobs=1)
    report = build_incident_evidence(ops, readiness={"status": "ready", "checks": []})
    first = reconcile_automated_incident_evidence(db, report, materialize=True)
    second = reconcile_automated_incident_evidence(db, report, materialize=True)
    rows = db.scalars(select(ProductionIncident)).all()
    assert len(rows) == 1
    assert first["actions"][0]["action"] == "CREATED"
    assert second["actions"][0]["action"] == "REFRESHED"
    assert rows[0].detected_by == "automated-observability"
    assert rows[0].status == "open"
    assert rows[0].evidence_json["governance"]["automatic_resolution"] is False

    clear = build_incident_evidence(base_operations(), readiness={"status": "ready", "checks": []})
    reconcile_automated_incident_evidence(db, clear, materialize=True)
    db.refresh(rows[0])
    assert rows[0].status == "open"
    assert rows[0].resolved_at is None


def test_admin_reconcile_route_respects_materialization_feature_gate():
    from pathlib import Path
    src = Path("backend/app/api/operations_routes.py").read_text()
    assert 'reconcile_automated_incident_evidence(db, report, actor=identity.user, materialize=None)' in src
    assert 'materialize=True' not in src[src.index('def incident_evidence_reconcile'):src.index('@router.get("/incidents")')]
