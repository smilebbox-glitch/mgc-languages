from sqlalchemy import create_engine, inspect, text

from app.db.migrations import ensure_v38_schema


def test_v38_change_migration_is_additive_and_idempotent():
    engine = create_engine("sqlite:///:memory:")
    with engine.begin() as conn:
        conn.execute(text("""CREATE TABLE change_requests (
            id VARCHAR(36) PRIMARY KEY,
            code VARCHAR(128), title VARCHAR(512), description TEXT,
            part_number VARCHAR(128), from_revision VARCHAR(64), to_revision VARCHAR(64),
            status VARCHAR(64), risk_level VARCHAR(32), metadata_json JSON,
            created_at DATETIME, updated_at DATETIME
        )"""))
        conn.execute(text("INSERT INTO change_requests(id, code, title, status, risk_level) VALUES ('1','ECR-OLD','old','open','medium')"))
    ensure_v38_schema(engine); ensure_v38_schema(engine)
    cols = {c['name'] for c in inspect(engine).get_columns('change_requests')}
    assert {'eco_code','reason','priority','owner','created_by','impact_json','affected_parts','affected_document_ids','design_review_id','implementation_plan','verification_plan','completed_at'} <= cols
    with engine.connect() as conn:
        row = conn.execute(text("SELECT status, priority, created_by FROM change_requests WHERE id='1'" )).one()
    assert row.status == 'draft' and row.priority == 'normal' and row.created_by == 'system'
