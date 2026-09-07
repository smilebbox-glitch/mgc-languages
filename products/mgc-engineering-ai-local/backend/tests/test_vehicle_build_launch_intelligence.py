from datetime import datetime, timedelta, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db.models import (
    BuildDefectLink, BuildGenealogyItem, ChangeRequest, ConfigurationApplicability,
    Document, DocumentStatus, Part, Problem8D, ProcessDefect, Project, ProjectArea,
    SafeLaunchControl, VehicleBuild, VehicleVariant,
)
from app.db.session import Base
from app.services.vehicle_build_launch_intelligence import vehicle_build_launch_workspace, visible_build_rows


def _db():
    engine=create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return Session(engine)


def _seed(db: Session, code="BL56"):
    p=Project(code=code,name="Build Launch",acl_groups=["engineering-ai-users"])
    a=ProjectArea(project_code=code,code="assembly",name="Assembly",acl_groups=["engineering-ai-users"])
    root=Part(part_number=f"ROOT-{code}",name="Vehicle",project_code=code,latest_revision="A",metadata_json={"manufacturing_area":"assembly"})
    part=Part(part_number=f"PART-{code}",name="Bracket",project_code=code,latest_revision="D",metadata_json={"manufacturing_area":"assembly"})
    doc=Document(filename="build.pdf",stored_path="/tmp/build.pdf",sha256="a"*64,status=DocumentStatus.ready,part_number=part.part_number,revision="D",doc_type="drawing",project_code=code,manufacturing_area="assembly",acl_groups=["engineering-ai-users"])
    db.add_all([p,a,root,part,doc]);db.commit();db.refresh(doc)
    v=VehicleVariant(project_code=code,manufacturing_area="assembly",code="PREM",name="Premium",status="released",evidence_document_ids=[doc.id])
    db.add(v);db.commit();db.refresh(v)
    for pn in (root.part_number,part.part_number):
        db.add(ConfigurationApplicability(project_code=code,variant_id=v.id,manufacturing_area="assembly",entity_type="part",entity_key=pn,applicability="included",source="manual",evidence_document_ids=[doc.id]))
    db.commit()
    return p,root,part,doc,v


def _workspace(db,p,root,part,doc,vin=None):
    return vehicle_build_launch_workspace(db,p.code,{doc.id},{root.part_number,part.part_number},"assembly",{"assembly"},vin)


def test_vin_build_genealogy_and_100_percent_coverage():
    db=_db();p,root,part,doc,v=_seed(db)
    b=VehicleBuild(project_code=p.code,manufacturing_area="assembly",code="PB-001",vehicle_identifier="VIN001",variant_id=v.id,plant="Kaluga",build_type="pilot",status="completed",completed_at=datetime.now(timezone.utc),evidence_document_ids=[doc.id])
    db.add(b);db.commit();db.refresh(b)
    db.add_all([
        BuildGenealogyItem(build_id=b.id,manufacturing_area="assembly",part_number=root.part_number,revision="A",source_system="mes",evidence_document_ids=[doc.id]),
        BuildGenealogyItem(build_id=b.id,manufacturing_area="assembly",part_number=part.part_number,revision="D",supplier_code="SUP1",lot_number="LOT1",source_system="mes",evidence_document_ids=[doc.id]),
    ]);db.commit()
    out=_workspace(db,p,root,part,doc,"VIN001")
    assert out["selected_build"]["genealogy_coverage_pct"] == 100.0
    assert out["selected_build"]["genealogy_status"] == "GREEN"
    assert out["selected_build"]["genealogy"][1]["supplier_code"] == "SUP1"


def test_missing_expected_genealogy_is_red_and_explicit():
    db=_db();p,root,part,doc,v=_seed(db,"MISS56")
    b=VehicleBuild(project_code=p.code,manufacturing_area="assembly",code="PB-001",vehicle_identifier="VIN001",variant_id=v.id,status="completed",evidence_document_ids=[doc.id])
    db.add(b);db.commit();db.refresh(b)
    db.add(BuildGenealogyItem(build_id=b.id,manufacturing_area="assembly",part_number=root.part_number,revision="A",source_system="mes",evidence_document_ids=[doc.id]));db.commit()
    out=_workspace(db,p,root,part,doc)
    assert out["selected_build"]["genealogy_status"] == "RED"
    assert part.part_number in out["selected_build"]["missing_expected_parts"]


def test_defect_recurrence_clusters_by_part_supplier_variant():
    db=_db();p,root,part,doc,v=_seed(db,"REC56")
    builds=[]
    for i in range(2):
        b=VehicleBuild(project_code=p.code,manufacturing_area="assembly",code=f"PB-{i}",vehicle_identifier=f"VIN{i}",variant_id=v.id,status="completed",completed_at=datetime.now(timezone.utc)+timedelta(minutes=i),evidence_document_ids=[doc.id]);db.add(b);db.commit();db.refresh(b);builds.append(b)
        db.add(BuildGenealogyItem(build_id=b.id,manufacturing_area="assembly",part_number=part.part_number,revision="D",supplier_code="SUP1",source_system="mes",evidence_document_ids=[doc.id]))
        d=ProcessDefect(project_code=p.code,manufacturing_area="assembly",part_number=part.part_number,defect_code="CRACK",title="Bracket crack",severity="high",status="open",evidence_document_ids=[doc.id]);db.add(d);db.commit();db.refresh(d)
        db.add(BuildDefectLink(build_id=b.id,defect_id=d.id,detection_stage="eol",evidence_document_ids=[doc.id]));db.commit()
    out=_workspace(db,p,root,part,doc)
    assert len(out["recurrence"]) == 1
    r=out["recurrence"][0]
    assert r["affected_builds"] == 2 and r["supplier_code"] == "SUP1" and r["recurrence"] is True


