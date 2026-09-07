from sqlalchemy import create_engine, inspect, text

from app.db import models  # noqa: F401
from app.db.migrations import ensure_v602_schema
from app.db.session import Base


def test_v602_schema_adds_integration_quality_contract_and_marker_idempotently():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    ensure_v602_schema(engine)
    ensure_v602_schema(engine)
    inspector = inspect(engine)
    tables = set(inspector.get_table_names())
    assert "integration_ingest_events" in tables
    assert "mgc_schema_state" in tables
    ext_system_columns = {c["name"] for c in inspector.get_columns("external_systems")}
    assert {"source_domain", "contract_version", "expected_freshness_minutes", "required_fields", "last_quality_json"}.issubset(ext_system_columns)
    ext_object_columns = {c["name"] for c in inspector.get_columns("external_objects")}
    assert {"source_modified_at", "data_confidence_score", "data_confidence_level", "data_quality_json"}.issubset(ext_object_columns)
    run_columns = {c["name"] for c in inspector.get_columns("integration_runs")}
    assert {"quarantined_count", "replayed_count", "quality_json"}.issubset(run_columns)
    with engine.connect() as conn:
        assert conn.execute(text("SELECT schema_version FROM mgc_schema_state WHERE id=1")).scalar_one() == "6.0.2"
