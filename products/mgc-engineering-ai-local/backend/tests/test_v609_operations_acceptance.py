from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.db.models import Base, OperationsGameDayExercise, OperationsGameDayRun
from app.db.migrations import ensure_v609_schema
from app.services.operations_acceptance import (
    DEFAULT_EXERCISES,
    REQUIRED_EXTERNAL_GATES,
    create_game_day,
    evaluate_game_day,
    finalize_game_day,
    record_external_gates,
    start_game_day,
    update_exercise,
)


def db_session():
    eng = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(eng)
    ensure_v609_schema(eng)
    return eng, sessionmaker(bind=eng)()


def _verify_all(db, run, *, base=None):
    base = base or datetime(2026, 9, 5, tzinfo=timezone.utc)
    rows = db.query(OperationsGameDayExercise).filter_by(run_id=run.id).all()
    for i, row in enumerate(rows):
        t = base + timedelta(minutes=i * 10)
        update_exercise(db, row, actor="ops", payload={
            "status": "verified", "started_at": t, "fault_injected_at": t,
            "detected_at": t + timedelta(seconds=10), "recovered_at": t + timedelta(seconds=min(row.target_rto_seconds or 100, 100)),
            "verified_at": t + timedelta(seconds=min(row.target_rto_seconds or 100, 100) + 20),
            "actual_rpo_seconds": 0, "evidence": {"ticket": f"E-{i}", "runbook": "verified"},
        })


def test_v609_schema_marker_and_tables():
    eng, db = db_session()
    assert db.execute(text("SELECT schema_version FROM mgc_schema_state WHERE id=1")).scalar_one() == "6.0.9"
    names = {r[0] for r in db.execute(text("SELECT name FROM sqlite_master WHERE type='table'"))}
    assert {"operations_game_day_runs", "operations_game_day_exercises"} <= names


def test_rehearsal_can_never_return_go():
    _, db = db_session(); run = create_game_day(db, code="GD-R", name="Rehearsal", mode="rehearsal", actor="ops")
    _verify_all(db, run)
    out = evaluate_game_day(db, run)
    assert out["decision"] == "PRECHECK_PASS"
    assert out["deployment_authorized"] is False


def test_controlled_requires_external_runtime_gates():
    _, db = db_session(); run = create_game_day(db, code="GD-C", name="Controlled", mode="controlled", actor="ops")
    _verify_all(db, run)
    out = evaluate_game_day(db, run)
    assert out["decision"] == "NO_GO"
    assert any(x.get("gate") == "cve_scan" for x in out["blockers"])


def test_controlled_go_only_when_all_required_evidence_passes():
    _, db = db_session(); run = create_game_day(db, code="GD-G", name="Go", mode="controlled", actor="ops")
    _verify_all(db, run)
    record_external_gates(db, run, evidence={g: {"status": "PASS", "evidence_ref": f"EV-{g}"} for g in REQUIRED_EXTERNAL_GATES})
    out = evaluate_game_day(db, run)
    assert out["decision"] == "GO"
    assert out["required_exercise_coverage"] == 1.0
    assert out["deployment_authorized"] is False


def test_rpo_miss_is_no_go():
    _, db = db_session(); run = create_game_day(db, code="GD-RPO", name="RPO", mode="controlled", actor="ops")
    _verify_all(db, run)
    record_external_gates(db, run, evidence={g: True for g in REQUIRED_EXTERNAL_GATES})
    row = db.query(OperationsGameDayExercise).filter_by(run_id=run.id, exercise_code="backup_restore").one()
    row.actual_rpo_seconds = (row.target_rpo_seconds or 0) + 1; db.commit()
    out = evaluate_game_day(db, run)
    assert out["decision"] == "NO_GO"
    assert any(x["code"] == "RPO_TARGET_MISSED" for x in out["blockers"])


def test_verified_exercise_requires_timing_and_evidence():
    _, db = db_session(); run = create_game_day(db, code="GD-V", name="Verify", mode="controlled", actor="ops")
    row = db.query(OperationsGameDayExercise).filter_by(run_id=run.id).first()
    with pytest.raises(ValueError):
        update_exercise(db, row, actor="ops", payload={"status": "verified"})


def test_finalization_requires_explicit_confirmation_and_never_authorizes_deployment():
    _, db = db_session(); run = create_game_day(db, code="GD-F", name="Final", mode="rehearsal", actor="ops")
    _verify_all(db, run)
    with pytest.raises(ValueError):
        finalize_game_day(db, run, actor="admin", confirm="YES")
    out = finalize_game_day(db, run, actor="admin", confirm="FINALIZE_OPERATIONS_ACCEPTANCE")
    assert out["finalized"] is True
    assert out["deployment_authorized"] is False


def test_application_policy_explicitly_forbids_fault_injection():
    _, db = db_session(); run = create_game_day(db, code="GD-P", name="Policy", mode="controlled", actor="ops")
    assert run.gate_policy_json["application_never_injects_faults"] is True
    assert len(run.required_exercises) == len(DEFAULT_EXERCISES)

def test_open_critical_incident_blocks_controlled_go():
    from app.services.production_support import create_incident
    _, db = db_session(); run = create_game_day(db, code="GD-I", name="Incident", mode="controlled", actor="ops")
    _verify_all(db, run)
    record_external_gates(db, run, evidence={g: True for g in REQUIRED_EXTERNAL_GATES})
    create_incident(db, code="INC-CRIT", severity="critical", component="database", summary="Database unstable", actor="ops")
    out = evaluate_game_day(db, run)
    assert out["decision"] == "NO_GO"
    assert any(x["code"] == "OPEN_CRITICAL_INCIDENT" for x in out["blockers"])


def test_open_high_incident_yields_conditional_go():
    from app.services.production_support import create_incident
    _, db = db_session(); run = create_game_day(db, code="GD-H", name="High incident", mode="controlled", actor="ops")
    _verify_all(db, run)
    record_external_gates(db, run, evidence={g: True for g in REQUIRED_EXTERNAL_GATES})
    create_incident(db, code="INC-HIGH", severity="high", component="qdrant", summary="Degraded recovery", actor="ops")
    out = evaluate_game_day(db, run)
    assert out["decision"] == "CONDITIONAL_GO"
    assert any(x["code"] == "OPEN_HIGH_INCIDENT" for x in out["conditions"])
