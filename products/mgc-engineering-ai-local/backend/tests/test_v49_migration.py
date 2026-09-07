from sqlalchemy import create_engine, inspect
from app.db.session import Base
from app.db import models  # noqa
from app.db.migrations import ensure_v49_schema


def test_v49_schema_is_idempotent_and_has_release_and_bom_columns():
    engine=create_engine('sqlite:///:memory:')
    Base.metadata.create_all(engine)
    ensure_v49_schema(engine); ensure_v49_schema(engine)
    insp=inspect(engine)
    assert 'release_baselines' in set(insp.get_table_names())
    cols={x['name'] for x in insp.get_columns('bom_items')}
    assert {'position','supplier_code','supplier_name','unit_cost','currency'} <= cols
