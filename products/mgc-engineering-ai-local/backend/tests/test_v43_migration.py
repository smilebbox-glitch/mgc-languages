from sqlalchemy import create_engine, inspect

from app.db.migrations import ensure_v43_schema
from app.db.session import Base
import app.db.models  # noqa: F401


def test_v43_schema_is_idempotent_and_has_launch_tables():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    ensure_v43_schema(engine); ensure_v43_schema(engine)
    tables = set(inspect(engine).get_table_names())
    assert "launch_readiness_items" in tables
    assert "launch_trials" in tables
