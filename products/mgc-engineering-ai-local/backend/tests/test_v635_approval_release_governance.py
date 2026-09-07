from pathlib import Path

import pytest
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker

from app.core.runtime_contract import APP_VERSION, SCHEMA_VERSION
from app.core.config import Settings
from app.db import models  # noqa
from app.db.migrations import ensure_v635_schema
from app.db.models import (
    Document, DocumentStatus, EngineeringApprovalCase, EngineeringApprovalPolicy,
    EngineeringReleasePackage, ManufacturingLayout, Project, WorkInstruction,
)
from app.db.session import Base
from app.services.approval_governance import (
    create_release_package, decide_case, governance_dashboard, release_package,
    serialize_case, submit_case, submit_package,
)


def _factory(tmp_path: Path | None = None):
    url = "sqlite:///:memory:" if tmp_path is None else f"sqlite:///{tmp_path / 'v635.db'}"
    eng = create_engine(url)
    Base.metadata.create_all(eng)
    return eng, sessionmaker(bind=eng, expire_on_commit=False)


def _seed(db):
    db.add(Project(code="P1", name="Car", acl_groups=["engineering-ai-users","engineering-ai-admins"]))
    wi = WorkInstruction(project_code="P1", manufacturing_area="assembly", code="WI1", title="Install", revision="B", status="approved", source_language="ru", translation_status="not_required", created_by="maker")
    layout = ManufacturingLayout(project_code="P1", manufacturing_area="assembly", code="LAY1", title="Assembly", revision="B", status="approved", created_by="maker")
    doc = Document(filename="bom.xlsx", stored_path="/tmp/bom.xlsx", sha256="a"*64, status=DocumentStatus.ready, project_code="P1", manufacturing_area="assembly", doc_type="bom", part_number="P100", revision="B", acl_groups=["engineering-ai-users"])
    db.add_all([wi,layout,doc]); db.commit()
    return wi,layout,doc


def test_v635_schema_marker_and_tables_are_idempotent():
    eng,_=_factory(); ensure_v635_schema(eng); ensure_v635_schema(eng)
    with eng.begin() as conn: assert conn.execute(text("SELECT schema_version FROM mgc_schema_state WHERE id=1")).scalar_one()=="6.3.5"
    tables=set(inspect(eng).get_table_names())
    assert {"engineering_approval_policies","engineering_approval_cases","engineering_approval_records","engineering_release_packages","engineering_release_package_items"}.issubset(tables)
    assert APP_VERSION=="6.3.34" and SCHEMA_VERSION=="6.3.13"
    assert Settings().allow_legacy_direct_wi_approval is False


def test_default_four_eyes_blocks_maker_and_requires_distinct_approvers():
    _,Factory=_factory()
    with Factory() as db:
        wi,_,_=_seed(db)
        case=submit_case(db,entity_type="work_instruction",entity_id=wi.id,project_code="P1",manufacturing_area="assembly",submitted_by="maker")
        with pytest.raises(PermissionError): decide_case(db,case,user="maker",groups=["engineering-ai-users"],is_admin=False,decision="approved",comment=None)
        case=decide_case(db,case,user="reviewer",groups=["engineering-ai-users"],is_admin=False,decision="approved",comment="ok")
        assert case.status=="pending"
        with pytest.raises(PermissionError): decide_case(db,case,user="reviewer",groups=["engineering-ai-admins"],is_admin=True,decision="approved",comment="same person")
        case=decide_case(db,case,user="admin2",groups=["engineering-ai-admins"],is_admin=True,decision="approved",comment="release")
        assert case.status=="approved"
        assert serialize_case(db,case)["approval_chain_integrity_valid"] is True


def test_area_specific_policy_snapshot_is_frozen_for_case():
    _,Factory=_factory()
    with Factory() as db:
        wi,_,_=_seed(db)
        p=EngineeringApprovalPolicy(project_code="P1",manufacturing_area="assembly",entity_type="work_instruction",name="Assembly WI",stages_json=[{"key":"final","label":"Final","required_role":"engineering_admin","required_groups":[]}],created_by="admin")
        db.add(p); db.commit()
        case=submit_case(db,entity_type="work_instruction",entity_id=wi.id,project_code="P1",manufacturing_area="assembly",submitted_by="maker")
        assert case.policy_id==p.id and case.policy_snapshot_json["name"]=="Assembly WI"
        p.stages_json=[{"key":"changed","label":"Changed","required_role":"engineering_admin","required_groups":[]}]; db.commit()
        assert db.get(EngineeringApprovalCase,case.id).policy_snapshot_json["stages"][0]["key"]=="final"


def test_release_package_requires_approved_items_and_rejects_drift():
    _,Factory=_factory()
    with Factory() as db:
        wi,layout,doc=_seed(db)
        pkg=create_release_package(db,project_code="P1",manufacturing_area="assembly",code="REL-1",title="SOP pack",source_change_id=None,items=[("work_instruction",wi.id),("manufacturing_layout",layout.id),("document",doc.id)],metadata={},user="maker")
        pkg,case=submit_package(db,pkg,"maker")
        assert pkg.status=="in_review" and case.status=="pending"
        decide_case(db,case,user="reviewer",groups=["engineering-ai-users"],is_admin=False,decision="approved",comment="ok")
        decide_case(db,case,user="admin",groups=["engineering-ai-admins"],is_admin=True,decision="approved",comment="ok")
        wi.title="Changed after approval"; db.commit()
        with pytest.raises(ValueError,match="changed after approval"): release_package(db,pkg,"admin",True)


def test_release_supersedes_old_mgc_revision_but_never_mutates_bom_authority():
    _,Factory=_factory()
    with Factory() as db:
        wi,layout,doc=_seed(db)
        old=WorkInstruction(project_code="P1",manufacturing_area="assembly",code="WI1",title="Old",revision="A",status="approved",source_language="ru",translation_status="not_required",created_by="oldmaker")
        db.add(old); db.commit()
        pkg=create_release_package(db,project_code="P1",manufacturing_area="assembly",code="REL-2",title="SOP pack",source_change_id=None,items=[("work_instruction",wi.id),("manufacturing_layout",layout.id),("document",doc.id)],metadata={},user="maker")
        pkg,case=submit_package(db,pkg,"maker")
        decide_case(db,case,user="reviewer",groups=["engineering-ai-users"],is_admin=False,decision="approved",comment=None)
        decide_case(db,case,user="admin",groups=["engineering-ai-admins"],is_admin=True,decision="approved",comment=None)
        pkg=release_package(db,pkg,"admin",True)
        db.refresh(old); db.refresh(doc)
        assert pkg.status=="released" and old.status=="obsolete"
        assert doc.status==DocumentStatus.ready and doc.sha256=="a"*64


def test_release_package_cannot_bypass_object_approval():
    _,Factory=_factory()
    with Factory() as db:
        wi,_,_=_seed(db); wi.status="draft"; db.commit()
        pkg=create_release_package(db,project_code="P1",manufacturing_area="assembly",code="REL-3",title="Bad pack",source_change_id=None,items=[("work_instruction",wi.id)],metadata={},user="maker")
        with pytest.raises(ValueError,match="must be approved"): submit_package(db,pkg,"maker")


def test_governance_dashboard_is_explicit_about_signature_boundary():
    _,Factory=_factory()
    with Factory() as db:
        _seed(db)
        out=governance_dashboard(db)
        assert out["qualified_electronic_signature"] is False
        assert out["record_type"]=="tamper_evident_engineering_approval_evidence"
