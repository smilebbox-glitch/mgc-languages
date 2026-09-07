from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db.models import APQPDeliverable, ControlPlanItem, Document, DocumentStatus, PFMEAItem, PPAPSubmission, Problem8D, Project, SpecialCharacteristic
from app.db.session import Base
from app.services.project_workspace import project_workspace
from app.services.quality_core_tools import internal_pfmea_risk_band, quality_workspace


def _db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return Session(engine)


def _project_with_part(db: Session, code="CARQ", part="P1", area="assembly"):
    project = Project(code=code, name="Quality program", acl_groups=["engineering-ai-users"])
    doc = Document(filename="p1.pdf", stored_path="/tmp/p1", sha256="a"*64, status=DocumentStatus.ready,
                   part_number=part, revision="A", doc_type="drawing", project_code=code,
                   manufacturing_area=area, acl_groups=["engineering-ai-users"])
    db.add_all([project, doc]); db.commit()
    return project, doc


def test_special_characteristic_requires_pfmea_and_active_control_plan_for_full_coverage():
    db = _db(); project, doc = _project_with_part(db)
    ch = SpecialCharacteristic(project_code=project.code, manufacturing_area="assembly", part_number="P1", code="SC-01",
                               category="safety", description="Torque", source_document_id=doc.id)
    db.add(ch); db.commit(); db.refresh(ch)
    first = quality_workspace(db, project.code, {doc.id}, {"P1"}, "assembly")
    assert first["gates"]["core_tools"] == 0.0
    assert sum(x["severity"] == "critical" for x in first["gaps"]) >= 2

    pfmea = PFMEAItem(project_code=project.code, manufacturing_area="assembly", part_number="P1", process_step="Tighten bolt",
                      failure_mode="Under torque", severity=9, occurrence=2, detection=3, status="controlled",
                      special_characteristic_ids=[ch.id])
    cp = ControlPlanItem(project_code=project.code, manufacturing_area="assembly", part_number="P1", process_step="Tighten bolt",
                         characteristic_id=ch.id, characteristic="Torque", measurement_method="DC tool trace",
                         reaction_plan="Stop station, contain parts, notify quality", status="active", control_phase="production")
    db.add_all([pfmea, cp]); db.commit()
    second = quality_workspace(db, project.code, {doc.id}, {"P1"}, "assembly")
    assert second["gates"]["core_tools"] == 100.0
    assert not [g for g in second["gaps"] if g["type"].startswith("characteristic_")]


def test_pfmea_internal_risk_band_is_explicitly_separate_from_action_priority():
    item = PFMEAItem(project_code="P", process_step="Weld", failure_mode="Missing weld", severity=10, occurrence=2, detection=2, action_priority="M")
    assert internal_pfmea_risk_band(item) == "critical"
    # User/customer configured AP is preserved and not overwritten by the internal advisory band.
    assert item.action_priority == "M"


def test_quality_workspace_respects_manufacturing_area_and_visible_part_scope():
    db = _db(); project, doc = _project_with_part(db, code="CAR2", part="VISIBLE", area="body_welding")
    hidden_doc = Document(filename="hidden.pdf", stored_path="/tmp/h", sha256="b"*64, status=DocumentStatus.ready,
                          part_number="HIDDEN", revision="A", doc_type="drawing", project_code="CAR2", manufacturing_area="paint",
                          acl_groups=["engineering-secret"])
    db.add(hidden_doc); db.commit()
    db.add_all([
        SpecialCharacteristic(project_code="CAR2", manufacturing_area="body_welding", part_number="VISIBLE", code="W1", description="Weld nugget"),
        SpecialCharacteristic(project_code="CAR2", manufacturing_area="paint", part_number="HIDDEN", code="P1", description="Coating"),
        Problem8D(project_code="CAR2", manufacturing_area="paint", part_number="HIDDEN", title="Secret paint defect", severity="critical"),
    ]); db.commit()
    out = quality_workspace(db, "CAR2", {doc.id}, {"VISIBLE"}, "body_welding")
    assert {x["code"] for x in out["special_characteristics"]} == {"W1"}
    assert not out["problems_8d"]
    assert all(g.get("part_number") != "HIDDEN" for g in out["gaps"])


def test_ppap_and_8d_are_reflected_in_quality_gates():
    db = _db(); project, doc = _project_with_part(db, code="CAR3")
    db.add(PPAPSubmission(project_code="CAR3", manufacturing_area="assembly", part_number="P1", status="rejected"))
    db.add(Problem8D(project_code="CAR3", manufacturing_area="assembly", part_number="P1", title="Customer complaint", severity="critical", status="root_cause"))
    db.commit()
    out = quality_workspace(db, "CAR3", {doc.id}, {"P1"}, "assembly")
    assert out["gates"]["ppap"] == 0.0
    assert out["gates"]["problem_solving"] < 100.0
    assert any(x["type"] == "ppap" and x["severity"] == "critical" for x in out["gaps"])
    assert any(x["type"] == "8d" and x["severity"] == "critical" for x in out["gaps"])


def test_project_readiness_includes_quality_core_tools_blockers():
    db = _db(); project, doc = _project_with_part(db, code="CAR4")
    db.add(SpecialCharacteristic(project_code="CAR4", manufacturing_area="assembly", part_number="P1", code="SAFE-1", category="safety", description="Safety characteristic"))
    db.commit()
    out = project_workspace(db, project, {doc.id}, manufacturing_area="assembly", identity_groups=["engineering-ai-users"])
    assert "quality_core_tools" in out["readiness"]
    assert any(b["type"] == "quality" and b["severity"] == "critical" for b in out["readiness"]["blockers"])
    assert out["readiness"]["status"] == "blocked"


def test_apqp_completion_contributes_to_quality_score():
    db = _db(); project, doc = _project_with_part(db, code="CAR5")
    db.add_all([
        APQPDeliverable(project_code="CAR5", code="A1", title="Process flow approved", status="done"),
        APQPDeliverable(project_code="CAR5", code="A2", title="Run at rate", status="planned"),
    ]); db.commit()
    out = quality_workspace(db, "CAR5", {doc.id}, {"P1"}, "assembly")
    assert out["gates"]["apqp"] == 50.0
