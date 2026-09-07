
from app.db import models  # noqa: F401
from sqlalchemy import create_engine, inspect
from app.db.session import Base
from app.db.migrations import ensure_v58_schema


def test_v58_schema_wrapper_is_additive_and_idempotent():
    engine=create_engine('sqlite:///:memory:')
    Base.metadata.create_all(engine)
    ensure_v58_schema(engine); ensure_v58_schema(engine)
    insp=inspect(engine); tables=set(insp.get_table_names())
    assert {'design_fmea_items','field_reliability_exposures','field_service_actions','field_quality_claims'}.issubset(tables)
    cols={x['name'] for x in insp.get_columns('field_quality_claims')}
    assert {'failure_family','mileage_km','market','climate_zone','repeat_repair','source_system'}.issubset(cols)
    assert {'series_quality_observations','vehicle_builds'}.issubset(tables)
