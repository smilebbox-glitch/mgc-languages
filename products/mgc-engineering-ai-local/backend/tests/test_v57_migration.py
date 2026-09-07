
from app.db import models  # noqa: F401
from sqlalchemy import create_engine, inspect
from app.db.session import Base
from app.db.migrations import ensure_v57_schema


def test_v57_schema_wrapper_is_additive_and_idempotent():
    engine=create_engine('sqlite:///:memory:')
    Base.metadata.create_all(engine)
    ensure_v57_schema(engine); ensure_v57_schema(engine)
    tables=set(inspect(engine).get_table_names())
    assert {'series_quality_observations','process_capability_records','series_containment_cases','field_quality_claims'}.issubset(tables)
    assert {'vehicle_builds','build_genealogy_items','safe_launch_controls'}.issubset(tables)
