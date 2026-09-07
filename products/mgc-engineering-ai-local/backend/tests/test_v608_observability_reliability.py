import io
import json
import zipfile
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.db.models import Base, ComputeJob, ExternalSystem, ProductionIncident
from app.db.migrations import ensure_v608_schema
from app.services.production_support import (
    build_support_bundle,
    capture_health_samples,
    create_incident,
    dependency_sli,
    error_budget,
    integration_lag_snapshot,
    queue_snapshot,
    update_incident,
)


def db_session():
    eng = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(eng)
    ensure_v608_schema(eng)
    return eng, sessionmaker(bind=eng)()


def test_v608_schema_marker_and_tables():
    eng, db = db_session()
    with eng.begin() as c:
        assert c.execute(text("SELECT schema_version FROM mgc_schema_state WHERE id=1")).scalar_one() == "6.0.8"
        names = {r[0] for r in c.execute(text("SELECT name FROM sqlite_master WHERE type='table'"))}
    assert "operational_health_samples" in names
    assert "production_incidents" in names


def test_error_budget_is_explainable():
    x = error_budget(target=0.99, good=990, total=1000)
    assert x["status"] == "PASS"
    assert x["bad"] == 10
    assert x["budget_consumed_ratio"] == 1.0
    y = error_budget(target=0.99, good=980, total=1000)
    assert y["status"] == "BURNING"
    assert y["budget_remaining_ratio"] == 0.0


def test_health_samples_and_dependency_sli():
    _, db = db_session()
    now = datetime.now(timezone.utc)
    snap = {"status": "not_ready", "checks": [
        {"name": "database_schema", "required": True, "status": "ok", "latency_ms": 2.0, "detail": "available"},
        {"name": "qdrant", "required": True, "status": "failed", "latency_ms": 10.0, "detail": "unavailable"},
        {"name": "redis", "required": False, "status": "failed", "latency_ms": 5.0, "detail": "unavailable"},
    ]}
    assert capture_health_samples(db, snap, captured_at=now)["samples"] == 3
    out = dependency_sli(db, window_minutes=60, now=now + timedelta(seconds=1))
    assert out["required_dependency_slo"]["observed"] == 0.5
    assert out["required_dependency_slo"]["status"] == "BURNING"
    assert {x["component"] for x in out["components"]} == {"database_schema", "qdrant", "redis"}


def test_queue_age_warns_without_requiring_live_redis():
    _, db = db_session()
    now = datetime.now(timezone.utc)
    db.add(ComputeJob(user="u", kind="x", queue="heavy", status="queued", created_at=now - timedelta(hours=1)))
    db.commit()
    out = queue_snapshot(db, now=now)
    assert out["oldest_job_age_seconds"] >= 3599
    assert out["status"] == "WARN"
    assert out["redis"] in {"available", "unavailable"}


def test_integration_freshness_sli():
    _, db = db_session()
    now = datetime.now(timezone.utc)
    db.add_all([
        ExternalSystem(code="PLM", name="PLM", connector_type="generic_rest", enabled=True, source_domain="plm", expected_freshness_minutes=10, last_sync_at=now - timedelta(minutes=2), last_sync_status="success", last_quality_json={"level":"HIGH"}),
        ExternalSystem(code="MES", name="MES", connector_type="mes_rest", enabled=True, source_domain="mes", expected_freshness_minutes=5, last_sync_at=now - timedelta(minutes=20), last_sync_status="success", last_quality_json={"level":"HIGH"}),
    ])
    db.commit()
    out = integration_lag_snapshot(db, now=now)
    assert out["systems_with_sla"] == 2
    assert out["freshness_compliance"] == 0.5
    assert out["status"] == "BURNING"


def test_incident_requires_resolution_evidence():
    _, db = db_session()
    row = create_incident(db, code="INC-1", severity="high", component="qdrant", summary="Search unavailable", actor="admin")
    with pytest.raises(ValueError):
        update_incident(db, row, actor="admin", status="resolved")
    row = update_incident(db, row, actor="admin", status="resolved", resolution_summary="Recovered after approved service restart")
    assert row.status == "resolved"
    assert row.resolved_at is not None


def test_support_bundle_is_privacy_safe_and_hashed(monkeypatch):
    _, db = db_session()
    create_incident(db, code="INC-2", severity="medium", component="api", summary="VIN-SECRET-123 P-SECRET latency increased", actor="admin", evidence={"metric":"p95", "vin":"VIN-SECRET-123", "part_number":"P-SECRET"})
    safe_ready = {"status":"ready", "service":"MGC", "version":"6.0.8", "checks":[{"name":"database_schema","required":True,"status":"ok","latency_ms":1,"detail":"available"}]}
    monkeypatch.setattr("app.services.production_support.readiness_snapshot", lambda: safe_ready)
    payload, manifest = build_support_bundle(db, actor="admin", readiness=safe_ready)
    assert len(manifest["zip_sha256"]) == 64
    zf = zipfile.ZipFile(io.BytesIO(payload))
    assert set(zf.namelist()) == {"health.json", "manifest.json", "operations-summary.json", "incident-evidence.json", "security-posture.json", "resilience.json", "deployment-safety.json", "cutover-safety.json", "high-availability.json", "authoritative-ha.json", "multi-host-topology.json", "production-certification.json"}
    m = json.loads(zf.read("manifest.json"))
    assert m["privacy"]["contains_raw_logs"] is False
    assert m["privacy"]["contains_document_content"] is False
    blob = payload.lower()
    for forbidden in (b"password=", b"authorization:", b"raw_query", b"document_content", b"vin-secret-123", b"p-secret"):
        assert forbidden not in blob


def test_incident_model_is_operator_domain_not_qms():
    _, db = db_session()
    row = create_incident(db, code="OPS-7", severity="critical", component="database", summary="Database unavailable", actor="admin", detected_by="readiness")
    assert isinstance(row, ProductionIncident)
    assert row.component == "database"
    assert row.detected_by == "readiness"
