from sqlalchemy import create_engine, inspect
from app.db.session import Base
from app.db import models  # noqa: F401
from app.db.migrations import ensure_v60_schema


def test_v60_schema_wrapper_is_additive_and_idempotent():
    engine=create_engine('sqlite:///:memory:')
    Base.metadata.create_all(engine)
    ensure_v60_schema(engine); ensure_v60_schema(engine)
    tables=set(inspect(engine).get_table_names())
    assert 'engineering_workflow_cases' in tables
    assert {'field_service_actions','series_quality_observations','vehicle_builds','release_baselines'}.issubset(tables)
