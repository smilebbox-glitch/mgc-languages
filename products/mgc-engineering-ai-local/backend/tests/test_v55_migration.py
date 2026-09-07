from sqlalchemy import create_engine, inspect
from app.db.session import Base
from app.db import models  # noqa
from app.db.migrations import ensure_v55_schema


def test_v55_schema_wrapper_is_additive_and_idempotent():
    engine=create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    ensure_v55_schema(engine);ensure_v55_schema(engine)
    tables=set(inspect(engine).get_table_names())
    assert {"manufacturing_bom_items","configuration_effectivity","change_cutins","as_built_configuration","part_supersessions"}.issubset(tables)
    assert "program_dependencies" in tables
