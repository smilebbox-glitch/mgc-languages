from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db.models import (
    Document, DocumentStatus, LaunchReadinessItem, LaunchTrial, PPAPSubmission, Project,
)
from app.db.session import Base
from app.services.launch_readiness import launch_readiness
from app.services.project_workspace import project_workspace


def _db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return Session(engine)


def _project(db: Session, code="LAUNCH1", area="assembly", part="P1"):
    project = Project(code=code, name="Launch project", acl_groups=["engineering-ai-users"])
    doc = Document(filename="p1.pdf", stored_path="/tmp/p1", sha256="a" * 64, status=DocumentStatus.ready,
                   part_number=part, revision="A", doc_type="drawing", project_code=code,
                   manufacturing_area=area, acl_groups=["engineering-ai-users"])
    db.add_all([project, doc]); db.commit(); db.refresh(doc)
    return project, doc


def test_launch_readiness_flags_run_at_rate_below_target_even_if_marked_passed():
    db = _db(); project, doc = _project(db)
    db.add(LaunchReadinessItem(project_code=project.code, manufacturing_area="assembly", code="TOOL-1", category="tooling",
                               title="Assembly fixture ready", status="ready", required=True))
    db.add(LaunchTrial(project_code=project.code, manufacturing_area="assembly", code="RAR-1", trial_type="run_at_rate",
                       title="Run at Rate", status="passed", target_rate_per_hour=60, actual_rate_per_hour=52,
                       produced_quantity=100, good_quantity=98, evidence_document_ids=[doc.id]))
    db.commit()
    out = launch_readiness(db, project.code, {doc.id}, {"P1"}, "assembly")
    assert out["configured"] is True
    assert out["gates"]["capacity"] == 86.7
    assert any(x["type"] == "capacity_mismatch" and x["severity"] == "critical" for x in out["gaps"])
    assert out["status"] == "blocked"


def test_supplier_ppap_is_reused_in_launch_gate_without_duplicate_input():
    db = _db(); project, doc = _project(db, code="LAUNCH2")
    db.add(LaunchReadinessItem(project_code=project.code, manufacturing_area="assembly", code="SUP-1", category="supplier",
                               title="Supplier readiness", status="ready", supplier_code="SUP01"))
    db.add(PPAPSubmission(project_code=project.code, manufacturing_area="assembly", part_number="P1", supplier_code="SUP01", status="approved"))
    db.commit()
    out = launch_readiness(db, project.code, {doc.id}, {"P1"}, "assembly")
    assert out["gates"]["supplier_ppap"] == 100.0
    assert not [x for x in out["gaps"] if x["type"] == "ppap"]


def test_launch_readiness_respects_area_scope():
    db = _db(); project, doc = _project(db, code="LAUNCH3", area="assembly")
    db.add_all([
        LaunchReadinessItem(project_code=project.code, manufacturing_area="assembly", code="ASM-1", category="tooling", title="Assembly fixture", status="ready"),
        LaunchReadinessItem(project_code=project.code, manufacturing_area="paint", code="PAINT-1", category="equipment", title="Paint oven", status="blocked"),
    ])
    db.commit()
    out = launch_readiness(db, project.code, {doc.id}, {"P1"}, "assembly", {"assembly"})
    assert {x["code"] for x in out["checks"]} == {"ASM-1"}
    assert not any("PAINT" in x["title"] for x in out["gaps"])


def test_project_workspace_adds_launch_gate_only_after_launch_is_configured():
    db = _db(); project, doc = _project(db, code="LAUNCH4")
    first = project_workspace(db, project, {doc.id}, manufacturing_area="assembly", identity_groups=["engineering-ai-users"])
    assert first["readiness"]["gates"]["launch"] is None
    db.add(LaunchReadinessItem(project_code=project.code, manufacturing_area="assembly", code="L-1", category="logistics",
                               title="Packaging approved", status="planned", required=True))
    db.commit()
    second = project_workspace(db, project, {doc.id}, manufacturing_area="assembly", identity_groups=["engineering-ai-users"])
    assert second["readiness"]["gates"]["launch"] is not None
    assert second["launch_readiness"]["configured"] is True
    assert any(b["type"] == "launch" for b in second["readiness"]["blockers"])


def test_good_quantity_cannot_exceed_produced_quantity_without_visible_gap():
    db = _db(); project, doc = _project(db, code="LAUNCH5")
    db.add(LaunchTrial(project_code=project.code, manufacturing_area="assembly", code="PB-1", trial_type="pilot_build",
                       title="Pilot build", status="passed", produced_quantity=10, good_quantity=12))
    db.commit()
    out = launch_readiness(db, project.code, {doc.id}, {"P1"}, "assembly")
    assert any(x["type"] == "trial_data" and x["severity"] == "critical" for x in out["gaps"])


def test_all_zones_launch_summary_still_respects_allowed_area_codes():
    db = _db(); project, doc = _project(db, code="LAUNCH6", area="assembly")
    db.add_all([
        LaunchReadinessItem(project_code=project.code, manufacturing_area="assembly", code="ASM-ALL", category="tooling", title="Assembly ready", status="ready"),
        LaunchReadinessItem(project_code=project.code, manufacturing_area="paint", code="PAINT-SECRET", category="equipment", title="Secret paint readiness", status="blocked"),
    ])
    db.commit()
    out = launch_readiness(db, project.code, {doc.id}, {"P1"}, None, {"assembly"})
    assert {x["code"] for x in out["checks"]} == {"ASM-ALL"}
    assert all("paint" not in (x["title"] or "").lower() for x in out["gaps"])
