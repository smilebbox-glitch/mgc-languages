from __future__ import annotations

from sqlalchemy import create_engine, inspect, text

from app.core.config import Settings
from app.core.db_performance import begin_request_budget, end_request_budget, install_db_performance_instrumentation, performance_snapshot
from app.core.runtime_contract import APP_VERSION, SCHEMA_VERSION
from app.db import models  # noqa: F401
from app.db.migrations import ensure_v639_schema
from app.db.session import Base
from app.services.performance_governance import SCALE_PROFILES, bounded_batch, decode_cursor, encode_cursor, performance_governance_snapshot


def test_v639_schema_marker_and_composite_indexes_are_idempotent():
    eng=create_engine("sqlite:///:memory:")
    Base.metadata.create_all(eng)
    ensure_v639_schema(eng); ensure_v639_schema(eng)
    with eng.begin() as conn:
        assert conn.execute(text("SELECT schema_version FROM mgc_schema_state WHERE id=1")).scalar_one()=="6.3.9"
    indexes={x["name"] for x in inspect(eng).get_indexes("documents")}
    assert "idx_v639_documents_project_area_created" in indexes
    assert "idx_v639_documents_part_revision" in indexes
    assert APP_VERSION=="6.3.34" and SCHEMA_VERSION=="6.3.13"


def test_measure_first_query_budget_and_pool_defaults_are_safe():
    cfg=Settings()
    assert cfg.db_query_budget_enforcement_enabled is False
    assert cfg.db_pool_size >= 1 and cfg.db_max_overflow >= 0
    assert cfg.db_query_budget_max_statements >= 10
    assert cfg.cursor_page_max_limit >= cfg.cursor_page_default_limit
    assert cfg.performance_scale_profile in {"pilot_15","pilot_30","enterprise_100"}


def test_privacy_safe_db_telemetry_records_group_not_sql_or_bind_values():
    eng=create_engine("sqlite:///:memory:")
    install_db_performance_instrumentation(eng)
    token=begin_request_budget("/test")
    with eng.begin() as conn:
        conn.execute(text("SELECT :secret AS secret_value"), {"secret":"PART-SECRET-123"}).all()
    summary=end_request_budget(token)
    snap=performance_snapshot(eng)
    assert summary.statements == 1
    assert snap["privacy"] == {"sql_text_stored":False,"bind_values_stored":False}
    assert "PART-SECRET-123" not in str(snap)
    assert snap["totals_since_process_start"]["statements"] >= 1


def test_cursor_roundtrip_and_invalid_cursor_fail_closed():
    from datetime import datetime, timezone
    dt=datetime(2026,9,5,12,0,tzinfo=timezone.utc)
    cur=encode_cursor(dt,"row-42")
    created,row_id=decode_cursor(cur)
    assert created==dt.isoformat() and row_id=="row-42"
    import pytest
    with pytest.raises(ValueError,match="Invalid cursor"):
        decode_cursor("not-a-valid-cursor")


def test_bounded_batch_prevents_unbounded_ingest_payloads():
    assert list(bounded_batch(range(7),3)) == [[0,1,2],[3,4,5],[6]]
    assert len(next(iter(bounded_batch(range(6000),99999)))) == 5000


def test_scale_profiles_cover_15_30_and_100_engineer_reference_envelopes():
    assert set(SCALE_PROFILES)=={"pilot_15","pilot_30","enterprise_100"}
    assert SCALE_PROFILES["pilot_15"].named_users==15
    assert SCALE_PROFILES["pilot_30"].named_users==30
    assert SCALE_PROFILES["enterprise_100"].named_users==100
    assert SCALE_PROFILES["enterprise_100"].target_concurrent_users >= SCALE_PROFILES["pilot_30"].target_concurrent_users


def test_performance_snapshot_is_capacity_reference_not_production_claim():
    out=performance_governance_snapshot(create_engine("sqlite:///:memory:"))
    assert out["certification_required"] is True
    assert out["production_capacity_claim"] is False
    assert out["pagination"]["strategy"].startswith("keyset")
    assert out["bulk_ingestion"]["single_transaction_unbounded_batches"] is False
