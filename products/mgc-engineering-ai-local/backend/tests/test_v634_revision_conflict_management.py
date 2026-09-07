from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy import create_engine, inspect, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

from app.core.runtime_contract import APP_VERSION, SCHEMA_VERSION
from app.core.security import Identity
from app.db import models  # noqa: F401
from app.db.migrations import ensure_v634_schema
from app.db.models import (
    ChangeApproval, ChangeRequest, EditConflictEvent, EngineeringRevisionSnapshot,
    ManufacturingLayout, ManufacturingLine, ProcessStation, Project,
    StationLayoutPlacement, WorkInstruction, WriteIdempotencyRecord,
)
from app.db.session import Base
from app.db.unit_of_work import EditConflict, require_expected_version
from app.services.revision_control import (
    clone_layout, clone_work_instruction, idempotency_lookup, integrity_dashboard,
    layout_diff, store_idempotency, visual_diff, work_instruction_diff,
)


def _factory(tmp_path: Path | None = None):
    url = "sqlite:///:memory:" if tmp_path is None else f"sqlite:///{tmp_path / 'v634.db'}"
    eng = create_engine(url)
    Base.metadata.create_all(eng)
    return eng, sessionmaker(bind=eng, expire_on_commit=False)


def _seed(db):
    db.add(Project(code="P1", name="Car", acl_groups=["engineering-ai-admins"]))
    line = ManufacturingLine(project_code="P1", manufacturing_area="assembly", code="L1", name="Line")
    db.add(line); db.flush()
    station = ProcessStation(line_id=line.id, code="ST10", name="Station", headcount=1)
    db.add(station); db.flush()
    wi = WorkInstruction(
        project_code="P1", manufacturing_area="assembly", station_id=station.id,
        code="WI-1", title="Install", revision="A", status="approved", source_language="zh",
        translation_status="reviewed", translated_text_ru="Установить", approved_by="admin",
        original_text="安装零件", steps_json=[{"sequence": 10, "text": "安装零件"}],
        translated_steps_json=[{"sequence": 10, "text": "Установить деталь"}],
        metadata_json={"translation_source_fingerprint": "old"}, created_by="u",
    )
    layout = ManufacturingLayout(project_code="P1", manufacturing_area="assembly", code="LAY1", title="Layout", revision="A")
    db.add_all([wi, layout]); db.flush()
    db.add(StationLayoutPlacement(layout_id=layout.id, station_id=station.id, x_pct=12, y_pct=18, width_pct=15, height_pct=12))
    db.commit()
    return wi, layout, station


def test_v634_schema_marker_and_new_reliability_tables_are_idempotent():
    eng, _ = _factory()
    ensure_v634_schema(eng); ensure_v634_schema(eng)
    with eng.begin() as conn:
        assert conn.execute(text("SELECT schema_version FROM mgc_schema_state WHERE id=1")).scalar_one() == "6.3.4"
    tables = set(inspect(eng).get_table_names())
    assert {"engineering_revision_snapshots", "write_idempotency_records", "edit_conflict_events"}.issubset(tables)
    assert APP_VERSION == "6.3.34"
    assert SCHEMA_VERSION == "6.3.13"


def test_conflict_contains_current_record_for_visual_review():
    _, Factory = _factory()
    with Factory() as db:
        wi, _, _ = _seed(db)
        with pytest.raises(EditConflict) as exc:
            require_expected_version(wi, wi.row_version + 5, "work_instruction")
        assert exc.value.current_record["title"] == "Install"
        assert exc.value.current_record["revision"] == "A"
        assert exc.value.current_record["row_version"] == wi.row_version


def test_work_instruction_revision_is_draft_and_does_not_inherit_foreign_translation_approval():
    _, Factory = _factory()
    with Factory() as db:
        wi, _, _ = _seed(db)
        new = clone_work_instruction(db, wi, new_revision="B", user="engineer", reason="Process update")
        db.commit(); db.refresh(new)
        assert new.code == wi.code and new.revision == "B"
        assert new.status == "draft"
        assert new.approved_by is None
        assert new.translation_status == "stale"
        assert new.translated_text_ru is None
        assert new.metadata_json["revision_lineage"]["source_instruction_id"] == wi.id
        assert db.scalar(select(EngineeringRevisionSnapshot).where(EngineeringRevisionSnapshot.entity_id == wi.id)) is not None
        diff = work_instruction_diff(wi, new)
        assert diff["changed"] is True
        assert diff["auto_merge"] is False


def test_layout_revision_copies_station_placements_and_diff_is_human_review_only():
    _, Factory = _factory()
    with Factory() as db:
        _, layout, station = _seed(db)
        new, placements = clone_layout(db, layout, new_revision="B", user="engineer", reason="Station rebalance")
        db.commit()
        assert new.status == "draft" and new.revision == "B"
        assert len(placements) == 1 and placements[0].station_id == station.id
        placements[0].x_pct = 35; db.commit()
        diff = layout_diff(db, layout, new)
        assert diff["changed"] is True
        assert diff["human_review_required"] is True
        assert any(x["field"].startswith("placements") for x in diff["changes"])


def test_write_idempotency_replays_same_payload_and_rejects_key_reuse_for_different_payload():
    _, Factory = _factory()
    with Factory() as db:
        payload = {"expected_version": 1, "new_revision": "B", "reason": "test"}
        assert idempotency_lookup(db, user="u", route_key="r", key="abc", request_payload=payload) is None
        store_idempotency(db, user="u", route_key="r", key="abc", request_payload=payload, response={"id": "X"}, entity_type="work_instruction", entity_id="X")
        db.commit()
        assert idempotency_lookup(db, user="u", route_key="r", key="abc", request_payload=payload) == {"id": "X"}
        with pytest.raises(ValueError):
            idempotency_lookup(db, user="u", route_key="r", key="abc", request_payload={**payload, "new_revision": "C"})


def test_database_blocks_duplicate_change_approval_stage():
    _, Factory = _factory()
    with Factory() as db:
        change = ChangeRequest(code="ECR-X", title="x", reason="r")
        db.add(change); db.flush()
        db.add(ChangeApproval(change_id=change.id, stage="technical_review", approver="a", decision="approved")); db.commit()
        db.add(ChangeApproval(change_id=change.id, stage="technical_review", approver="b", decision="approved"))
        with pytest.raises(IntegrityError): db.commit()


def test_integrity_dashboard_surfaces_conflicts_and_never_enables_auto_merge():
    _, Factory = _factory()
    with Factory() as db:
        db.add(EditConflictEvent(entity_type="work_instruction", entity_id="W1", expected_version=2, current_version=3, current_record_json={"id": "W1"}))
        db.add(WriteIdempotencyRecord(user="u", route_key="r", idempotency_key="k", request_sha256="a"*64, response_json={}))
        db.commit()
        out = integrity_dashboard(db)
        assert out["edit_conflicts_total"] == 1
        assert out["idempotent_write_receipts"] == 1
        assert out["auto_merge_enabled"] is False
        assert out["human_conflict_resolution_required"] is True
