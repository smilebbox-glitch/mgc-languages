from sqlalchemy import create_engine, inspect, text
from app.db.session import Base
from app.db import models  # noqa: F401
from app.db.migrations import ensure_v601_schema


def test_v601_schema_wrapper_preserves_v60_and_adds_state_marker():
    engine=create_engine('sqlite:///:memory:')
    Base.metadata.create_all(engine)
    ensure_v601_schema(engine); ensure_v601_schema(engine)
    tables=set(inspect(engine).get_table_names())
    assert 'engineering_workflow_cases' in tables
    assert 'mgc_schema_state' in tables
    with engine.connect() as conn:
        assert conn.execute(text("SELECT schema_version FROM mgc_schema_state WHERE id=1")).scalar_one() == '6.0.1'
