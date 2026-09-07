
from app.db import models  # noqa: F401
from sqlalchemy import create_engine, inspect

from app.db.migrations import ensure_v42_schema
from app.db.session import Base


def test_v42_schema_is_idempotent_and_has_process_tables_and_quality_links(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path/'v42.db'}")
    Base.metadata.create_all(engine)
    ensure_v42_schema(engine); ensure_v42_schema(engine)
    insp = inspect(engine)
    tables = set(insp.get_table_names())
    for name in {"manufacturing_lines", "process_stations", "process_operations", "process_assets", "process_parameters", "process_defects"}:
        assert name in tables
    pf_cols = {c["name"] for c in insp.get_columns("pfmea_items")}
    cp_cols = {c["name"] for c in insp.get_columns("control_plan_items")}
    assert "process_operation_id" in pf_cols
    assert "process_operation_id" in cp_cols
