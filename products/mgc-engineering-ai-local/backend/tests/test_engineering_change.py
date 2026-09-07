import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db.models import BOMItem, ChangeEvent, Document, DocumentStatus, PartRevision
from app.db.session import Base
from app.services.engineering_change import (
    change_history,
    complete_change,
    create_change,
    decide_change,
    run_change_impact,
    start_implementation,
    submit_for_approval,
)


def _db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return Session(engine)


def _seed(db: Session):
    pn = "8450012345"
    db.add_all([
        PartRevision(part_number=pn, revision="C", metadata_json={"material": "SUS409L"}, document_ids=[]),
        PartRevision(part_number=pn, revision="D", metadata_json={"material": "SUS409L", "thickness_mm": 1.5}, document_ids=[]),
    ])
    docs = [
        Document(filename="C.step", stored_path="/tmp/C.step", sha256="a"*64, status=DocumentStatus.ready, part_number=pn, revision="C", doc_type="cad", acl_groups=["all"], extracted_metadata={"volume_mm3": 100}),
        Document(filename="D.step", stored_path="/tmp/D.step", sha256="b"*64, status=DocumentStatus.ready, part_number=pn, revision="D", doc_type="cad", acl_groups=["all"], extracted_metadata={"volume_mm3": 110}),
        Document(filename="D.pdf", stored_path="/tmp/D.pdf", sha256="c"*64, status=DocumentStatus.ready, part_number=pn, revision="D", doc_type="drawing", acl_groups=["all"], extracted_metadata={"geometry_links": {"status": "ready", "coverage": 1.0}}),
    ]
    db.add_all(docs); db.commit()
    return pn, docs


def test_ecr_to_eco_workflow_requires_separation_of_duties():
    db = _db(); pn, docs = _seed(db); visible = {d.id for d in docs}
    change = create_change(db, title="Усилить кронштейн", description="Durability improvement", reason="Трещина на испытании", part_number=pn, from_revision="C", to_revision="D", priority="high", user="author", allowed_document_ids=visible)
    assert change.code.startswith("ECR-") and change.status == "draft"
    run_change_impact(db, change, "author", visible)
    assert change.status == "impact_review" and change.impact_json["risk_score"] >= 10
    submit_for_approval(db, change, "author")
    with pytest.raises(PermissionError):
        decide_change(db, change, stage="technical_review", decision="approved", comment="self", user="author", is_admin=False, allowed_document_ids=visible)
    decide_change(db, change, stage="technical_review", decision="approved", comment="geometry checked", user="reviewer", is_admin=False, allowed_document_ids=visible)
    with pytest.raises(PermissionError):
        decide_change(db, change, stage="final_approval", decision="approved", comment="release", user="reviewer", is_admin=False, allowed_document_ids=visible)
    with pytest.raises(PermissionError, match="different from the technical reviewer"):
        decide_change(db, change, stage="final_approval", decision="approved", comment="release", user="reviewer", is_admin=True, allowed_document_ids=visible)
    decide_change(db, change, stage="final_approval", decision="approved", comment="release", user="admin", is_admin=True, allowed_document_ids=visible)
    assert change.status == "approved" and change.eco_code.startswith("ECO-")
    start_implementation(db, change, implementation_plan={"step": "update tooling"}, verification_plan={"check": "drawing and BOM"}, user="implementer")
    complete_change(db, change, verification_result="Drawing, CAD and BOM verified", user="implementer")
    assert change.status == "implemented" and change.completed_at is not None


def test_change_history_is_tamper_evident():
    db = _db(); pn, docs = _seed(db); visible = {d.id for d in docs}
    change = create_change(db, title="Change", description=None, reason="test reason", part_number=pn, from_revision="C", to_revision="D", priority="normal", user="author", allowed_document_ids=visible)
    run_change_impact(db, change, "author", visible)
    rows, valid = change_history(db, change.id)
    assert valid is True and len(rows) >= 2
    oldest = rows[-1]
    stored = db.get(ChangeEvent, oldest.id); stored.summary = "tampered"; db.commit()
    _, valid_after = change_history(db, change.id)
    assert valid_after is False

def test_final_approval_rejects_stale_impact_evidence():
    db = _db(); pn, docs = _seed(db); visible = {d.id for d in docs}
    change = create_change(db, title="Bracket update", description=None, reason="supplier update", part_number=pn, from_revision="C", to_revision="D", priority="normal", user="author", allowed_document_ids=visible)
    run_change_impact(db, change, "author", visible)
    submit_for_approval(db, change, "author")
    decide_change(db, change, stage="technical_review", decision="approved", comment="ok", user="reviewer", is_admin=False, allowed_document_ids=visible)
    docs[-1].sha256 = "f" * 64; db.commit()
    with pytest.raises(ValueError, match="rerun impact analysis"):
        decide_change(db, change, stage="final_approval", decision="approved", comment="release", user="admin", is_admin=True, allowed_document_ids=visible)
    assert change.status == "impact_review"

def test_final_approval_detects_new_bom_impact_scope():
    db = _db(); pn, docs = _seed(db); visible = {d.id for d in docs}
    change = create_change(db, title="Bracket update", description=None, reason="durability", part_number=pn, from_revision="C", to_revision="D", priority="normal", user="author", allowed_document_ids=visible)
    run_change_impact(db, change, "author", visible); submit_for_approval(db, change, "author")
    decide_change(db, change, stage="technical_review", decision="approved", comment="ok", user="reviewer", is_admin=False, allowed_document_ids=visible)
    parent_doc = Document(filename="assy_bom.csv", stored_path="/tmp/assy_bom.csv", sha256="9"*64, status=DocumentStatus.ready, part_number="ASSY-100", revision="A", doc_type="bom", acl_groups=["all"])
    db.add(parent_doc); db.commit(); db.refresh(parent_doc)
    db.add(BOMItem(parent_part_number="ASSY-100", parent_revision="A", child_part_number=pn, child_revision="D", quantity=1, source_document_id=parent_doc.id)); db.commit()
    visible.add(parent_doc.id)
    with pytest.raises(ValueError, match="rerun impact analysis"):
        decide_change(db, change, stage="final_approval", decision="approved", comment="release", user="admin", is_admin=True, allowed_document_ids=visible)
    assert change.status == "impact_review"
