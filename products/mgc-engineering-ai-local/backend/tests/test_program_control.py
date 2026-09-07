from datetime import datetime, timedelta, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db.models import (
    Document, DocumentStatus, EngineeringRisk, LaunchReadinessItem, Part, PPAPSubmission,
    ProgramDependency, Project, ProjectArea, ProjectMilestone, RequirementVerification,
    EngineeringRequirement,
)
from app.db.session import Base
from app.services.program_control import (
    critical_dependency_chain, program_control_workspace, simulate_milestone_slip,
    visible_program_rows,
)


def _db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return Session(engine)


def _seed(db: Session, code="PC54"):
    now = datetime.now(timezone.utc)
    project = Project(code=code, name="Program Control", phase="launch", target_release_at=now + timedelta(days=60), acl_groups=["engineering-ai-users"])
    area = ProjectArea(project_code=code, code="body_welding", name="Сварка", acl_groups=["engineering-ai-users"], sort_order=10)
    part = Part(part_number=f"PART-{code}", name="Bracket", project_code=code, latest_revision="D", metadata_json={"manufacturing_area":"body_welding"})
    doc = Document(filename="evidence.pdf", stored_path="/tmp/evidence.pdf", sha256="a"*64, status=DocumentStatus.ready, part_number=part.part_number, revision="D", doc_type="test_report", project_code=code, manufacturing_area="body_welding", acl_groups=["engineering-ai-users"])
    db.add_all([project, area, part, doc]); db.commit(); db.refresh(doc)
    m1 = ProjectMilestone(project_code=code, code="DF-PREP", name="Design Freeze preparation", due_at=now + timedelta(days=10), status="planned", owner="eng-a", gate="engineering", manufacturing_area="body_welding")
    m2 = ProjectMilestone(project_code=code, code="DESIGN-FREEZE", name="Design Freeze", due_at=now + timedelta(days=20), status="planned", owner="eng-b", gate="design_freeze", manufacturing_area="body_welding")
    m3 = ProjectMilestone(project_code=code, code="SOP", name="Start of Production", due_at=now + timedelta(days=50), status="planned", owner="launch", gate="sop", manufacturing_area="body_welding")
    db.add_all([m1,m2,m3]); db.commit()
    d1 = ProgramDependency(project_code=code, manufacturing_area="body_welding", predecessor_milestone_id=m1.id, successor_milestone_id=m2.id, lag_days=5, criticality="high")
    d2 = ProgramDependency(project_code=code, manufacturing_area="body_welding", predecessor_milestone_id=m2.id, successor_milestone_id=m3.id, lag_days=20, criticality="critical")
    db.add_all([d1,d2]); db.commit()
    return project, area, part, doc, (m1,m2,m3), (d1,d2)


def test_program_control_builds_gate_maturity_chain_and_actions():
    db=_db(); project, _, part, doc, milestones, _ = _seed(db)
    db.add(LaunchReadinessItem(project_code=project.code, manufacturing_area="body_welding", part_number=part.part_number, code="LR-PPAP", category="ppap", title="PPAP ready", required=True, status="planned", due_at=datetime.now(timezone.utc)+timedelta(days=25), evidence_document_ids=[doc.id]))
    db.add(EngineeringRisk(project_code=project.code, manufacturing_area="body_welding", code="R-54", title="Supplier capacity", part_number=part.part_number, probability=4, severity=5, detectability=3, residual_probability=4, residual_severity=5, residual_detectability=3, status="open", evidence_document_ids=[doc.id]))
    db.commit()
    out=program_control_workspace(db,project,{doc.id},{part.part_number},"body_welding",{"body_welding"})
    assert out["target_gate"]["code"] == "DESIGN-FREEZE"
    assert out["critical_dependency_chain"]["formal_cpm"] is False
    assert out["critical_dependency_chain"]["path"]
    assert out["maturity"]["overall"] <= 100
    assert out["gate_forecast"]["band"] in {"GREEN","AMBER","RED"}
    assert any(x["source_type"]=="engineering_risk" for x in out["top_actions"])
    assert out["governance"]["no_automatic_gate_approval"] is True


