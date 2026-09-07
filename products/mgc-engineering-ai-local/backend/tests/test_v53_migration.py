from sqlalchemy import create_engine, inspect
from app.db.session import Base
from app.db import models  # noqa
from app.db.migrations import ensure_v53_schema


def test_v53_schema_wrapper_is_additive_and_idempotent():
    engine=create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    ensure_v53_schema(engine); ensure_v53_schema(engine)
    tables=set(inspect(engine).get_table_names())
    assert {"engineering_decision_records","production_feedback","change_effectiveness_reviews","engineering_deviations","engineering_risks"}.issubset(tables)
