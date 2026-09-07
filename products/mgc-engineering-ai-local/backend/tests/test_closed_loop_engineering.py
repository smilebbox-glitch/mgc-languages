from datetime import datetime, timedelta, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db.models import (
    ChangeEffectivenessReview, ChangeRequest, Document, DocumentStatus, EngineeringDecisionRecord,
    EngineeringDeviation, EngineeringRisk, IncomingQualityRecord, LocalizationItem, PPAPSubmission,
    Part, Problem8D, ProcessDefect, ProductionFeedback, Project,
)
from app.db.session import Base
from app.services.closed_loop_engineering import (
    closed_loop_workspace, defect_root_cause_explorer, risk_based_validation_plan,
    serialize_deviation, serialize_feedback, serialize_risk, supplier_quality_closed_loop,
)


def _db():
    engine=create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return Session(engine)


def _seed(db: Session, code="CL53"):
    p=Project(code=code,name="Closed Loop",acl_groups=["engineering-ai-users"])
    part=Part(part_number=f"BRKT-{code}",name="Bracket",project_code=code,latest_revision="D",metadata_json={"manufacturing_area":"body_welding"})
    doc=Document(filename="evidence.pdf",stored_path="/tmp/evidence.pdf",sha256="a"*64,status=DocumentStatus.ready,part_number=part.part_number,revision="D",doc_type="test_report",project_code=code,manufacturing_area="body_welding",acl_groups=["engineering-ai-users"])
    db.add_all([p,part,doc]);db.commit();db.refresh(doc)
    change=ChangeRequest(code=f"ECR-{code}",eco_code=f"ECO-{code}",title="Bracket improvement",reason="weld crack",part_number=part.part_number,from_revision="C",to_revision="D",status="implemented",risk_level="high",affected_document_ids=[doc.id],metadata_json={"verification_result":"DV passed"})
    db.add(change);db.commit();db.refresh(change)
    return p,part,doc,change


def test_closed_loop_workspace_connects_decision_feedback_effectiveness_and_risk():
    db=_db();p,part,doc,change=_seed(db)
    decision=EngineeringDecisionRecord(project_code=p.code,manufacturing_area="body_welding",code="DR-001",title="Reinforce bracket",part_number=part.part_number,change_id=change.id,problem_statement="Weld crack",alternatives_json=[{"option":"A"},{"option":"B"}],chosen_option="B",rationale="lower mass",expected_result="defects <0.2%",status="approved",evidence_document_ids=[doc.id],created_by="eng")
    db.add(decision);db.commit();db.refresh(decision)
    fb=ProductionFeedback(project_code=p.code,manufacturing_area="body_welding",code="PF-001",change_id=change.id,decision_id=decision.id,part_number=part.part_number,built_quantity=1200,defect_quantity=1,before_defect_rate_pct=0.94,planned_cost_delta=-70,actual_cost_delta=-64,planned_mass_delta_kg=0.12,actual_mass_delta_kg=0.11,planned_cycle_time_delta_sec=0,actual_cycle_time_delta_sec=1.4,currency="RUB",status="complete",evidence_document_ids=[doc.id])
    db.add(fb);db.commit();db.refresh(fb)
    eff=ChangeEffectivenessReview(project_code=p.code,manufacturing_area="body_welding",code="EFF-001",change_id=change.id,decision_id=decision.id,feedback_id=fb.id,target_description="defect rate <0.2%",baseline_value=0.94,target_value=0.2,observed_value=0.083,population=1200,unit="%",status="effective",conclusion="verified positive",evidence_document_ids=[doc.id],reviewed_by="admin")
    risk=EngineeringRisk(project_code=p.code,manufacturing_area="body_welding",code="R-001",title="Weld durability",part_number=part.part_number,change_id=change.id,probability=4,severity=5,detectability=3,residual_probability=1,residual_severity=5,residual_detectability=2,status="mitigating",evidence_document_ids=[doc.id])
    db.add_all([eff,risk]);db.commit()
    out=closed_loop_workspace(db,p.code,{doc.id},{part.part_number},"body_welding",{"body_welding"})
    assert out["engineering_pulse"]["release_confidence"] in {"GREEN","AMBER","RED"}
    assert out["production_feedback"][0]["defect_rate_pct"] < 0.2
    assert out["production_feedback"][0]["defect_rate_improvement_pct"] > 90
    assert out["planned_vs_actual"][0]["accuracy"] in {"high","medium","low"}
    assert out["effectiveness_reviews"][0]["status"] == "effective"
    assert out["risks"][0]["residual_score"] == 10
    assert out["governance"]["not_mes_or_scada"] is True