def test_slip_simulation_propagates_without_writing_schedule():
    db=_db(); project, _, part, doc, milestones, deps = _seed(db,"SLIP54")
    before=[m.due_at for m in milestones]
    out=simulate_milestone_slip(list(milestones),list(deps),milestones[0].id,15)
    assert out["no_schedule_write"] is True
    assert out["affected_count"] >= 2
    assert any(x["code"]=="DESIGN-FREEZE" and x["slip_days"]>=10 for x in out["affected"])
    assert [m.due_at for m in milestones] == before


def test_hidden_evidence_rows_do_not_enter_program_forecast():
    db=_db(); project, _, part, doc, _, _ = _seed(db,"ACL54")
    hidden=Document(filename="secret.pdf",stored_path="/tmp/secret.pdf",sha256="b"*64,status=DocumentStatus.ready,part_number=part.part_number,revision="D",doc_type="test_report",project_code=project.code,manufacturing_area="body_welding",acl_groups=["secret"])
    db.add(hidden);db.commit();db.refresh(hidden)
    visible=EngineeringRisk(project_code=project.code,manufacturing_area="body_welding",code="R-V",title="Visible",part_number=part.part_number,probability=3,severity=4,detectability=3,evidence_document_ids=[doc.id])
    mixed=EngineeringRisk(project_code=project.code,manufacturing_area="body_welding",code="R-H",title="Mixed hidden",part_number=part.part_number,probability=5,severity=5,detectability=5,evidence_document_ids=[doc.id,hidden.id])
    db.add_all([visible,mixed]);db.commit()
    rows=visible_program_rows(db,project.code,{doc.id},{part.part_number},"body_welding",{"body_welding"})
    assert {x.code for x in rows["risks"]} == {"R-V"}


def test_requirement_and_ppap_maturity_are_evidence_based():
    db=_db(); project, _, part, doc, _, _ = _seed(db,"MAT54")
    req=EngineeringRequirement(project_code=project.code,manufacturing_area="body_welding",code="REQ-1",title="Strength",requirement_text="Must pass",part_numbers=[part.part_number],source_document_id=doc.id)
    db.add(req);db.commit();db.refresh(req)
    db.add(RequirementVerification(project_code=project.code,requirement_id=req.id,manufacturing_area="body_welding",code="VV-1",title="DV",status="passed",evidence_document_ids=[doc.id]))
    db.add(PPAPSubmission(project_code=project.code,manufacturing_area="body_welding",part_number=part.part_number,supplier_code="SUP-A",supplier_name="Supplier A",status="approved",evidence_document_ids=[doc.id]))
    db.commit()
    out=program_control_workspace(db,project,{doc.id},{part.part_number},"body_welding",{"body_welding"})
    assert out["maturity"]["domains"]["vv"] == 100.0
    assert out["maturity"]["domains"]["supplier"] == 100.0


def test_dependency_chain_reports_due_date_slack_method():
    db=_db(); _, _, _, _, milestones, deps = _seed(db,"CHAIN54")
    out=critical_dependency_chain(list(milestones),list(deps),milestones[-1].id)
    assert out["method"] == "deterministic_due_date_dependency_slack"
    assert out["formal_cpm"] is False
    assert len(out["path"]) == 2


def test_overdue_target_gate_is_red_and_explained():
    db=_db(); project, _, part, doc, milestones, deps = _seed(db,"RED54")
    now=datetime.now(timezone.utc)
    milestones[1].due_at=now-timedelta(days=3)
    milestones[2].due_at=now-timedelta(days=1)
    db.commit()
    out=program_control_workspace(db,project,{doc.id},{part.part_number},"body_welding",{"body_welding"})
    assert out["gate_forecast"]["band"] == "RED"
    assert any(x["type"]=="overdue_milestone" for x in out["blocker_forecast"])


def test_legacy_dependency_cycle_is_surfaced_as_red_not_hidden():
    db=_db(); project, _, part, doc, milestones, deps = _seed(db,"CYCLE54")
    db.add(ProgramDependency(project_code=project.code,manufacturing_area="body_welding",predecessor_milestone_id=milestones[2].id,successor_milestone_id=milestones[0].id,lag_days=0,criticality="critical"))
    db.commit()
    out=program_control_workspace(db,project,{doc.id},{part.part_number},"body_welding",{"body_welding"})
    assert out["schedule"]["dependency_cycles"]
    assert out["gate_forecast"]["band"] == "RED"
