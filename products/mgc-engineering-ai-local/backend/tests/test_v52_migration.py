from sqlalchemy import create_engine, inspect
from app.db.session import Base
from app.db import models  # noqa
from app.db.migrations import ensure_v52_schema


def test_v52_schema_is_additive_and_idempotent():
    engine=create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    ensure_v52_schema(engine); ensure_v52_schema(engine)
    tables=set(inspect(engine).get_table_names())
    assert "engineering_lessons" in tables
    cols={c["name"] for c in inspect(engine).get_columns("engineering_lessons")}
    assert {"project_code","source_type","source_id","problem","decision","outcome","effectiveness","status","evidence_document_ids","validated_by","validated_at"} <= cols
