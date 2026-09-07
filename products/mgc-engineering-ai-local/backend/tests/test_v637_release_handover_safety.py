from __future__ import annotations

from datetime import datetime, timezone
import pytest
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import DatabaseError
from sqlalchemy.orm import sessionmaker

from app.core.config import Settings
from app.core.runtime_contract import APP_VERSION, SCHEMA_VERSION
from app.core.security import Identity
from app.db import models  # noqa: F401
from app.db.migrations import ensure_v637_schema
from app.db.models import ExternalSystem, EngineeringHandoverJob, EngineeringHandoverTarget, EngineeringReleasePackage, Project
from app.db.session import Base
from app.ports.handover import HandoverDeliveryResult
from app.services.engineering_handover import create_target, create_job, authorize_job, execute_job, reconcile_job, handover_dashboard


def _factory():
    eng=create_engine("sqlite:///:memory:")
    Base.metadata.create_all(eng)
    return eng, sessionmaker(bind=eng, expire_on_commit=False)


def _seed(db):
    db.add(Project(code="P1",name="Car",acl_groups=["engineering-ai-users","engineering-ai-admins"]))
    system=ExternalSystem(code="mes-gw",name="MES Gateway",connector_type="mes_rest",enabled=True,config_json={"base_url":"https://mes.internal"},secret_config_json={},acl_groups=["engineering-ai-admins"],source_domain="mes")
    db.add(system); db.flush()
    target=create_target(db,code="mes-pilot",name="MES Pilot",external_system_id=system.id,environment="pilot",allow_write=True,write_path="/api/mgc/releases",reconcile_path_template="/api/mgc/releases/{receipt_id}",allowed_projects=["P1"],allowed_areas=["assembly"],metadata={},user="admin")
    pkg=EngineeringReleasePackage(project_code="P1",manufacturing_area="assembly",code="REL1",title="Release",status="released",release_sha256="a"*64,created_by="maker",released_by="release-admin",released_at=datetime.now(timezone.utc))
    db.add(pkg); db.commit()
    return system,target,pkg


class FakeAdapter:
    def execute(self, **kwargs):
        assert kwargs["headers"]["Idempotency-Key"]
        assert kwargs["payload"]["machine_control"] is False
        return HandoverDeliveryResult(ok=True,status="accepted",external_receipt_id="MES-R-42",response={"receipt_id":"MES-R-42","accepted":True})
    def reconcile(self, **kwargs):
        return HandoverDeliveryResult(ok=True,status="reconciled",external_receipt_id=kwargs["external_receipt_id"],response={"status":"reconciled","manifest_sha256":kwargs["headers"]["X-MGC-Manifest-SHA256"]},target_state_sha256="b"*64)


def test_v637_schema_marker_tables_and_version_are_idempotent():
    eng,_=_factory(); ensure_v637_schema(eng); ensure_v637_schema(eng)
    with eng.begin() as conn:
        assert conn.execute(text("SELECT schema_version FROM mgc_schema_state WHERE id=1")).scalar_one()=="6.3.7"
    tables=set(inspect(eng).get_table_names())
    assert {"engineering_handover_targets","engineering_handover_jobs","engineering_handover_receipts"}.issubset(tables)
    assert APP_VERSION=="6.3.34" and SCHEMA_VERSION=="6.3.13"
    cfg=Settings()
    assert cfg.handover_write_enabled is False and cfg.handover_dry_run_default is True and cfg.handover_allowed_target_code_set==set() and cfg.handover_allowed_host_set==set()


def test_target_is_restricted_to_plm_pdm_mes_rest_gateways_and_relative_paths():
    _,Factory=_factory()
    with Factory() as db:
        bad=ExternalSystem(code="files",name="Files",connector_type="mounted_folder",enabled=True,config_json={},secret_config_json={},source_domain="files")
        db.add(bad); db.commit()
        with pytest.raises(ValueError,match="PLM/PDM/MES"):
            create_target(db,code="files-out",name="bad",external_system_id=bad.id,environment="test",allow_write=True,write_path="/write",reconcile_path_template=None,allowed_projects=[],allowed_areas=[],metadata={},user="admin")
        good=ExternalSystem(code="plm",name="PLM",connector_type="plm_rest",enabled=True,config_json={"base_url":"https://plm.internal"},secret_config_json={},source_domain="plm")
        db.add(good); db.commit()
        with pytest.raises(ValueError,match="relative"):
            create_target(db,code="plm-out",name="bad",external_system_id=good.id,environment="test",allow_write=True,write_path="https://evil.example/write",reconcile_path_template=None,allowed_projects=[],allowed_areas=[],metadata={},user="admin")


def test_dry_run_is_default_safe_and_idempotency_key_cannot_be_reused_for_different_command():
    _,Factory=_factory()
    with Factory() as db:
        _,target,pkg=_seed(db)
        maker=Identity("maker",["engineering-ai-users"],subject="maker")
        job=create_job(db,package_id=pkg.id,target_code=target.code,idempotency_key="req-00000001",mode="dry_run",identity=maker)
        assert job.status=="dry_run_ready" and job.mode=="dry_run" and len(job.request_sha256)==64
        same=create_job(db,package_id=pkg.id,target_code=target.code,idempotency_key="req-00000001",mode="dry_run",identity=maker)
        assert same.id==job.id
        with pytest.raises(ValueError,match="different handover command"):
            create_job(db,package_id=pkg.id,target_code=target.code,idempotency_key="req-00000001",mode="write",identity=maker)


