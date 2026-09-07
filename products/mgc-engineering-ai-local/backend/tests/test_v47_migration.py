from sqlalchemy import create_engine, inspect
from app.db.session import Base
from app.db import models  # noqa
from app.db.migrations import ensure_v47_schema


def test_v47_schema_is_idempotent_and_contains_architecture_tables():
    engine=create_engine('sqlite:///:memory:')
    Base.metadata.create_all(engine)
    ensure_v47_schema(engine); ensure_v47_schema(engine)
    tables=set(inspect(engine).get_table_names())
    assert {'architecture_nodes','interface_definitions','interface_verifications'} <= tables
