from __future__ import annotations

from datetime import datetime, timezone
import pytest
from sqlalchemy import create_engine, inspect, select, text
from sqlalchemy.orm import sessionmaker

from app.core.config import Settings
from app.core.runtime_contract import APP_VERSION, SCHEMA_VERSION
from app.core.security import Identity
from app.db import models  # noqa: F401
from app.db.migrations import ensure_v638_schema
from app.db.models import (
    Document, DocumentSearchChunk, EngineeringDataLifecycleState, EngineeringLegalHold,
    EngineeringLifecycleEvent, EngineeringReleasePackage, EngineeringRetentionPolicy, Project,
)
from app.db.session import Base
from app.services.data_lifecycle import (
    archive_entity, authorize_purge, create_policy, create_purge_request, enforce_upload_quota,
    execute_purge, evidence_lineage, lifecycle_dashboard, place_hold, release_hold, storage_usage,
)


def _factory():
    eng=create_engine("sqlite:///:memory:")
    Base.metadata.create_all(eng)
    return eng, sessionmaker(bind=eng, expire_on_commit=False)


def _seed_document(db):
    db.add(Project(code="P1",name="Car",acl_groups=["engineering-ai-admins"]))
    doc=Document(filename="WI.pdf",stored_path="/tmp/nonexistent-v638.pdf",mime_type="application/pdf",extension=".pdf",size_bytes=1024,sha256="a"*64,project_code="P1",manufacturing_area="assembly",acl_groups=["engineering-ai-admins"])
    db.add(doc); db.flush()
    db.add(DocumentSearchChunk(document_id=doc.id,chunk_index=0,text="authoritative chunk",content_sha256="b"*64,metadata_json={}))
    db.commit(); return doc


class _Search:
    mode="fake_search"
    def __init__(self): self.deleted=[]
    def delete_document(self,document_id): self.deleted.append(document_id)

class _Graph:
    mode="fake_graph"
    def __init__(self): self.deleted=[]
    def delete_document(self,document_id): self.deleted.append(document_id); return {"enabled":True,"deleted":1,"adapter":self.mode}


def test_v638_schema_marker_tables_and_safe_defaults_are_idempotent():
    eng,_=_factory(); ensure_v638_schema(eng); ensure_v638_schema(eng)
    with eng.begin() as conn:
        assert conn.execute(text("SELECT schema_version FROM mgc_schema_state WHERE id=1")).scalar_one()=="6.3.8"
    tables=set(inspect(eng).get_table_names())
    assert {"engineering_retention_policies","engineering_legal_holds","engineering_data_lifecycle_states","engineering_purge_requests","engineering_lifecycle_events"}.issubset(tables)
    assert APP_VERSION=="6.3.34" and SCHEMA_VERSION=="6.3.13"
    cfg=Settings(); assert cfg.data_lifecycle_authoritative_purge_enabled is False and cfg.data_lifecycle_project_quota_mb==0


def test_retention_policy_storage_usage_and_quota_gate(monkeypatch):
    import app.services.data_lifecycle as dl
    _,Factory=_factory()
    with Factory() as db:
        _seed_document(db)
        row=create_policy(db,name="Documents 10y",entity_type="document",project_code="P1",manufacturing_area=None,archive_after_days=365,retain_for_days=3650,immutable_min_days=0,allow_authoritative_purge=False,created_by="admin")
        assert isinstance(row,EngineeringRetentionPolicy)
        usage=storage_usage(db,project_code="P1"); assert usage["bytes"]==1024 and usage["documents"]==1
        monkeypatch.setattr(dl,"get_settings",lambda:Settings(data_lifecycle_project_quota_mb=1))
        enforce_upload_quota(db,project_code="P1",manufacturing_area=None,incoming_bytes=100)
        with pytest.raises(PermissionError,match="quota exceeded"):
            enforce_upload_quota(db,project_code="P1",manufacturing_area=None,incoming_bytes=2*1024*1024)


def test_legal_hold_blocks_purge_until_controlled_release():
    _,Factory=_factory()
    with Factory() as db:
        doc=_seed_document(db); maker=Identity("maker",["engineering-ai-admins"])
        hold=place_hold(db,hold_code="CASE-001",project_code="P1",manufacturing_area="assembly",entity_type="document",entity_id=doc.id,reason="Regulatory investigation",expires_at=None,user="legal-admin")
        assert isinstance(hold,EngineeringLegalHold) and hold.active
        with pytest.raises(PermissionError,match="legal hold"):
            create_purge_request(db,entity_type="document",entity_id=doc.id,purge_scope="projections_only",reason="cleanup",identity=maker)
        release_hold(db,hold,user="legal-admin-2",reason="case closed")
        req=create_purge_request(db,entity_type="document",entity_id=doc.id,purge_scope="projections_only",reason="cleanup",identity=maker)
        assert req.status=="pending_authorization"


