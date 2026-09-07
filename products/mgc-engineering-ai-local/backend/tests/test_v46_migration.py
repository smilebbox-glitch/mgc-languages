
from app.db import models  # noqa: F401
from sqlalchemy import create_engine, inspect
from app.db.migrations import ensure_v46_schema
from app.db.session import Base


def test_v46_migration_is_idempotent_and_cost_tables_exist():
    engine=create_engine('sqlite:///:memory:')
    Base.metadata.create_all(engine)
    ensure_v46_schema(engine); ensure_v46_schema(engine)
    tables=set(inspect(engine).get_table_names())
    assert {'cost_baselines','cost_lines','supplier_quotations'} <= tables
