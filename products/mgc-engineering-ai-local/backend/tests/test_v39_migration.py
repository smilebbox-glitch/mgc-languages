from sqlalchemy import create_engine, inspect, text

from app.db.migrations import ensure_v39_schema


def test_v39_project_migration_is_additive_and_idempotent():
    engine = create_engine("sqlite:///:memory:")
    with engine.begin() as conn:
        conn.execute(text("""CREATE TABLE projects (
            id VARCHAR(36) PRIMARY KEY,
            code VARCHAR(64), name VARCHAR(255), acl_groups JSON, created_at DATETIME
        )"""))
        conn.execute(text("INSERT INTO projects(id, code, name) VALUES ('1','OLD','Old Project')"))
    ensure_v39_schema(engine); ensure_v39_schema(engine)
    cols = {c['name'] for c in inspect(engine).get_columns('projects')}
    assert {'description','status','phase','owner','root_part_number','target_release_at','metadata_json','updated_at'} <= cols
    with engine.connect() as conn:
        row = conn.execute(text("SELECT status, phase FROM projects WHERE id='1'")).one()
    assert row.status == 'active' and row.phase == 'development'
