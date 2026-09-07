from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db.models import (
    ChangeRequest, Document, DocumentStatus, EngineeringLesson, Part, Problem8D, ProcessDefect, Project
)
from app.db.session import Base
from app.services.engineering_knowledge_memory import (
    collect_project_cases, create_lesson_from_case, knowledge_memory_workspace, recurrence_signals, validate_lesson
)


def _db():
    engine=create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return Session(engine)


def _seed(db: Session, code="MEM1"):
    project=Project(code=code,name="Knowledge Memory",acl_groups=["engineering-ai-users"])
    part=Part(part_number=f"BRKT-{code}",name="Welded bracket",project_code=code,latest_revision="D",metadata_json={"manufacturing_area":"body_welding"})
    doc=Document(filename="evidence.pdf",stored_path="/tmp/evidence.pdf",sha256="a"*64,status=DocumentStatus.ready,part_number=part.part_number,revision="D",doc_type="test_report",project_code=code,manufacturing_area="body_welding",acl_groups=["engineering-ai-users"])
    db.add_all([project,part,doc]);db.commit();db.refresh(doc)
    change=ChangeRequest(code=f"ECR-{code}",eco_code=f"ECO-{code}",title="Increase bracket thickness after weld crack",description="Fatigue crack near weld",reason="weld fatigue crack",part_number=part.part_number,from_revision="C",to_revision="D",status="implemented",risk_level="high",implementation_plan={"action":"increase thickness and adjust weld parameter"},verification_plan={"test":"fatigue"},metadata_json={"verification_result":"fatigue retest passed; no crack"},affected_document_ids=[doc.id])
    problem=Problem8D(project_code=code,manufacturing_area="body_welding",part_number=part.part_number,title="Weld fatigue crack",severity="high",status="closed",disciplines_json={"d2":"crack near spot weld","d5":"increase thickness and tune weld","d6":"500k cycle test passed","d7":"update PFMEA"},evidence_document_ids=[doc.id])
    db.add_all([change,problem]);db.commit()
    return project,part,doc,change,problem


def test_memory_finds_explainable_historical_analogues():
    db=_db(); project,part,doc,_,_=_seed(db)
    cases=collect_project_cases(db,project.code,{doc.id},{part.part_number},"body_welding",{"body_welding"})
    out=knowledge_memory_workspace(cases,"fatigue crack weld thickness",part.part_number,"body_welding",limit=10)
    assert out["metrics"]["historical_cases"] >= 2
    assert out["matches"][0]["similarity"] > 0.45
    assert any("та же деталь" in r for r in out["matches"][0]["why_similar"])
    assert out["deterministic_similarity"] is True and out["human_validation_required"] is True


def test_hidden_evidence_case_fails_closed():
    db=_db(); project,part,doc,_,_=_seed(db,"MEM2")
    hidden=Document(filename="secret.pdf",stored_path="/tmp/secret.pdf",sha256="b"*64,status=DocumentStatus.ready,part_number=part.part_number,revision="D",doc_type="test_report",project_code=project.code,manufacturing_area="body_welding",acl_groups=["secret"])
    db.add(hidden);db.commit();db.refresh(hidden)
    db.add(ProcessDefect(project_code=project.code,manufacturing_area="body_welding",part_number=part.part_number,defect_code="SECRET",title="Secret porosity root cause",status="resolved",evidence_document_ids=[doc.id,hidden.id],metadata_json={"corrective_action":"secret parameter","verification_result":"passed"}))
    db.commit()
    cases=collect_project_cases(db,project.code,{doc.id},{part.part_number},"body_welding",{"body_welding"})
    assert all("Secret porosity" not in c["title"] for c in cases)


def test_lesson_requires_explicit_human_validation_and_outcome():
    db=_db(); project,part,doc,_,_=_seed(db,"MEM3")
    cases=collect_project_cases(db,project.code,{doc.id},{part.part_number},"body_welding",{"body_welding"})
    source=next(c for c in cases if c["source_type"]=="change")
    lesson=create_lesson_from_case(db,source,created_by="engineer")
    assert lesson.status=="draft"
    lesson.outcome=""
    db.commit()
    try:
        validate_lesson(db,lesson,validator="admin",status="validated",effectiveness="verified")
        assert False,"missing outcome must block validation"
    except ValueError as exc:
        assert "outcome" in str(exc)
    lesson.outcome="fatigue retest passed"
    db.commit()
    validate_lesson(db,lesson,validator="admin",status="validated",effectiveness="verified")
    assert lesson.status=="validated" and lesson.validated_by=="admin"


def test_recurrence_signal_links_open_problem_to_prior_verified_case():
    db=_db(); project,part,doc,_,_=_seed(db,"MEM4")
    db.add(ProcessDefect(project_code=project.code,manufacturing_area="body_welding",part_number=part.part_number,defect_code="WCRACK",title="Fatigue crack near weld again",status="open",severity="high",evidence_document_ids=[doc.id]))
    db.commit()
    cases=collect_project_cases(db,project.code,{doc.id},{part.part_number},"body_welding",{"body_welding"})
    signals=recurrence_signals(cases)
    assert signals
    assert signals[0]["current_case"]["status"]=="open"
    assert signals[0]["historical_case"]["status"] in {"implemented","closed","resolved"}
    assert signals[0]["similarity"] >= 0.34




def test_portfolio_context_excludes_inaccessible_projects():
    from app.services.engineering_knowledge_memory import accessible_memory_contexts
    db=_db()
    visible=Project(code="PORT-V",name="Visible",acl_groups=["engineering-ai-users"])
    hidden=Project(code="PORT-H",name="Hidden",acl_groups=["secret-group"])
    d1=Document(filename="v.pdf",stored_path="/tmp/v",sha256="c"*64,status=DocumentStatus.ready,part_number="PV-1",revision="A",doc_type="drawing",project_code="PORT-V",acl_groups=["engineering-ai-users"])
    d2=Document(filename="h.pdf",stored_path="/tmp/h",sha256="d"*64,status=DocumentStatus.ready,part_number="PH-1",revision="A",doc_type="drawing",project_code="PORT-H",acl_groups=["secret-group"])
    db.add_all([visible,hidden,d1,d2]);db.commit()
    ctx=accessible_memory_contexts(db,visible,["engineering-ai-users"],[d1],None,"portfolio")
    codes={x[0].code for x in ctx}
    assert codes=={"PORT-V"}
