import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import Identity, _require_engineer, get_identity, is_engineering_admin
from app.db.models import Document, DocumentActivity, DocumentStatus, PartRevision
from app.db.session import Base
from app.services.audit import document_activity_history, log_document_activity
from app.services.design_review import run_design_review


def _db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return Session(engine)


def test_engineer_only_gate_denies_non_engineering_group(monkeypatch):
    cfg = get_settings()
    monkeypatch.setattr(cfg, "engineer_only_access", True)
    monkeypatch.setattr(cfg, "engineer_access_groups", "engineering-ai-users,engineering-ai-admins")
    monkeypatch.setattr(cfg, "engineering_admin_groups", "engineering-ai-admins")
    with pytest.raises(HTTPException) as exc:
        _require_engineer(Identity("finance.user", ["finance"]))
    assert exc.value.status_code == 403
    allowed = _require_engineer(Identity("engineer.user", ["engineering-ai-users"]))
    assert allowed.user == "engineer.user"


def test_admin_is_separate_from_normal_engineer(monkeypatch):
    cfg = get_settings()
    monkeypatch.setattr(cfg, "engineering_admin_groups", "engineering-ai-admins")
    assert is_engineering_admin(Identity("e", ["engineering-ai-users"])) is False
    assert is_engineering_admin(Identity("a", ["engineering-ai-admins"])) is True



def test_shared_api_key_is_blocked_for_production_human_access(monkeypatch):
    cfg = get_settings()
    monkeypatch.setattr(cfg, "app_env", "prod")
    monkeypatch.setattr(cfg, "auth_mode", "api_key")
    monkeypatch.setattr(cfg, "engineer_only_access", True)
    monkeypatch.setattr(cfg, "allow_api_key_auth_in_prod", False)
    monkeypatch.setattr(cfg, "api_key", "a-real-test-key")
    with pytest.raises(HTTPException) as exc:
        get_identity(x_api_key="a-real-test-key")
    assert exc.value.status_code == 503


def test_document_activity_chain_detects_tampering():
    db = _db_session()
    doc = Document(filename="drawing.pdf", stored_path="/tmp/drawing.pdf", sha256="a" * 64, status=DocumentStatus.ready, doc_type="drawing", acl_groups=["all"])
    db.add(doc); db.commit(); db.refresh(doc)
    first = log_document_activity(db, doc.id, "eng.one", "DOCUMENT_OPEN", "Открыт документ")
    second = log_document_activity(db, doc.id, "eng.two", "ENGINEER_NOTE", "Проверен размер Ø10", {"category": "work_done"})
    rows, valid = document_activity_history(db, doc.id)
    assert valid is True
    assert [x.id for x in rows] == [second.id, first.id]
    assert second.previous_hash == first.event_hash

    stored = db.get(DocumentActivity, first.id)
    stored.summary = "Подменённая запись"
    db.commit()
    _, valid_after = document_activity_history(db, doc.id)
    assert valid_after is False


def test_document_activity_anchor_detects_newest_event_deletion():
    db = _db_session()
    doc = Document(filename="drawing.pdf", stored_path="/tmp/drawing.pdf", sha256="e" * 64, status=DocumentStatus.ready, doc_type="drawing", acl_groups=["all"])
    db.add(doc); db.commit(); db.refresh(doc)
    log_document_activity(db, doc.id, "eng.one", "DOCUMENT_OPEN", "Открыт документ")
    newest = log_document_activity(db, doc.id, "eng.two", "ENGINEER_NOTE", "Проверено отверстие Ø8")
    db.delete(db.get(DocumentActivity, newest.id)); db.commit()
    _, valid = document_activity_history(db, doc.id)
    assert valid is False


def test_design_review_builds_simple_report_and_checklist():
    db = _db_session()
    pn = "8450012345"
    db.add(PartRevision(part_number=pn, revision="D", metadata_json={}, document_ids=[]))
    cad = Document(filename="part.step", stored_path="/tmp/part.step", sha256="b" * 64, status=DocumentStatus.ready, part_number=pn, revision="D", doc_type="cad", acl_groups=["all"], extracted_metadata={"material": "SUS409L"})
    drawing = Document(filename="drawing.pdf", stored_path="/tmp/drawing.pdf", sha256="c" * 64, status=DocumentStatus.ready, part_number=pn, revision="D", doc_type="drawing", acl_groups=["all"], extracted_metadata={"material": "SUS409L", "geometry_links": {"status": "ready", "coverage": 1.0, "linked_multiple": 0, "unmatched": 0}})
    bom = Document(filename="bom.csv", stored_path="/tmp/bom.csv", sha256="d" * 64, status=DocumentStatus.ready, part_number=pn, revision="D", doc_type="bom", acl_groups=["all"])
    db.add_all([cad, drawing, bom]); db.commit()
    review = run_design_review(db, pn, "D", None, "eng.one", {cad.id, drawing.id, bom.id})
    assert review.report_json["title"].startswith("Design Review")
    checklist = {x["item"]: x["status"] for x in review.report_json["checklist"]}
    assert checklist["3D-модель"] == "ok"
    assert checklist["Чертёж"] == "ok"
    assert checklist["BOM"] == "ok"
    assert review.report_json["recommended_actions"]



def test_compute_job_result_visibility_rule():
    from app.services.compute_manager import can_view_job
    assert can_view_job("eng.owner", "eng.owner", False) is True
    assert can_view_job("eng.owner", "eng.other", False) is False
    assert can_view_job("eng.owner", "eng.admin", True) is True
