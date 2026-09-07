from sqlalchemy import create_engine, inspect
from app.db.session import Base
from app.db.migrations import ensure_v56_schema
from app.db import models  # noqa: F401


def test_v56_schema_wrapper_is_additive_and_idempotent():
    engine=create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    ensure_v56_schema(engine); ensure_v56_schema(engine)
    tables=set(inspect(engine).get_table_names())
    assert {"vehicle_builds","build_genealogy_items","build_defect_links","safe_launch_controls"}.issubset(tables)
