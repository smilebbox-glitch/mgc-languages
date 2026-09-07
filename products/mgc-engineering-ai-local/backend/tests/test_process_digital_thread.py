from datetime import datetime, timedelta, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db.models import (
    ControlPlanItem, Document, DocumentStatus, ManufacturingLine, PFMEAItem, ProcessAsset, ProcessDefect,
    ProcessOperation, ProcessParameter, ProcessStation, Project, SpecialCharacteristic,
)
from app.db.session import Base
from app.services.process_digital_thread import process_digital_thread
from app.services.project_workspace import project_workspace


def _db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return Session(engine)


def _base(db: Session, code="CARP", area="assembly", part="P1"):
    project = Project(code=code, name="Process program", acl_groups=["engineering-ai-users"])
    doc = Document(filename="wi.pdf", stored_path="/tmp/wi", sha256="a" * 64, status=DocumentStatus.ready,
                   part_number=part, revision="A", doc_type="drawing", project_code=code,
                   manufacturing_area=area, acl_groups=["engineering-ai-users"])
    db.add_all([project, doc]); db.commit(); db.refresh(doc)
    line = ManufacturingLine(project_code=code, manufacturing_area=area, code="L1", name="Main line")
    db.add(line); db.commit(); db.refresh(line)
    station = ProcessStation(line_id=line.id, code="S10", name="Station 10", sequence=10)
    db.add(station); db.commit(); db.refresh(station)
    op = ProcessOperation(station_id=station.id, code="OP10", name="Torque fastening", part_number=part,
                          work_instruction_document_ids=[doc.id], cycle_time_sec=45)
    db.add(op); db.commit(); db.refresh(op)
    return project, doc, line, station, op


def test_process_thread_builds_line_station_operation_and_core_tool_links():
    db = _db(); project, doc, line, station, op = _base(db)
    sc = SpecialCharacteristic(project_code=project.code, manufacturing_area="assembly", part_number="P1", code="SC-TQ", description="Torque")
    db.add(sc); db.commit(); db.refresh(sc)
    pf = PFMEAItem(project_code=project.code, manufacturing_area="assembly", part_number="P1", process_step=op.name,
                   process_operation_id=op.id, failure_mode="Under torque", status="controlled", special_characteristic_ids=[sc.id])
    cp = ControlPlanItem(project_code=project.code, manufacturing_area="assembly", part_number="P1", process_step=op.name,
                         process_operation_id=op.id, characteristic_id=sc.id, characteristic="Torque", reaction_plan="Stop and contain", status="active")
    db.add_all([pf, cp]); db.commit(); db.refresh(cp)
    db.add(ProcessParameter(operation_id=op.id, code="TQ", name="Torque", target_value=45, lower_spec_limit=42, upper_spec_limit=48,
                            unit="Nm", special_characteristic_id=sc.id, control_plan_item_id=cp.id, reaction_plan="Stop and contain"))
    db.commit()
    out = process_digital_thread(db, project.code, {doc.id}, {"P1"}, "assembly")
    assert out["configured"] is True
    assert out["counts"]["operations"] == 1
    assert out["tree"][0]["stations"][0]["operations"][0]["pfmea_count"] == 1
    assert out["tree"][0]["stations"][0]["operations"][0]["control_plan_count"] == 1
    assert out["score"] == 100.0
    assert not out["gaps"]


def test_process_thread_surfaces_missing_work_instruction_pfmea_and_control_plan():
    db = _db(); project, doc, line, station, op = _base(db, code="CARP2")
    op.work_instruction_document_ids = []
    db.commit()
    out = process_digital_thread(db, project.code, {doc.id}, {"P1"}, "assembly")
    types = {x["type"] for x in out["gaps"]}
    assert {"work_instruction", "operation_pfmea", "operation_control_plan"}.issubset(types)
    assert out["score"] < 100


def test_process_thread_flags_overdue_measurement_asset_and_critical_defect_without_8d():
    db = _db(); project, doc, line, station, op = _base(db, code="CARP3")
    past = datetime.now(timezone.utc) - timedelta(days=2)
    db.add(ProcessAsset(operation_id=op.id, code="GAUGE-1", name="Torque calibrator", asset_type="measurement", calibration_due_at=past))
    db.add(ProcessDefect(project_code=project.code, manufacturing_area="assembly", line_id=line.id, station_id=station.id, operation_id=op.id,
                         part_number="P1", title="Torque trace missing", severity="critical", quantity=2, status="open"))
    db.commit()
    out = process_digital_thread(db, project.code, {doc.id}, {"P1"}, "assembly")
    assert any(x["type"] == "asset_calibration" and x["severity"] == "critical" for x in out["gaps"])
    assert any(x["type"] == "process_defect" and x["severity"] == "critical" for x in out["gaps"])
    assert any(x["type"] == "defect_8d" for x in out["gaps"])


def test_process_thread_does_not_promote_hidden_part_process_data():
    db = _db(); project, doc, line, station, op = _base(db, code="CARP4", part="VISIBLE")
    hidden_op = ProcessOperation(station_id=station.id, code="SECRET", name="Secret operation", part_number="HIDDEN")
    db.add(hidden_op); db.commit()
    out = process_digital_thread(db, project.code, {doc.id}, {"VISIBLE"}, "assembly")
    codes = {o["code"] for l in out["tree"] for s in l["stations"] for o in s["operations"]}
    assert codes == {"OP10"}


def test_project_readiness_adds_process_gate_only_when_process_is_configured():
    db = _db(); project, doc, line, station, op = _base(db, code="CARP5")
    out = project_workspace(db, project, {doc.id}, manufacturing_area="assembly", identity_groups=["engineering-ai-users"])
    assert out["readiness"]["gates"]["process"] is not None
    assert out["process_thread"]["configured"] is True
    assert any(b["type"] == "process" for b in out["readiness"]["blockers"])
