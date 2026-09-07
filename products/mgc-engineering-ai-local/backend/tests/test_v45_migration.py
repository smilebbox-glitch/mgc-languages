
from app.db import models  # noqa: F401
from sqlalchemy import create_engine, inspect
from app.db.migrations import ensure_v45_schema
from app.db.session import Base


def test_v45_migration_is_idempotent_and_new_tables_exist():
    engine=create_engine('sqlite:///:memory:')
    Base.metadata.create_all(engine)
    ensure_v45_schema(engine); ensure_v45_schema(engine)
    tables=set(inspect(engine).get_table_names())
    assert 'localization_items' in tables
    assert 'incoming_quality_records' in tables
