from sqlalchemy import create_engine, inspect, text

from app.db import models  # noqa: F401
from app.db.migrations import ensure_v41_schema
from app.db.session import Base


def test_v41_core_tools_upgrade_is_additive_and_preserves_existing_project():
    engine = create_engine("sqlite:///:memory:")
    with engine.begin() as conn:
        conn.execute(text("CREATE TABLE projects (id VARCHAR(36) PRIMARY KEY, code VARCHAR(64), name VARCHAR(255), acl_groups JSON, created_at DATETIME)"))
        conn.execute(text("INSERT INTO projects (id,code,name,acl_groups,created_at) VALUES ('1','OLD','Existing','[\"engineering-ai-users\"]','2026-09-04')"))
    # Production startup creates newly introduced tables first, then runs additive legacy column upgrades.
    Base.metadata.create_all(engine, checkfirst=True)
    ensure_v41_schema(engine); ensure_v41_schema(engine)
    tables=set(inspect(engine).get_table_names())
    assert {"apqp_deliverables","special_characteristics","pfmea_items","control_plan_items","ppap_submissions","problems_8d"} <= tables
    with engine.begin() as conn:
        assert conn.execute(text("SELECT name FROM projects WHERE code='OLD'")) .scalar_one() == "Existing"
