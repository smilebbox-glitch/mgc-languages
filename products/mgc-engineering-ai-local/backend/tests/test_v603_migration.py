from sqlalchemy import create_engine, inspect, text

from app.db import models  # noqa: F401
from app.db.migrations import ensure_v603_schema
from app.db.session import Base


def test_v603_schema_adds_mapping_registry_and_marker_idempotently():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    ensure_v603_schema(engine)
    ensure_v603_schema(engine)
    tables = set(inspect(engine).get_table_names())
    assert "integration_entity_mappings" in tables
    cols = {x["name"] for x in inspect(engine).get_columns("integration_entity_mappings")}
    assert {"system_id", "source_external_id", "source_key", "canonical_entity_type", "canonical_key", "source_fingerprint", "last_verified_at"}.issubset(cols)
    with engine.connect() as conn:
        assert conn.execute(text("SELECT schema_version FROM mgc_schema_state WHERE id=1")).scalar_one() == "6.0.3"
