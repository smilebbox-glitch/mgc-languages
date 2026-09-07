from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker

from app.core.config import Settings
from app.core.runtime_contract import APP_VERSION, SCHEMA_VERSION
from app.core.security import Identity, identity_snapshot
from app.db import models  # noqa: F401
from app.db.migrations import ensure_v636_schema
from app.db.models import (
    EngineeringIdentityDelegation, EngineeringIdentityPolicy, Project, WorkInstruction,
)
from app.db.session import Base
from app.services.approval_governance import decide_case, release_manifest, serialize_case, submit_case, create_release_package
from app.services.identity_policy import enforce_identity_policy


def _factory():
    eng=create_engine("sqlite:///:memory:")
    Base.metadata.create_all(eng)
    return eng, sessionmaker(bind=eng, expire_on_commit=False)


def _seed(db):
    db.add(Project(code="P1",name="Car",acl_groups=["engineering-ai-users","engineering-ai-admins","assembly-reviewers"]))
    wi=WorkInstruction(project_code="P1",manufacturing_area="assembly",code="WI1",title="Install",revision="A",status="approved",source_language="ru",translation_status="not_required",created_by="maker")
    db.add(wi); db.commit(); return wi


def test_v636_schema_marker_identity_tables_and_evidence_columns_are_idempotent():
    eng,_=_factory(); ensure_v636_schema(eng); ensure_v636_schema(eng)
    with eng.begin() as conn:
        assert conn.execute(text("SELECT schema_version FROM mgc_schema_state WHERE id=1")).scalar_one()=="6.3.6"
    tables=set(inspect(eng).get_table_names())
    assert {"engineering_identity_policies","engineering_identity_delegations"}.issubset(tables)
    cols={x["name"] for x in inspect(eng).get_columns("engineering_approval_records")}
    assert {"identity_snapshot_json","assurance_json"}.issubset(cols)
    assert APP_VERSION=="6.3.34" and SCHEMA_VERSION=="6.3.13"


def test_scoped_identity_policy_denies_then_allows_required_group():
    _,Factory=_factory()
    with Factory() as db:
        _seed(db)
        p=EngineeringIdentityPolicy(project_code="P1",manufacturing_area="assembly",entity_type="work_instruction",action="approval_decision",name="Assembly reviewers",allowed_groups_json=["assembly-reviewers"],created_by="admin")
        db.add(p); db.commit()
        with pytest.raises(PermissionError,match="allowed group"):
            enforce_identity_policy(db,Identity("u",["engineering-ai-users"]),action="approval_decision",project_code="P1",manufacturing_area="assembly",entity_type="work_instruction")
        out=enforce_identity_policy(db,Identity("u",["engineering-ai-users","assembly-reviewers"]),action="approval_decision",project_code="P1",manufacturing_area="assembly",entity_type="work_instruction")
        assert out.allowed and out.policy_id==p.id


def test_service_account_cannot_perform_human_approval_even_if_group_matches():
    _,Factory=_factory()
    with Factory() as db:
        _seed(db)
        db.add(EngineeringIdentityPolicy(action="approval_decision",name="human",allowed_groups_json=["assembly-reviewers"],allow_service_accounts=True,created_by="admin")); db.commit()
        identity=Identity("svc",["assembly-reviewers"],subject="svc",auth_mode="oidc",is_service_account=True)
        with pytest.raises(PermissionError,match="Human identity"):
            enforce_identity_policy(db,identity,action="approval_decision")


def test_controlled_delegation_can_add_non_admin_stage_group_only_when_policy_allows():
    _,Factory=_factory()
    with Factory() as db:
        _seed(db); now=datetime.now(timezone.utc)
        p=EngineeringIdentityPolicy(project_code="P1",manufacturing_area="assembly",entity_type="work_instruction",action="approval_decision",name="delegation",allowed_groups_json=["assembly-reviewers"],delegation_allowed=True,created_by="admin")
        d=EngineeringIdentityDelegation(delegator="reviewer",delegate="standin",project_code="P1",manufacturing_area="assembly",entity_type="work_instruction",actions_json=["approval_decision"],delegated_groups_json=["assembly-reviewers","engineering-ai-admins"],valid_from=now-timedelta(minutes=1),valid_until=now+timedelta(hours=2),reason="absence",created_by="admin")
        db.add_all([p,d]); db.commit()
        out=enforce_identity_policy(db,Identity("standin",["engineering-ai-users"]),action="approval_decision",project_code="P1",manufacturing_area="assembly",entity_type="work_instruction",allow_delegation=True)
        assert "assembly-reviewers" in out.effective_groups
        assert "engineering-ai-admins" not in out.effective_groups
        assert out.delegation_ids==[d.id]


def test_production_privileged_action_requires_oidc_and_fresh_authentication(monkeypatch):
    import app.services.identity_policy as ip
    cfg=Settings(app_env="production",privileged_actions_require_oidc_in_prod=True,privileged_reauth_max_age_seconds=900,engineering_admin_groups="engineering-ai-admins")
    monkeypatch.setattr(ip,"get_settings",lambda: cfg)
    _,Factory=_factory()
    with Factory() as db:
        _seed(db); now=int(datetime.now(timezone.utc).timestamp())
        with pytest.raises(PermissionError,match="OIDC"):
            enforce_identity_policy(db,Identity("admin",["engineering-ai-admins"],auth_mode="api_key"),action="release_package_release")
        with pytest.raises(PermissionError,match="too old"):
            enforce_identity_policy(db,Identity("admin",["engineering-ai-admins"],auth_mode="oidc",auth_time=now-3600),action="release_package_release")
        out=enforce_identity_policy(db,Identity("admin",["engineering-ai-admins"],auth_mode="oidc",auth_time=now-60),action="release_package_release")
        assert out.assurance["auth_age_seconds"] <= 120


def test_approval_evidence_binds_sanitized_identity_and_assurance_snapshot():
    _,Factory=_factory()
    with Factory() as db:
        wi=_seed(db)
        submit_id=Identity("maker",["engineering-ai-users"],subject="sub-maker",auth_mode="oidc",issuer="https://idp",acr="mfa")
        case=submit_case(db,entity_type="work_instruction",entity_id=wi.id,project_code="P1",manufacturing_area="assembly",submitted_by="maker",submitted_identity=identity_snapshot(submit_id))
        case=decide_case(db,case,user="reviewer",groups=["engineering-ai-users"],is_admin=False,decision="approved",comment="ok",identity_snapshot_payload={"user":"reviewer","subject":"sub-r"},assurance_payload={"acr":"mfa","identity_policy_id":"P"})
        out=serialize_case(db,case)
        assert out["submitted_identity"]["subject"]=="sub-maker"
        assert out["records"][0]["identity"]["subject"]=="sub-r"
        assert out["records"][0]["assurance"]["identity_policy_id"]=="P"


def test_release_manifest_is_handover_only_and_hashes_canonical_content():
    _,Factory=_factory()
    with Factory() as db:
        wi=_seed(db)
        pkg=create_release_package(db,project_code="P1",manufacturing_area="assembly",code="REL1",title="Release",source_change_id=None,items=[("work_instruction",wi.id)],metadata={},user="maker")
        out=release_manifest(db,pkg)
        assert out["manifest"]["production_writeback"] is False
        assert out["manifest"]["items"][0]["snapshot_sha256"]
        assert len(out["manifest_sha256"])==64
        assert out["qualified_electronic_signature"] is False
