from datetime import datetime, timedelta, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.db.session import Base
from app.db.models import ExternalObject, ExternalSystem, IntegrationRun
from app.services import integration_certification as cert


def _db():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    return Session(engine)


def _system(**overrides):
    config = {
        "base_url": "https://plm-gateway.internal.example",
        "certification": {
            "declared_capabilities": list(cert.DOMAIN_PROFILES["plm"]["required_capabilities"]),
            "checkpoint_mode": "fingerprint",
            "degraded_mode": "cached_read_only",
            "writeback_enabled": False,
            "enforce_for_sync": True,
            "recovery_sync_enabled": True,
            "max_cache_staleness_minutes": 120,
        },
    }
    fields = dict(
        id=None, code="plm1", name="PLM", connector_type="plm_rest", enabled=True,
        config_json=config, secret_config_json={"token_env": "MGC_TEST_TOKEN"}, acl_groups=["all"],
        source_domain="plm", contract_version="mgc-integration-v1", expected_freshness_minutes=60,
        required_fields=list(cert.DOMAIN_PROFILES["plm"]["recommended_required_fields"]),
    )
    fields.update(overrides)
    return ExternalSystem(**fields)


def _cached(db, system, *, age_minutes, now):
    db.add(ExternalObject(
        system_id=system.id, external_id=f"X-{age_minutes}", name="x", object_type="document",
        last_seen_at=now - timedelta(minutes=age_minutes),
    ))
    db.commit()


def test_policy_defaults_cache_staleness_to_twice_source_freshness():
    s = _system(expected_freshness_minutes=90)
    s.config_json = {**s.config_json, "certification": {k: v for k, v in s.config_json["certification"].items() if k != "max_cache_staleness_minutes"}}
    assert cert._policy(s)["max_cache_staleness_minutes"] == 180.0


def test_static_contract_rejects_unbounded_or_invalid_cache_window():
    s = _system()
    s.config_json = {**s.config_json, "certification": {**s.config_json["certification"], "max_cache_staleness_minutes": 20000}}
    out = cert.static_contract_report(s)
    assert out["decision"] == "NO_GO"
    assert any(x["code"] == "BOUNDED_CACHE_STALENESS" and x["status"] == "FAIL" for x in out["checks"])


def test_failed_source_with_fresh_cache_remains_read_only_and_recoverable():
    db = _db(); s = _system(); db.add(s); db.commit(); db.refresh(s)
    now = datetime.now(timezone.utc); _cached(db, s, age_minutes=30, now=now)
    s.last_health_status = "failed"; db.commit()
    out = cert.runtime_posture(db, s, now=now)
    assert out["mode"] == "DEGRADED_READ_ONLY"
    assert out["cached_engineering_reads_allowed"] is True
    assert out["cache_stale"] is False
    assert out["recovery_sync_allowed"] is True


def test_failed_source_with_stale_cache_blocks_cached_reads_but_allows_recovery_pull():
    db = _db(); s = _system(); db.add(s); db.commit(); db.refresh(s)
    now = datetime.now(timezone.utc); _cached(db, s, age_minutes=121, now=now)
    s.last_health_status = "failed"; db.commit()
    out = cert.runtime_posture(db, s, now=now)
    assert out["mode"] == "BLOCKED"
    assert out["cache_stale"] is True
    assert out["cached_engineering_reads_allowed"] is False
    assert out["recovery_sync_allowed"] is True
    assert "CACHE_STALE" in out["reasons"]


def test_healthy_source_with_stale_cache_degrades_until_refresh():
    db = _db(); s = _system(); db.add(s); db.commit(); db.refresh(s)
    now = datetime.now(timezone.utc); _cached(db, s, age_minutes=121, now=now)
    s.last_health_status = "ok"; db.commit()
    out = cert.runtime_posture(db, s, now=now)
    assert out["mode"] == "DEGRADED_READ_ONLY"
    assert out["reasons"] == ["CACHE_STALE"]
    assert out["recovery_sync_allowed"] is True
    assert out["cached_engineering_reads_allowed"] is False


def test_sync_guard_allows_recovery_sync_to_break_health_deadlock():
    db = _db(); s = _system(); db.add(s); db.commit(); db.refresh(s)
    s.last_health_status = "failed"; db.commit()
    allowed, posture = cert.sync_allowed(db, s)
    assert allowed is True
    assert posture["mode"] == "BLOCKED"
    assert posture["recovery_sync_allowed"] is True


def test_sync_guard_still_blocks_quality_degradation():
    db = _db(); s = _system(); db.add(s); db.commit(); db.refresh(s)
    now = datetime.now(timezone.utc); _cached(db, s, age_minutes=1, now=now)
    for _ in range(4):
        db.add(IntegrationRun(system_id=s.id, status="failed", failed_count=1))
    db.commit()
    allowed, posture = cert.sync_allowed(db, s)
    assert allowed is False
    assert posture["mode"] == "DEGRADED_READ_ONLY"
    assert posture["reasons"] == ["SYNC_SUCCESS_RATE_LOW"]


def test_ok_run_status_counts_as_success_in_reliability_metric():
    db = _db(); s = _system(); db.add(s); db.commit(); db.refresh(s)
    now = datetime.now(timezone.utc); _cached(db, s, age_minutes=1, now=now)
    for _ in range(4):
        db.add(IntegrationRun(system_id=s.id, status="ok", failed_count=0))
    db.commit()
    out = cert.runtime_posture(db, s, now=now)
    assert out["recent_sync_success_rate"] == 1.0
    assert out["mode"] == "ACTIVE"


def test_runtime_posture_v2_exposes_cache_freshness_without_raw_external_ids():
    db = _db(); s = _system(); db.add(s); db.commit(); db.refresh(s)
    now = datetime.now(timezone.utc); _cached(db, s, age_minutes=10, now=now)
    out = cert.runtime_posture(db, s, now=now)
    assert out["schema"] == "mgc.integration-runtime-posture.v2"
    assert out["cache_age_minutes"] == 10.0
    assert out["max_cache_staleness_minutes"] == 120.0
    assert "external_id" not in out


def test_naive_sqlite_timestamp_is_safely_treated_as_utc():
    now = datetime(2026, 9, 6, 9, 0, tzinfo=timezone.utc)
    assert cert._age_minutes(datetime(2026, 9, 6, 8, 30), now) == 30.0