def test_projection_purge_is_four_eyes_and_preserves_authoritative_chunks(monkeypatch):
    import app.services.data_lifecycle as dl
    _,Factory=_factory(); search=_Search(); graph=_Graph()
    monkeypatch.setattr(dl,"get_search_port",lambda:search); monkeypatch.setattr(dl,"get_graph_projection_port",lambda:graph)
    with Factory() as db:
        doc=_seed_document(db); maker=Identity("maker",["engineering-ai-admins"]); checker=Identity("checker",["engineering-ai-admins"])
        req=create_purge_request(db,entity_type="document",entity_id=doc.id,purge_scope="projections_only",reason="rebuild projection",identity=maker)
        with pytest.raises(PermissionError,match="cannot authorize"):
            authorize_purge(db,req,identity=maker)
        authorize_purge(db,req,identity=checker)
        with pytest.raises(PermissionError,match="Maker cannot execute"):
            execute_purge(db,req,identity=maker)
        execute_purge(db,req,identity=checker)
        assert req.status=="executed" and req.result_json["postgresql_authoritative_preserved"] is True
        assert search.deleted==[doc.id] and graph.deleted==[doc.id]
        assert db.get(Document,doc.id) is not None
        assert db.scalar(select(DocumentSearchChunk).where(DocumentSearchChunk.document_id==doc.id)) is not None
        state=db.scalar(select(EngineeringDataLifecycleState).where(EngineeringDataLifecycleState.entity_id==doc.id)); assert state.state=="projections_purged"


def test_purge_snapshot_becomes_stale_after_entity_change(monkeypatch):
    import app.services.data_lifecycle as dl
    monkeypatch.setattr(dl,"get_search_port",lambda:_Search()); monkeypatch.setattr(dl,"get_graph_projection_port",lambda:_Graph())
    _,Factory=_factory()
    with Factory() as db:
        doc=_seed_document(db); maker=Identity("maker",["engineering-ai-admins"]); checker=Identity("checker",["engineering-ai-admins"])
        req=create_purge_request(db,entity_type="document",entity_id=doc.id,purge_scope="projections_only",reason="cleanup",identity=maker); authorize_purge(db,req,identity=checker)
        doc.filename="changed.pdf"; db.commit()
        with pytest.raises(ValueError,match="changed after purge authorization"):
            execute_purge(db,req,identity=checker)


def test_released_package_is_never_a_normal_purge_target():
    _,Factory=_factory()
    with Factory() as db:
        db.add(Project(code="P1",name="Car",acl_groups=["engineering-ai-admins"])); pkg=EngineeringReleasePackage(project_code="P1",manufacturing_area="assembly",code="REL",title="Released",status="released",release_sha256="c"*64,created_by="a",released_by="b",released_at=datetime.now(timezone.utc)); db.add(pkg); db.commit()
        with pytest.raises(PermissionError,match="immutable retention evidence"):
            create_purge_request(db,entity_type="release_package",entity_id=pkg.id,purge_scope="authoritative",reason="should not happen",identity=Identity("admin",["engineering-ai-admins"]))


def test_archive_and_lineage_preserve_source_record_and_hash_chained_history():
    eng,Factory=_factory(); ensure_v638_schema(eng)
    with Factory() as db:
        doc=_seed_document(db); admin=Identity("admin",["engineering-ai-admins"])
        state=archive_entity(db,entity_type="document",entity_id=doc.id,identity=admin,reason="cold archive")
        assert state.state=="archived" and db.get(Document,doc.id) is not None
        lineage=evidence_lineage(db,entity_type="document",entity_id=doc.id); assert lineage["lifecycle"][-1]["action"]=="ARCHIVED"
        ev=db.scalar(select(EngineeringLifecycleEvent).where(EngineeringLifecycleEvent.entity_id==doc.id))
        with pytest.raises(Exception):
            db.execute(text("UPDATE engineering_lifecycle_events SET action='TAMPER' WHERE id=:id"),{"id":ev.id}); db.commit()
        db.rollback(); assert db.get(EngineeringLifecycleEvent,ev.id).action=="ARCHIVED"


def test_lifecycle_dashboard_is_fail_closed_for_authoritative_purge():
    _,Factory=_factory()
    with Factory() as db:
        _seed_document(db)
        snap=lifecycle_dashboard(db)
        assert snap["authoritative_purge_enabled"] is False
        assert snap["released_packages_immutable"] is True
        assert snap["projection_purge_preserves_postgresql_chunks"] is True
        assert snap["machine_control"] is False