def test_safe_launch_exit_is_deterministic_but_requires_human_approval():
    db=_db();p,root,part,doc,v=_seed(db,"SAFE56")
    db.add(SafeLaunchControl(project_code=p.code,manufacturing_area="assembly",code="SL1",part_number=part.part_number,characteristic="weld crack",status="active",inspected_quantity=120,defect_quantity=0,consecutive_clean_builds=4,required_clean_builds=3,required_inspected_quantity=100,evidence_document_ids=[doc.id]));db.commit()
    out=_workspace(db,p,root,part,doc)
    c=out["safe_launch"]["controls"][0]
    assert c["exit_candidate"] is True
    assert c["human_exit_approval_required"] is True
    assert out["safe_launch"]["status"] == "AMBER"


def test_safe_launch_defect_blocks_exit_candidate():
    db=_db();p,root,part,doc,v=_seed(db,"SAFEB56")
    db.add(SafeLaunchControl(project_code=p.code,manufacturing_area="assembly",code="SL1",part_number=part.part_number,characteristic="gap",status="active",inspected_quantity=200,defect_quantity=1,consecutive_clean_builds=5,required_clean_builds=3,required_inspected_quantity=100,evidence_document_ids=[doc.id]));db.commit()
    c=_workspace(db,p,root,part,doc)["safe_launch"]["controls"][0]
    assert c["exit_candidate"] is False
    assert "safe_launch_defects_detected" in c["exit_gaps"]


def test_build_rows_with_mixed_hidden_evidence_fail_closed():
    db=_db();p,root,part,doc,v=_seed(db,"ACL56")
    hidden=Document(filename="hidden.pdf",stored_path="/tmp/hidden",sha256="b"*64,status=DocumentStatus.ready,part_number=part.part_number,revision="D",doc_type="spec",project_code=p.code,manufacturing_area="assembly",acl_groups=["secret"])
    db.add(hidden);db.commit();db.refresh(hidden)
    db.add(VehicleBuild(project_code=p.code,manufacturing_area="assembly",code="PB1",vehicle_identifier="VIN1",variant_id=v.id,status="completed",evidence_document_ids=[doc.id,hidden.id]));db.commit()
    rows=visible_build_rows(db,p.code,{doc.id},{root.part_number,part.part_number},"assembly",{"assembly"})
    assert rows["builds"] == []


def test_build_defect_to_8d_change_to_next_build_feedback_loop_is_explainable_not_causal():
    db=_db();p,root,part,doc,v=_seed(db,"LOOP56")
    t=datetime.now(timezone.utc)
    b1=VehicleBuild(project_code=p.code,manufacturing_area="assembly",code="PB1",vehicle_identifier="VIN1",variant_id=v.id,status="completed",completed_at=t,evidence_document_ids=[doc.id])
    b2=VehicleBuild(project_code=p.code,manufacturing_area="assembly",code="PB2",vehicle_identifier="VIN2",variant_id=v.id,status="completed",completed_at=t+timedelta(days=1),evidence_document_ids=[doc.id])
    ch=ChangeRequest(code="ECR-LOOP56",eco_code="ECO-LOOP56",title="Fix bracket",part_number=part.part_number,status="implemented",affected_document_ids=[doc.id])
    db.add_all([b1,b2,ch]);db.commit();db.refresh(b1);db.refresh(b2);db.refresh(ch)
    eight=Problem8D(project_code=p.code,manufacturing_area="assembly",part_number=part.part_number,title="Crack 8D",severity="high",status="closed",linked_change_id=ch.id,evidence_document_ids=[doc.id]);db.add(eight);db.commit();db.refresh(eight)
    d=ProcessDefect(project_code=p.code,manufacturing_area="assembly",part_number=part.part_number,defect_code="CRACK",title="Bracket crack",severity="high",status="closed",linked_8d_id=eight.id,evidence_document_ids=[doc.id]);db.add(d);db.commit();db.refresh(d)
    db.add(BuildDefectLink(build_id=b1.id,defect_id=d.id,detection_stage="eol",containment_status="closed",evidence_document_ids=[doc.id]));db.commit()
    out=_workspace(db,p,root,part,doc)
    loop=out["engineering_feedback_loop"][0]
    assert loop["change_code"] == "ECO-LOOP56"
    assert loop["later_builds_observed"] == 1
    assert loop["same_issue_on_later_builds"] == 0
    assert loop["causal_claim"] is False
