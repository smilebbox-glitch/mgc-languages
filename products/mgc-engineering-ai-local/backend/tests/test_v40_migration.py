from sqlalchemy import create_engine, inspect, text

from app.db.migrations import ensure_v40_schema


def test_v40_manufacturing_area_migration_is_additive_and_idempotent():
    engine = create_engine("sqlite:///:memory:")
    with engine.begin() as conn:
        conn.execute(text("CREATE TABLE documents (id VARCHAR(36) PRIMARY KEY, filename VARCHAR(255))"))
        conn.execute(text("CREATE TABLE project_milestones (id VARCHAR(36) PRIMARY KEY, project_code VARCHAR(64), code VARCHAR(64))"))
    ensure_v40_schema(engine); ensure_v40_schema(engine)
    doc_cols = {c["name"] for c in inspect(engine).get_columns("documents")}
    ms_cols = {c["name"] for c in inspect(engine).get_columns("project_milestones")}
    assert "manufacturing_area" in doc_cols
    assert "manufacturing_area" in ms_cols
