from sqlalchemy import create_engine, inspect

from app.db.migrations import ensure_v44_schema
from app.db.session import Base
import app.db.models  # noqa: F401


def test_v44_schema_is_idempotent_and_has_requirements_tables():
    engine=create_engine('sqlite:///:memory:')
    Base.metadata.create_all(engine)
    ensure_v44_schema(engine); ensure_v44_schema(engine)
    tables=set(inspect(engine).get_table_names())
    assert 'engineering_requirements' in tables
    assert 'requirement_verifications' in tables