def test_validation_plan_is_deterministic_and_human_approved():
    out=risk_based_validation_plan({"material_from":"DC01","material_to":"DP600","supplier_from":"A","supplier_to":"B","geometry_changed":True,"from_revision":"C","to_revision":"D"})
    assert "supplier qualification" in out["required"]
    assert "drawing↔CAD consistency" in out["required"]
    assert "joining/weldability compatibility" in out["required"]
    assert out["human_vv_scope_approval_required"] is True


def test_root_cause_explorer_returns_candidates_not_causal_claim():
    db=_db();p,part,doc,change=_seed(db,"RC53")
    d=ProcessDefect(project_code=p.code,manufacturing_area="body_welding",part_number=part.part_number,defect_code="CRACK",title="Crack after change",severity="high",status="open",evidence_document_ids=[doc.id])
    db.add(d);db.commit();db.refresh(d)
    out=defect_root_cause_explorer(db,p.code,{doc.id},{part.part_number},"body_welding",{"body_welding"},d.id)
    assert out["causal_claim"] is False
    assert any(x["candidate_type"]=="recent_change" for x in out["investigation_candidates"])
    assert all(x["path"] for x in out["investigation_candidates"])


def test_root_cause_hidden_evidence_fails_closed():
    db=_db();p,part,doc,_=_seed(db,"RCS53")
    hidden=Document(filename="secret.pdf",stored_path="/tmp/secret",sha256="b"*64,status=DocumentStatus.ready,part_number=part.part_number,revision="D",doc_type="test_report",project_code=p.code,manufacturing_area="body_welding",acl_groups=["secret"])
    db.add(hidden);db.commit();db.refresh(hidden)
    d=ProcessDefect(project_code=p.code,manufacturing_area="body_welding",part_number=part.part_number,title="Secret defect",evidence_document_ids=[doc.id,hidden.id])
    db.add(d);db.commit();db.refresh(d)
    try:
        defect_root_cause_explorer(db,p.code,{doc.id},{part.part_number},"body_welding",{"body_welding"},d.id)
        assert False,"mixed visible/hidden evidence must fail closed"
    except LookupError:
        pass


def test_supplier_quality_closed_loop_aggregates_ppap_iq_and_8d():
    db=_db();p,part,doc,_=_seed(db,"SQ53")
    db.add(LocalizationItem(project_code=p.code,manufacturing_area="body_welding",part_number=part.part_number,supplier_code="SUP-A",supplier_name="Supplier A",status="sop",evidence_document_ids=[doc.id]))
    db.add(PPAPSubmission(project_code=p.code,manufacturing_area="body_welding",part_number=part.part_number,supplier_code="SUP-A",supplier_name="Supplier A",status="approved",evidence_document_ids=[doc.id]))
    prob=Problem8D(project_code=p.code,manufacturing_area="body_welding",part_number=part.part_number,title="Supplier porosity",status="open",metadata_json={"supplier_code":"SUP-A"},evidence_document_ids=[doc.id])
    db.add(prob);db.commit();db.refresh(prob)
    db.add(IncomingQualityRecord(project_code=p.code,manufacturing_area="body_welding",code="IQ-1",supplier_code="SUP-A",supplier_name="Supplier A",part_number=part.part_number,inspected_quantity=1000,defect_quantity=5,rejected_quantity=2,defect_code="POR",linked_8d_id=prob.id,evidence_document_ids=[doc.id]))
    db.commit()
    out=supplier_quality_closed_loop(db,p.code,{doc.id},{part.part_number},"body_welding",{"body_welding"})
    assert out[0]["supplier_code"]=="SUP-A"
    assert out[0]["incoming_defect_rate_pct"]==0.5
    assert out[0]["ppap"]["approved"]==1
    assert out[0]["open_8d"]==1


def test_deviation_expiry_and_residual_risk_are_explicit():
    db=_db();p,part,doc,_=_seed(db,"DR53")
    dev=EngineeringDeviation(project_code=p.code,manufacturing_area="body_welding",code="DEV-1",part_number=part.part_number,reason="supplier shortage",status="approved",valid_until=datetime.now(timezone.utc)-timedelta(days=1),evidence_document_ids=[doc.id])
    risk=EngineeringRisk(project_code=p.code,manufacturing_area="body_welding",code="R-1",title="Coating",part_number=part.part_number,probability=3,severity=5,detectability=3,residual_probability=2,residual_severity=5,residual_detectability=2,evidence_document_ids=[doc.id])
    db.add_all([dev,risk]);db.commit()
    assert serialize_deviation(dev)["status"]=="expired"
    assert serialize_risk(risk)["initial_score"]==45
    assert serialize_risk(risk)["residual_score"]==20
