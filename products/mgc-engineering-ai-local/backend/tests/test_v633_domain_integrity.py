from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy import create_engine, inspect, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

from app.core.runtime_contract import APP_VERSION, SCHEMA_VERSION
from app.core.security import Identity
from app.db import models  # noqa: F401
from app.db.migrations import ensure_v633_schema
from app.db.models import AuditEvent, BOMItem, Document, ManufacturingLine, ProcessStation, Project, WorkInstruction
from app.db.session import Base
from app.db.unit_of_work import EditConflict, UnitOfWork, require_expected_version
from app.schemas.api import WorkInstructionUpdateRequest
from app.api.contexts.manufacturing_quality import update_work_instruction
from app.services.audit import add_audit_event
from app.services import engineering_change as ec


def _factory(tmp_path: Path | None = None):
    url = "sqlite:///:memory:" if tmp_path is None else f"sqlite:///{tmp_path / 'v633.db'}"
    eng = create_engine(url)
    Base.metadata.create_all(eng)
    return eng, sessionmaker(bind=eng, expire_on_commit=False)


def _seed_wi(db):
    db.add(Project(code="P1", name="Car", acl_groups=["engineering-ai-admins"]))
    line = ManufacturingLine(project_code="P1", manufacturing_area="assembly", code="L1", name="Line")
    db.add(line); db.flush()
    station = ProcessStation(line_id=line.id, code="ST10", name="Station", headcount=1)
    db.add(station); db.flush()
    wi = WorkInstruction(
        project_code="P1", manufacturing_area="assembly", station_id=station.id,
        code="WI-1", title="Install", revision="A", source_language="ru",
        original_text="Install part", steps_json=[{"sequence": 10, "text": "Install part"}],
    )
    db.add(wi); db.commit(); db.refresh(wi)
    return wi, station


def test_v633_schema_marker_and_version_columns_are_idempotent():
    eng, _ = _factory()
    ensure_v633_schema(eng); ensure_v633_schema(eng)
    with eng.begin() as conn:
        assert conn.execute(text("SELECT schema_version FROM mgc_schema_state WHERE id=1")).scalar_one() == "6.3.3"
    cols = {c["name"] for c in inspect(eng).get_columns("work_instructions")}
    assert "row_version" in cols
    assert APP_VERSION == "6.3.34"
    assert SCHEMA_VERSION == "6.3.13"


def test_expected_version_rejects_stale_work_instruction_edit():
    _, Factory = _factory()
    with Factory() as db:
        wi, _ = _seed_wi(db)
        current = wi.row_version
        out = update_work_instruction(
            "P1", wi.id, WorkInstructionUpdateRequest(expected_version=current, title="First edit"),
            Identity("admin", ["engineering-ai-admins"]), db,
        )
        assert out["row_version"] == current + 1
        with pytest.raises(EditConflict) as exc:
            update_work_instruction(
                "P1", wi.id, WorkInstructionUpdateRequest(expected_version=current, title="Stale edit"),
                Identity("admin", ["engineering-ai-admins"]), db,
            )
        assert exc.value.expected_version == current
        assert exc.value.current_version == current + 1


def test_sqlalchemy_version_column_prevents_true_parallel_lost_update(tmp_path):
    _, Factory = _factory(tmp_path)
    with Factory() as db:
        wi, _ = _seed_wi(db); wi_id = wi.id
    a, b = Factory(), Factory()
    try:
        wa, wb = a.get(WorkInstruction, wi_id), b.get(WorkInstruction, wi_id)
        wa.title = "Engineer A"; UnitOfWork(a).commit()
        wb.title = "Engineer B"
        with pytest.raises(EditConflict):
            UnitOfWork(b).commit()
        with Factory() as check:
            assert check.get(WorkInstruction, wi_id).title == "Engineer A"
    finally:
        a.close(); b.close()


def test_unit_of_work_rolls_back_domain_and_audit_together():
    _, Factory = _factory()
    with Factory() as db:
        wi, _ = _seed_wi(db); wi_id = wi.id
        original = wi.title
        with pytest.raises(RuntimeError):
            with UnitOfWork(db):
                wi.title = "Must roll back"
                add_audit_event(db, "engineer", "TEST_ATOMIC", "work_instruction", wi.id, {})
                raise RuntimeError("simulate audit/write failure")
        db.expire_all()
        assert db.get(WorkInstruction, wi_id).title == original
        assert db.scalar(select(AuditEvent).where(AuditEvent.action == "TEST_ATOMIC")) is None


def test_change_creation_and_hash_event_are_one_transaction(monkeypatch):
    _, Factory = _factory()
    with Factory() as db:
        db.add(Project(code="P1", name="Car"))
        # visible revision evidence required by create_change
        for rev, did in [("A", "D1"), ("B", "D2")]:
            db.add(models.PartRevision(part_number="PN1", revision=rev))
            db.add(Document(id=did, filename=f"{rev}.pdf", stored_path=f"/{rev}.pdf", sha256=rev.lower()*64,
                            part_number="PN1", revision=rev, project_code="P1"))
        db.commit()
        original = ec.add_change_event
        def fail_event(*args, **kwargs):
            raise RuntimeError("event store unavailable")
        monkeypatch.setattr(ec, "add_change_event", fail_event)
        with pytest.raises(RuntimeError):
            ec.create_change(db, title="Change", description=None, reason="Needed", part_number="PN1",
                             from_revision="A", to_revision="B", priority="normal", user="u", allowed_document_ids={"D1","D2"})
        assert db.scalar(select(models.ChangeRequest)) is None
        monkeypatch.setattr(ec, "add_change_event", original)


def test_fresh_schema_enforces_basic_manufacturing_and_bom_constraints():
    _, Factory = _factory()
    with Factory() as db:
        db.add(Project(code="P1", name="Car"))
        line = ManufacturingLine(project_code="P1", manufacturing_area="assembly", code="L1", name="Line")
        db.add(line); db.commit()
        db.add(ProcessStation(line_id=line.id, code="BAD", name="Bad", headcount=0))
        with pytest.raises(IntegrityError): db.commit()
        db.rollback()
        # FK source doc is created to isolate the quantity invariant.
        doc = Document(filename="b.csv", stored_path="/b.csv", sha256="a"*64)
        db.add(doc); db.flush()
        db.add(BOMItem(parent_part_number="P", child_part_number="C", quantity=0, source_document_id=doc.id))
        with pytest.raises(IntegrityError): db.commit()
