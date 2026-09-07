from sqlalchemy import create_engine, inspect, text

from app.db import models  # noqa: F401
from app.db.migrations import ensure_v604_schema
from app.db.session import Base


REQUIRED = {
    "idx_v604_bom_parent_revision_child",
    "idx_v604_relationship_subject_predicate",
    "idx_v604_relationship_object_predicate",
    "idx_v604_vehicle_build_project_vin_status",
    "idx_v604_genealogy_build_part_supplier_lot",
    "idx_v604_series_project_time_part",
    "idx_v604_external_object_system_type_part",
    "idx_v604_ingest_system_status_received",
    "idx_v604_mapping_project_type_status",
}


def test_v604_schema_adds_performance_indexes_and_marker_idempotently():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    ensure_v604_schema(engine)
    ensure_v604_schema(engine)
    seen=set()
    inspector=inspect(engine)
    for table in inspector.get_table_names():
        seen.update(x["name"] for x in inspector.get_indexes(table))
    assert REQUIRED.issubset(seen)
    with engine.connect() as conn:
        assert conn.execute(text("SELECT schema_version FROM mgc_schema_state WHERE id=1")).scalar_one() == "6.0.4"
