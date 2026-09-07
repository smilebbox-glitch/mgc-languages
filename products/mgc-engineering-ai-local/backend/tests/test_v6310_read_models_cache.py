from __future__ import annotations

from sqlalchemy import create_engine, inspect, select, text
from sqlalchemy.orm import sessionmaker

from app.core.config import Settings
from app.core.runtime_contract import APP_VERSION, SCHEMA_VERSION
from app.db import models  # noqa
from app.db.migrations import ensure_v6310_schema
from app.db.models import EngineeringReadModel, ManufacturingLine, ProcessStation, ProjectionOutboxEvent, Project, WorkInstruction
from app.db.session import Base
from app.services.projection_outbox import process_projection_event
from app.services.read_models import acl_fingerprint, etag_for_payload, get_wi_coverage_read_model, invalidate_read_models, pending_read_model_invalidation
from app.services.read_model_hooks import install_read_model_invalidation_hooks


def _factory():
    eng=create_engine("sqlite:///:memory:")
    Base.metadata.create_all(eng)
    return eng, sessionmaker(bind=eng, expire_on_commit=False)


def _seed(db):
    db.add(Project(code="P1",name="Car",acl_groups=["engineering-ai-users"]))
    line=ManufacturingLine(project_code="P1",manufacturing_area="assembly",code="L1",name="Line 1")
    db.add(line); db.flush()
    station=ProcessStation(line_id=line.id,code="ST10",name="Station 10",headcount=1)
    db.add(station); db.flush()
    wi=WorkInstruction(project_code="P1",manufacturing_area="assembly",line_id=line.id,station_id=station.id,code="WI-1",title="Install",revision="A",status="approved",source_language="ru",steps_json=[{"text":"Install part"}])
    db.add(wi); db.commit()
    return wi


def test_v6310_schema_marker_and_rebuildable_table_are_idempotent():
    eng,_=_factory(); ensure_v6310_schema(eng); ensure_v6310_schema(eng)
    with eng.begin() as conn:
        assert conn.execute(text("SELECT schema_version FROM mgc_schema_state WHERE id=1")).scalar_one()=="6.3.10"
    assert "engineering_read_models" in set(inspect(eng).get_table_names())
    assert APP_VERSION=="6.3.34" and SCHEMA_VERSION=="6.3.13"


def test_safe_wi_coverage_read_model_persists_only_aggregates():
    _,Factory=_factory()
    with Factory() as db:
        _seed(db)
        payload=get_wi_coverage_read_model(db,"P1","assembly")
        assert payload["counts"]["stations"]==1 and payload["counts"]["approved_instructions"]==1
        row=db.scalar(select(EngineeringReadModel))
        assert row.status=="fresh" and row.payload_sha256
        assert "Install part" not in str(row.payload_json)
        assert row.payload_json["authoritative"] is False and row.payload_json["rebuildable"] is True


def test_read_model_hit_is_stable_until_invalidated():
    _,Factory=_factory()
    with Factory() as db:
        _seed(db); first=get_wi_coverage_read_model(db,"P1","assembly"); second=get_wi_coverage_read_model(db,"P1","assembly")
        assert first["etag"]==second["etag"] and second["cache_state"]=="read_model_hit"
        assert invalidate_read_models(db,project_code="P1",manufacturing_area="assembly")==1
        db.commit()
        third=get_wi_coverage_read_model(db,"P1","assembly")
        assert third["cache_state"]=="rebuilt"


def test_api_session_hook_enqueues_transactional_read_model_invalidation():
    install_read_model_invalidation_hooks(); _,Factory=_factory()
    with Factory() as db:
        db.info["mgc_read_model_invalidation_enabled"]=True
        _seed(db)
        rows=db.scalars(select(ProjectionOutboxEvent).where(ProjectionOutboxEvent.target=="read_model")).all()
        assert rows and all(x.event_type=="read_model_invalidate" for x in rows)


def test_pending_invalidation_forces_cache_bypass_signal():
    _,Factory=_factory()
    with Factory() as db:
        db.add(ProjectionOutboxEvent(idempotency_key="k"*64,target="read_model",event_type="read_model_invalidate",aggregate_type="read_model",aggregate_id="P1:assembly",source_version="v1",payload_json={"project_code":"P1","manufacturing_area":"assembly"},status="pending"))
        db.commit(); assert pending_read_model_invalidation(db) is True


def test_read_model_outbox_delivery_marks_snapshot_stale_without_touching_authoritative_data():
    _,Factory=_factory()
    with Factory() as db:
        _seed(db); get_wi_coverage_read_model(db,"P1","assembly")
        event=ProjectionOutboxEvent(idempotency_key="z"*64,target="read_model",event_type="read_model_invalidate",aggregate_type="read_model",aggregate_id="P1:assembly",source_version="v2",payload_json={"project_code":"P1","manufacturing_area":"assembly","cache_prefix":"mgc:v6310:"},status="processing")
        db.add(event); db.commit(); eid=event.id
        out=process_projection_event(db,eid)
        assert out["status"]=="succeeded"
        assert db.scalar(select(EngineeringReadModel)).status=="stale"
        assert db.scalar(select(WorkInstruction)).title=="Install"


def test_acl_fingerprint_and_etag_are_deterministic_and_scope_sensitive():
    a=acl_fingerprint({"D1","D2"},["g1"]); b=acl_fingerprint({"D2","D1"},["g1"]); c=acl_fingerprint({"D1"},["g1"])
    assert a==b and a!=c
    assert etag_for_payload({"b":2,"a":1})==etag_for_payload({"a":1,"b":2})


def test_cache_defaults_are_acceleration_only():
    cfg=Settings()
    assert cfg.read_model_enabled is True and cfg.read_model_cache_enabled is True
    assert cfg.read_model_cache_ttl_seconds > 0
    assert cfg.read_model_pending_invalidation_bypass is True