def test_write_job_requires_distinct_human_checker():
    _,Factory=_factory()
    with Factory() as db:
        _,target,pkg=_seed(db)
        maker=Identity("maker",["engineering-ai-users"])
        job=create_job(db,package_id=pkg.id,target_code=target.code,idempotency_key="write-000001",mode="write",identity=maker)
        assert job.status=="pending_authorization"
        with pytest.raises(PermissionError,match="creator cannot authorize"):
            authorize_job(db,job,identity=maker,identity_policy_id=None,assurance={})
        with pytest.raises(PermissionError,match="Human checker"):
            authorize_job(db,job,identity=Identity("svc",["engineering-ai-admins"],is_service_account=True),identity_policy_id=None,assurance={})
        checker=Identity("checker",["engineering-ai-admins"],auth_mode="oidc",subject="sub-checker")
        authorize_job(db,job,identity=checker,identity_policy_id="POL",assurance={"acr":"mfa"})
        assert job.status=="authorized" and job.checker_user=="checker" and job.checker_assurance_json["identity_policy_id"]=="POL"


def test_write_is_fail_closed_until_global_target_and_allowlist_gates_are_all_enabled(monkeypatch):
    import app.services.engineering_handover as eh
    _,Factory=_factory()
    with Factory() as db:
        _,target,pkg=_seed(db)
        maker=Identity("maker",["engineering-ai-users"]); checker=Identity("checker",["engineering-ai-admins"],auth_mode="oidc")
        job=create_job(db,package_id=pkg.id,target_code=target.code,idempotency_key="write-000002",mode="write",identity=maker)
        authorize_job(db,job,identity=checker,identity_policy_id=None,assurance={})
        monkeypatch.setattr(eh,"get_settings",lambda:Settings(handover_write_enabled=False,handover_allowed_target_codes="mes-pilot",handover_allowed_hosts="mes.internal"))
        with pytest.raises(PermissionError,match="globally disabled"):
            execute_job(db,job,identity=checker,adapter=FakeAdapter())
        monkeypatch.setattr(eh,"get_settings",lambda:Settings(handover_write_enabled=True,handover_allowed_target_codes="",handover_allowed_hosts="mes.internal"))
        with pytest.raises(PermissionError,match="HANDOVER_ALLOWED_TARGET_CODES"):
            execute_job(db,job,identity=checker,adapter=FakeAdapter())


def test_controlled_execute_records_receipt_and_reconciliation(monkeypatch):
    import app.services.engineering_handover as eh
    _,Factory=_factory()
    with Factory() as db:
        _,target,pkg=_seed(db)
        maker=Identity("maker",["engineering-ai-users"]); checker=Identity("checker",["engineering-ai-admins"],auth_mode="oidc",subject="sub-checker")
        job=create_job(db,package_id=pkg.id,target_code=target.code,idempotency_key="write-000003",mode="write",identity=maker)
        authorize_job(db,job,identity=checker,identity_policy_id=None,assurance={"acr":"mfa"})
        monkeypatch.setattr(eh,"get_settings",lambda:Settings(handover_write_enabled=True,handover_allowed_target_codes="mes-pilot",handover_allowed_hosts="mes.internal"))
        job=execute_job(db,job,identity=checker,adapter=FakeAdapter())
        assert job.status=="delivered" and job.external_receipt_id=="MES-R-42" and job.executed_by=="checker" and job.response_sha256
        job=reconcile_job(db,job,identity=checker,adapter=FakeAdapter())
        assert job.status=="reconciled" and job.reconciliation_json["status"]=="reconciled"


def test_database_rejects_mutating_immutable_handover_command_fields():
    eng,Factory=_factory(); ensure_v637_schema(eng)
    with Factory() as db:
        _,target,pkg=_seed(db)
        job=create_job(db,package_id=pkg.id,target_code=target.code,idempotency_key="immutable-01",mode="dry_run",identity=Identity("maker",["engineering-ai-users"]))
        with pytest.raises(Exception):
            db.execute(text("UPDATE engineering_handover_jobs SET request_sha256=:x WHERE id=:id"),{"x":"f"*64,"id":job.id}); db.commit()
        db.rollback()
        assert db.get(EngineeringHandoverJob,job.id).request_sha256==job.request_sha256


def test_handover_dashboard_warns_on_failed_or_stale_unreconciled_jobs():
    _,Factory=_factory()
    with Factory() as db:
        _,target,pkg=_seed(db)
        job=create_job(db,package_id=pkg.id,target_code=target.code,idempotency_key="ops-00000001",mode="write",identity=Identity("maker",["engineering-ai-users"]))
        assert handover_dashboard(db)["operational_status"]=="OK"
        job.status="failed"; db.commit()
        snap=handover_dashboard(db)
        assert snap["failed"]==1 and snap["operational_status"]=="WARN"
        assert snap["machine_control"] is False
