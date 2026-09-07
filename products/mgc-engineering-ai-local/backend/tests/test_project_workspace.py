from datetime import datetime, timedelta, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db.models import BOMItem, ChangeRequest, Document, DocumentStatus, IssueSeverity, IssueStatus, Part, Project, ProjectMilestone, ValidationIssue
from app.db.session import Base
from app.services.project_workspace import project_allowed, project_workspace


def _db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return Session(engine)


def test_project_workspace_is_explainable_and_blocked_by_critical_issue():
    db = _db()
    project = Project(code="P1", name="Project One", root_part_number="ASSY-1", acl_groups=["engineering-a"], owner="lead")
    db.add(project)
    db.add_all([Part(part_number="ASSY-1", name="Assembly", project_code="P1"), Part(part_number="CHILD-1", name="Bracket", project_code="P1")])
    docs = [
        Document(filename="assy.step", stored_path="/tmp/a", sha256="a"*64, status=DocumentStatus.ready, part_number="ASSY-1", revision="A", doc_type="cad", project_code="P1", acl_groups=["engineering-a"]),
        Document(filename="assy.pdf", stored_path="/tmp/b", sha256="b"*64, status=DocumentStatus.ready, part_number="ASSY-1", revision="A", doc_type="drawing", project_code="P1", acl_groups=["engineering-a"]),
        Document(filename="child.step", stored_path="/tmp/c", sha256="c"*64, status=DocumentStatus.ready, part_number="CHILD-1", revision="A", doc_type="cad", project_code="P1", acl_groups=["engineering-a"]),
        Document(filename="child.pdf", stored_path="/tmp/d", sha256="d"*64, status=DocumentStatus.ready, part_number="CHILD-1", revision="A", doc_type="drawing", project_code="P1", acl_groups=["engineering-a"]),
    ]
    db.add_all(docs); db.commit()
    db.add(BOMItem(parent_part_number="ASSY-1", parent_revision="A", child_part_number="CHILD-1", child_revision="A", quantity=2, source_document_id=docs[1].id))
    db.add(ValidationIssue(part_number="CHILD-1", severity=IssueSeverity.critical, status=IssueStatus.open, rule_code="TEST", title="Critical geometry mismatch", details={}, document_ids=[docs[-1].id], fingerprint="f"*64))
    db.commit()
    out = project_workspace(db, project, {d.id for d in docs})
    assert out["readiness"]["status"] == "blocked"
    assert out["readiness"]["advisory_only"] is True
    assert out["readiness"]["human_release_approval_required"] is True
    assert out["readiness"]["gates"]["documentation"] == 100.0
    assert any(x["type"] == "issue" for x in out["readiness"]["blockers"])
    assert out["assembly_tree"]["part_number"] == "ASSY-1"
    assert out["assembly_tree"]["children"][0]["part_number"] == "CHILD-1"


def test_overdue_milestone_is_visible_but_not_automatic_release_authority():
    db = _db()
    project = Project(code="P2", name="Project Two", acl_groups=["engineering-a"])
    db.add(project)
    db.add(ProjectMilestone(project_code="P2", code="DR", name="Design Release", due_at=datetime.now(timezone.utc)-timedelta(days=2), status="in_progress"))
    db.commit()
    out = project_workspace(db, project, set())
    assert any(b["type"] == "milestone" for b in out["readiness"]["blockers"])
    assert out["readiness"]["status"] == "needs_review"
    assert out["readiness"]["human_release_approval_required"] is True


def test_project_acl_is_group_scoped():
    project = Project(code="P3", name="Secret Project", acl_groups=["engineering-special"])
    assert project_allowed(project, ["engineering-special"]) is True
    assert project_allowed(project, ["engineering-other"]) is False

def test_project_workspace_does_not_promote_hidden_document_facts():
    db = _db()
    project = Project(code="P4", name="Scoped", root_part_number="VISIBLE", acl_groups=["engineering-a"])
    db.add_all([project, Part(part_number="VISIBLE", project_code="P4"), Part(part_number="HIDDEN", project_code="P4")])
    visible = Document(filename="v.pdf", stored_path="/tmp/v", sha256="1"*64, status=DocumentStatus.ready, part_number="VISIBLE", revision="A", doc_type="drawing", project_code="P4", acl_groups=["engineering-a"])
    hidden = Document(filename="h.pdf", stored_path="/tmp/h", sha256="2"*64, status=DocumentStatus.ready, part_number="HIDDEN", revision="A", doc_type="drawing", project_code="P4", acl_groups=["engineering-secret"])
    db.add_all([visible, hidden]); db.commit()
    db.add(ValidationIssue(part_number="HIDDEN", severity=IssueSeverity.critical, status=IssueStatus.open, rule_code="SECRET", title="Hidden issue", details={}, document_ids=[hidden.id], fingerprint="3"*64)); db.commit()
    out = project_workspace(db, project, {visible.id})
    assert {p["part_number"] for p in out["parts"]} == {"VISIBLE"}
    assert all(i["rule_code"] != "SECRET" for i in out["issues"])


def test_project_workspace_action_center_is_bounded_evidence_backed_and_advisory():
    db = _db()
    project = Project(code="P5", name="Action Project", acl_groups=["engineering-a"])
    db.add(project)
    db.add(ProjectMilestone(project_code="P5", code="LATE", name="Late Gate", due_at=datetime.now(timezone.utc)-timedelta(days=1), status="in_progress"))
    db.commit()
    out = project_workspace(db, project, set(), identity_groups=["engineering-a"])
    center = out["action_center"]
    assert center["advisory_only"] is True
    assert center["human_decision_required"] is True
    assert center["source"] == "project_readiness_evidence"
    assert center["count"] == len(center["items"])
    assert center["count"] <= 12
    item = next(x for x in center["items"] if x["kind"] == "milestone")
    assert item["route"] == "projects"
    assert item["object_id"]
    assert item["human_decision_required"] is True


def test_project_workspace_action_center_orders_critical_before_warning():
    db = _db()
    project = Project(code="P6", name="Priority Project", acl_groups=["engineering-a"])
    db.add(project)
    doc = Document(filename="bad.pdf", stored_path="/tmp/bad", sha256="6"*64, status=DocumentStatus.failed, project_code="P6", acl_groups=["engineering-a"])
    db.add(doc)
    db.add(ProjectMilestone(project_code="P6", code="LATE", name="Late Gate", due_at=datetime.now(timezone.utc)-timedelta(days=1), status="in_progress"))
    db.commit()
    out = project_workspace(db, project, {doc.id}, identity_groups=["engineering-a"])
    items = out["action_center"]["items"]
    assert items[0]["severity"] == "critical"
    assert any(x["severity"] == "warning" for x in items)
