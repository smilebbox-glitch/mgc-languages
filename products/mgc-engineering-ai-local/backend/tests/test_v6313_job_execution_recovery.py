from __future__ import annotations

from datetime import datetime, timedelta, timezone
from types import ModuleType, SimpleNamespace

import pytest
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker

from app.core.config import get_settings
from app.core.runtime_contract import APP_VERSION, SCHEMA_VERSION
from app.db import models  # noqa: F401
from app.db.migrations import ensure_v6313_schema
from app.db.models import ComputeJobRecoveryEvent
from app.db.session import Base
from app.services.background_jobs import (
    ActiveJobLease,
    JobRecoveryNotAllowed,
    StaleJobDelivery,
    acquire_execution_slot,
    create_job,
    dispatch_job,
    list_recovery_events,
    mark_success,
    prepare_orphan_recovery,
    recover_expired_leases,
    set_progress,
    workload_snapshot,
)


def _factory():
    eng = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(eng)
    ensure_v6313_schema(eng)
    return eng, sessionmaker(bind=eng, expire_on_commit=False)


def _expire(job, db):
    job.lease_expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
    db.commit()


def test_v6313_schema_marker_columns_and_recovery_ledger_are_idempotent():
    eng, _ = _factory()
    ensure_v6313_schema(eng)
    with eng.begin() as conn:
        assert conn.execute(text("SELECT schema_version FROM mgc_schema_state WHERE id=1")).scalar_one() == "6.3.13"
    cols = {x["name"] for x in inspect(eng).get_columns("compute_jobs")}
    assert {"dispatch_token", "dispatch_generation", "lease_expires_at", "recovery_count", "last_recovery_at", "recovery_reason"}.issubset(cols)
    assert "compute_job_recovery_events" in inspect(eng).get_table_names()
    assert APP_VERSION == "6.3.34" and SCHEMA_VERSION == "6.3.13"


def test_delivery_fence_rejects_stale_progress_and_result_writes():
    _, Factory = _factory()
    with Factory() as db:
        job = create_job(db, user="u", kind="document_ingest", project_code="P1")
        job.dispatch_token = "current-token"; job.dispatch_generation = 1; db.commit()
        with pytest.raises(StaleJobDelivery):
            acquire_execution_slot(db, job, worker_id="w-old", dispatch_token="old-token")
        acquire_execution_slot(db, job, worker_id="w-current", dispatch_token="current-token")
        with pytest.raises(StaleJobDelivery):
            set_progress(db, job, 50, "late write", dispatch_token="old-token")
        with pytest.raises(StaleJobDelivery):
            mark_success(db, job, {"bad": True}, dispatch_token="old-token")
        assert job.status == "running"


def test_duplicate_delivery_cannot_enter_while_active_lease_is_owned():
    _, Factory = _factory()
    with Factory() as db:
        job = create_job(db, user="u", kind="document_ingest", project_code="P1")
        job.dispatch_token = "same-delivery"; job.dispatch_generation = 1; db.commit()
        acquire_execution_slot(db, job, worker_id="w1", dispatch_token="same-delivery")
        with pytest.raises(ActiveJobLease):
            acquire_execution_slot(db, job, worker_id="w2", dispatch_token="same-delivery")
        assert job.worker_id == "w1" and job.attempt_count == 1


def test_expired_replay_safe_ingest_is_fenced_and_auto_requeued_without_broker():
    _, Factory = _factory()
    with Factory() as db:
        job = create_job(db, user="u", kind="document_ingest", project_code="P1")
        job.dispatch_token = "old-token"; job.dispatch_generation = 1; db.commit()
        acquire_execution_slot(db, job, worker_id="lost", dispatch_token="old-token")
        _expire(job, db)
        out = recover_expired_leases(db, actor="test", dispatch=False)
        assert out["expired"] == 1 and out["auto_requeued"] == 1
        assert job.status == "queued" and job.recovery_count == 1
        assert job.dispatch_token != "old-token" and job.worker_id is None
        events = list_recovery_events(db, job_id=job.id)
        assert events[0]["action"] == "auto_requeue" and events[0]["actor"] == "test"
        with pytest.raises(StaleJobDelivery):
            set_progress(db, job, 80, "late old worker", dispatch_token="old-token")


def test_expired_decision_job_becomes_orphaned_and_requires_exact_admin_confirmation():
    _, Factory = _factory()
    with Factory() as db:
        job = create_job(db, user="u", kind="design_review", project_code="P1")
        job.dispatch_token = "decision-token"; job.dispatch_generation = 1; db.commit()
        acquire_execution_slot(db, job, worker_id="lost", dispatch_token="decision-token")
        _expire(job, db)
        out = recover_expired_leases(db, actor="scheduler", dispatch=False)
        assert out["manual_orphaned"] == 1 and job.status == "orphaned"
        assert job.dispatch_token != "decision-token"
        with pytest.raises(JobRecoveryNotAllowed):
            prepare_orphan_recovery(db, job, actor="admin", confirm="yes")
        prepare_orphan_recovery(db, job, actor="admin", confirm="RECOVER_ORPHANED")
        assert job.status == "queued"
        actions = [x["action"] for x in list_recovery_events(db, job_id=job.id)]
        assert "manual_review" in actions and "manual_requeue_prepared" in actions


def test_expired_job_with_exhausted_attempt_budget_enters_dlq():
    _, Factory = _factory()
    with Factory() as db:
        job = create_job(db, user="u", kind="document_ingest")
        job.max_attempts = 1; job.dispatch_token = "t"; job.dispatch_generation = 1; db.commit()
        acquire_execution_slot(db, job, worker_id="lost", dispatch_token="t")
        _expire(job, db)
        out = recover_expired_leases(db, dispatch=False)
        assert out["dead_lettered"] == 1
        assert job.status == "dead_letter" and job.dead_lettered_at is not None


def test_dispatch_rotates_fence_and_increments_generation_before_publish(monkeypatch):
    _, Factory = _factory()
    calls = []
    import sys
    fake = ModuleType("app.workers.tasks")
    fake.ingest_document_task = SimpleNamespace(apply_async=lambda **kw: calls.append(kw) or SimpleNamespace(id="celery-1"))
    fake.run_design_review_task = SimpleNamespace(apply_async=lambda **kw: SimpleNamespace(id="celery-2"))
    monkeypatch.setitem(sys.modules, "app.workers.tasks", fake)
    with Factory() as db:
        job = create_job(db, user="u", kind="document_ingest", request_json={"document_id": "doc-1"})
        first = job.dispatch_token
        task = dispatch_job(job)
        assert task.id == "celery-1" and job.dispatch_generation == 1
        assert job.dispatch_token and job.dispatch_token != first
        assert calls[0]["args"] == ["doc-1", job.id, job.dispatch_token]


def test_workload_snapshot_exposes_recovery_policy_and_metrics():
    _, Factory = _factory()
    with Factory() as db:
        job = create_job(db, user="u", kind="design_review")
        job.status = "orphaned"; job.recovery_count = 1; db.add(ComputeJobRecoveryEvent(job_id=job.id, recovery_number=1, action="manual_review", reason="lease", actor="test")); db.commit()
        out = workload_snapshot(db)
        assert out["orphaned_jobs"] == 1 and out["recovery_events"] == 1
        assert out["recovery"]["safe_replay_kinds"] == ["document_ingest"]
        assert out["recovery"]["lease_grace_seconds"] >= 0
