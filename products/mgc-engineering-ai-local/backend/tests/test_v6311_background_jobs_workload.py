from __future__ import annotations

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker

from app.core.config import Settings
from app.core.runtime_contract import APP_VERSION, SCHEMA_VERSION
from app.db import models  # noqa: F401
from app.db.migrations import ensure_v6311_schema
from app.db.models import ComputeJob
from app.db.session import Base
from app.services.background_jobs import (
    ProjectConcurrencyBusy, acquire_execution_slot, create_job, mark_failure,
    policy_for, request_cancellation, retry_dead_letter, workload_snapshot,
)


def _factory():
    eng = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(eng)
    return eng, sessionmaker(bind=eng, expire_on_commit=False)


def test_v6311_schema_marker_and_job_columns_are_idempotent():
    eng, _ = _factory()
    ensure_v6311_schema(eng); ensure_v6311_schema(eng)
    with eng.begin() as conn:
        assert conn.execute(text("SELECT schema_version FROM mgc_schema_state WHERE id=1")).scalar_one() == "6.3.11"
    cols = {x["name"] for x in inspect(eng).get_columns("compute_jobs")}
    assert {"project_code","resource_class","priority","progress_percent","cancellation_requested","dead_lettered_at"}.issubset(cols)
    assert APP_VERSION == "6.3.34" and SCHEMA_VERSION == "6.3.13"


def test_job_policies_isolate_cpu_cad_ai_io_and_maintenance():
    assert policy_for("design_review").queue == "cpu"
    assert policy_for("cad_analysis").resource_class == "cad"
    assert policy_for("translation").queue == "ai"
    assert policy_for("integration_sync").queue == "io"
    assert policy_for("projection_rebuild").queue == "maintenance"


def test_project_concurrency_limit_defers_second_job(monkeypatch):
    _, Factory = _factory()
    monkeypatch.setenv("JOB_PROJECT_DEFAULT_CONCURRENCY", "1")
    from app.core.config import get_settings
    get_settings.cache_clear()
    try:
        with Factory() as db:
            a=create_job(db,user="a",kind="design_review",project_code="P1")
            b=create_job(db,user="b",kind="design_review",project_code="P1")
            acquire_execution_slot(db,a,worker_id="w1")
            import pytest
            with pytest.raises(ProjectConcurrencyBusy):
                acquire_execution_slot(db,b,worker_id="w2")
            assert b.status == "queued" and b.attempt_count == 0
    finally:
        get_settings.cache_clear()


def test_cancellation_is_cooperative_and_queued_job_finishes_cancelled():
    _, Factory = _factory()
    with Factory() as db:
        job=create_job(db,user="u",kind="document_ingest",project_code="P1")
        request_cancellation(db,job)
        assert job.status == "cancelled"
        assert job.cancellation_requested is True and job.finished_at is not None


def test_retry_budget_enters_dead_letter_and_admin_replay_resets_budget():
    _, Factory = _factory()
    with Factory() as db:
        job=create_job(db,user="u",kind="design_review")
        job.max_attempts=1; db.commit()
        acquire_execution_slot(db,job,worker_id="w")
        terminal=mark_failure(db,job,RuntimeError("boom"))
        assert terminal is True and job.status == "dead_letter" and job.dead_lettered_at is not None
        retry_dead_letter(db,job)
        assert job.status == "queued" and job.attempt_count == 0 and job.error is None


def test_workload_snapshot_contains_resource_classes_and_safe_limits():
    _, Factory = _factory()
    with Factory() as db:
        create_job(db,user="u",kind="design_review",project_code="P1")
        create_job(db,user="u",kind="translation",project_code="P1")
        out=workload_snapshot(db)
        assert set(out["queues"]) == {"interactive","cpu","io","cad","ai","maintenance"}
        assert out["resource_classes"]["cpu"]["queued"] == 1
        assert out["resource_classes"]["ai"]["queued"] == 1
        assert "cooperative" in out["safe_cancellation"]


def test_workload_defaults_keep_core_cpu_first_and_bounded():
    cfg=Settings()
    assert cfg.job_project_default_concurrency >= 1
    assert cfg.job_project_cad_concurrency == 1
    assert cfg.job_project_ai_concurrency == 1
    assert cfg.job_max_attempts_cap <= 8
    assert cfg.job_cancel_revoke_enabled is True
