from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any
import uuid

from sqlalchemy import func, select, text
from sqlalchemy.orm import Session, object_session

from app.core.config import get_settings
from app.core.resilience import CircuitOpenError, circuit_allows, record_failure, record_success
from app.db.models import ComputeJob, ComputeJobRecoveryEvent


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _as_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    return value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)


@dataclass(frozen=True)
class JobPolicy:
    resource_class: str
    queue: str
    priority: int
    max_attempts: int
    timeout_seconds: int
    recovery_mode: str = "manual"  # manual | safe_replay


# Automatic replay is deliberately opt-in. A workflow is marked safe_replay only when
# its authoritative writes converge when repeated. Human engineering decisions remain
# manual-recovery so infrastructure cannot silently duplicate a decision-producing run.
JOB_POLICIES: dict[str, JobPolicy] = {
    "design_review": JobPolicy("cpu", "cpu", 7, 3, 1800, "manual"),
    "document_ingest": JobPolicy("cpu", "cpu", 6, 3, 3600, "safe_replay"),
    "cad_analysis": JobPolicy("cad", "cad", 6, 2, 7200, "manual"),
    "ocr": JobPolicy("cpu", "cpu", 5, 3, 3600, "manual"),
    "translation": JobPolicy("ai", "ai", 6, 3, 1800, "manual"),
    "rag_index": JobPolicy("ai", "ai", 5, 3, 3600, "manual"),
    "integration_sync": JobPolicy("io", "io", 2, 5, 1800, "manual"),
    "projection_rebuild": JobPolicy("maintenance", "maintenance", 1, 5, 7200, "manual"),
    "read_model_rebuild": JobPolicy("maintenance", "maintenance", 1, 5, 3600, "manual"),
}
DEFAULT_POLICY = JobPolicy("cpu", "cpu", 4, 3, 1800, "manual")


class JobCancelled(RuntimeError):
    pass


class ProjectConcurrencyBusy(RuntimeError):
    pass


class ActiveJobLease(RuntimeError):
    pass


class StaleJobDelivery(RuntimeError):
    """A late/duplicate Celery delivery no longer owns the PostgreSQL job ledger."""


class JobRecoveryNotAllowed(RuntimeError):
    pass


def policy_for(kind: str) -> JobPolicy:
    return JOB_POLICIES.get(kind, DEFAULT_POLICY)


def _lease_deadline(job: ComputeJob, now: datetime | None = None) -> datetime:
    cfg = get_settings()
    base = now or _now()
    seconds = max(int(job.timeout_seconds or 1), 1) + max(int(cfg.job_worker_lease_grace_seconds), 0)
    return base + timedelta(seconds=seconds)


def _lease_expired(job: ComputeJob, now: datetime | None = None) -> bool:
    now = now or _now()
    deadline = _as_utc(job.lease_expires_at)
    if deadline is not None:
        return deadline <= now
    # Transition compatibility for jobs that were already running during a 6.3.12 -> 6.3.13 upgrade.
    hb = _as_utc(job.heartbeat_at or job.started_at or job.updated_at or job.created_at)
    if hb is None:
        return False
    cfg = get_settings()
    seconds = max(int(job.timeout_seconds or 1), 1) + max(int(cfg.job_worker_lease_grace_seconds), 0)
    return hb + timedelta(seconds=seconds) <= now


def _assert_fence(job: ComputeJob, dispatch_token: str | None) -> None:
    expected = job.dispatch_token
    if expected:
        if not dispatch_token or dispatch_token != expected:
            raise StaleJobDelivery("Delivery fencing token is stale")
    elif dispatch_token:
        # A token-bearing delivery may never write to a legacy/unfenced ledger row.
        raise StaleJobDelivery("Delivery fencing token has no matching ledger token")


def _fence_old_delivery(job: ComputeJob) -> None:
    # Rotate token without incrementing dispatch_generation. Generation counts real dispatches;
    # this UUID exists only to make every older message fail closed.
    job.dispatch_token = str(uuid.uuid4())


def _record_recovery(
    db: Session,
    job: ComputeJob,
    *,
    action: str,
    reason: str,
    actor: str,
    prior_status: str | None,
    prior_worker_id: str | None,
    prior_task_id: str | None,
    prior_generation: int,
    new_generation: int | None = None,
) -> ComputeJobRecoveryEvent:
    event = ComputeJobRecoveryEvent(
        job_id=job.id,
        recovery_number=max(int(job.recovery_count or 0), 1),
        action=action,
        reason=reason[:512],
        actor=actor[:255],
        prior_status=prior_status,
        prior_worker_id=prior_worker_id,
        prior_celery_task_id=prior_task_id,
        prior_dispatch_generation=max(int(prior_generation or 0), 0),
        new_dispatch_generation=new_generation,
    )
    db.add(event)
    return event


def create_job(
    db: Session,
    *,
    user: str,
    kind: str,
    project_code: str | None = None,
    manufacturing_area: str | None = None,
    request_json: dict[str, Any] | None = None,
) -> ComputeJob:
    p = policy_for(kind)
    cfg = get_settings()
    max_attempts = max(1, min(int(p.max_attempts), int(cfg.job_max_attempts_cap)))
    job = ComputeJob(
        user=user,
        project_code=(project_code or "").upper() or None,
        manufacturing_area=manufacturing_area,
        kind=kind,
        resource_class=p.resource_class,
        queue=p.queue,
        priority=p.priority,
        max_attempts=max_attempts,
        timeout_seconds=p.timeout_seconds,
        status="queued",
        request_json=request_json or {},
        dispatch_generation=0,
        recovery_count=0,
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


def serialize_job(job: ComputeJob, *, include_result: bool = False, admin: bool = False) -> dict[str, Any]:
    out = {
        "job_id": job.id,
        "state": job.status,
        "kind": job.kind,
        "resource_class": job.resource_class,
        "queue": job.queue,
        "priority": int(job.priority or 0),
        "project_code": job.project_code,
        "manufacturing_area": job.manufacturing_area,
        "progress_percent": int(job.progress_percent or 0),
        "progress_message": job.progress_message,
        "cancellation_requested": bool(job.cancellation_requested),
        "attempt_count": int(job.attempt_count or 0),
        "max_attempts": int(job.max_attempts or 1),
        "dispatch_generation": int(job.dispatch_generation or 0),
        "recovery_count": int(job.recovery_count or 0),
        "created_at": job.created_at.isoformat() if job.created_at else None,
        "started_at": job.started_at.isoformat() if job.started_at else None,
        "finished_at": job.finished_at.isoformat() if job.finished_at else None,
    }
    if admin:
        out.update({
            "worker_id": job.worker_id,
            "lease_expires_at": job.lease_expires_at.isoformat() if job.lease_expires_at else None,
            "last_dispatch_at": job.last_dispatch_at.isoformat() if job.last_dispatch_at else None,
            "last_recovery_at": job.last_recovery_at.isoformat() if job.last_recovery_at else None,
            "recovery_reason": job.recovery_reason,
            "recovery_mode": policy_for(job.kind).recovery_mode,
        })
    if include_result and job.status == "success":
        out["result"] = job.result_json or {}
    if job.status in {"failure", "dead_letter", "orphaned"}:
        out["error"] = job.error if admin else "Задача требует внимания. Подробности доступны инженерному администратору."
    return out


def set_progress(
    db: Session,
    job: ComputeJob,
    percent: int,
    message: str | None = None,
    *,
    dispatch_token: str | None = None,
) -> None:
    db.refresh(job)
    _assert_fence(job, dispatch_token)
    if job.status != "running":
        raise StaleJobDelivery(f"Job is no longer running: {job.status}")
    now = _now()
    job.progress_percent = max(0, min(int(percent), 100))
    job.progress_message = (message or "")[:512] or None
    job.heartbeat_at = now
    job.lease_expires_at = _lease_deadline(job, now)
    db.commit()


def request_cancellation(db: Session, job: ComputeJob) -> ComputeJob:
    if job.status in {"success", "failure", "cancelled", "dead_letter"}:
        return job
    job.cancellation_requested = True
    if job.status in {"queued", "retry_wait", "orphaned"}:
        job.status = "cancelled"
        job.finished_at = _now()
        job.progress_message = "Отменено до начала выполнения"
        job.lease_expires_at = None
        _fence_old_delivery(job)
    db.commit()
    db.refresh(job)
    return job


def check_cancelled(db: Session, job: ComputeJob, *, dispatch_token: str | None = None) -> None:
    db.refresh(job)
    _assert_fence(job, dispatch_token)
    if job.status not in {"running", "queued", "retry_wait"}:
        raise StaleJobDelivery(f"Job ledger moved to {job.status}")
    if job.cancellation_requested or job.status == "cancelled":
        if job.status != "cancelled":
            job.status = "cancelled"
            job.finished_at = _now()
            job.lease_expires_at = None
            db.commit()
        raise JobCancelled("Job cancellation requested")


def _project_limit(resource_class: str) -> int:
    cfg = get_settings()
    if resource_class == "ai":
        return max(1, int(cfg.job_project_ai_concurrency))
    if resource_class == "cad":
        return max(1, int(cfg.job_project_cad_concurrency))
    return max(1, int(cfg.job_project_default_concurrency))


def acquire_execution_slot(
    db: Session,
    job: ComputeJob,
    *,
    worker_id: str,
    dispatch_token: str | None = None,
) -> None:
    db.refresh(job)
    _assert_fence(job, dispatch_token)
    if job.cancellation_requested or job.status == "cancelled":
        raise JobCancelled("Job cancellation requested")
    if job.status == "running":
        # A second delivery may not enter while the current lease is still valid.
        if not _lease_expired(job):
            raise ActiveJobLease("Another delivery still owns the active job lease")
        raise StaleJobDelivery("Expired running ledger must be recovered before re-entry")
    if job.status not in {"queued", "retry_wait"}:
        raise StaleJobDelivery(f"Job state does not accept execution: {job.status}")

    # Serialize the count/update decision for the same project/resource on PostgreSQL.
    if job.project_code and db.bind is not None and db.bind.dialect.name == "postgresql":
        lock_key = f"mgc-job:{job.project_code}:{job.resource_class}"
        db.execute(text("SELECT pg_advisory_xact_lock(hashtext(:key))"), {"key": lock_key})
    if job.project_code:
        running = int(db.scalar(select(func.count(ComputeJob.id)).where(
            ComputeJob.project_code == job.project_code,
            ComputeJob.resource_class == job.resource_class,
            ComputeJob.status == "running",
            ComputeJob.id != job.id,
        )) or 0)
        if running >= _project_limit(job.resource_class):
            raise ProjectConcurrencyBusy(f"Project concurrency limit reached for {job.resource_class}")
    now = _now()
    job.status = "running"
    job.worker_id = worker_id[:255]
    job.started_at = job.started_at or now
    job.heartbeat_at = now
    job.lease_expires_at = _lease_deadline(job, now)
    job.attempt_count = int(job.attempt_count or 0) + 1
    job.progress_percent = max(int(job.progress_percent or 0), 1)
    db.commit()


def mark_success(
    db: Session,
    job: ComputeJob,
    result: dict[str, Any] | None = None,
    *,
    dispatch_token: str | None = None,
) -> None:
    db.refresh(job)
    _assert_fence(job, dispatch_token)
    if job.status != "running":
        raise StaleJobDelivery(f"Job is no longer running: {job.status}")
    if job.cancellation_requested:
        job.status = "cancelled"
        job.finished_at = _now()
        job.lease_expires_at = None
        db.commit()
        raise JobCancelled("Job cancellation requested")
    job.status = "success"
    job.result_json = result or {}
    job.progress_percent = 100
    job.progress_message = "Завершено"
    job.finished_at = _now()
    job.heartbeat_at = job.finished_at
    job.lease_expires_at = None
    job.error = None
    db.commit()


def mark_failure(
    db: Session,
    job: ComputeJob,
    exc: BaseException,
    *,
    dispatch_token: str | None = None,
) -> bool:
    """Persist failure. Returns True when the job exhausted retry budget and entered DLQ."""
    db.refresh(job)
    _assert_fence(job, dispatch_token)
    if job.status != "running":
        raise StaleJobDelivery(f"Job is no longer running: {job.status}")
    terminal = int(job.attempt_count or 0) >= int(job.max_attempts or 1)
    job.error = f"{type(exc).__name__}: {str(exc)}"[:1000]
    job.heartbeat_at = _now()
    job.lease_expires_at = None
    job.worker_id = None
    if terminal:
        job.status = "dead_letter"
        job.dead_lettered_at = _now()
        job.finished_at = job.dead_lettered_at
        job.progress_message = "Retry budget exhausted"
    else:
        job.status = "retry_wait"
        job.progress_message = "Ожидает повторной попытки"
    db.commit()
    return terminal


def retry_dead_letter(db: Session, job: ComputeJob) -> ComputeJob:
    if job.status not in {"dead_letter", "failure"}:
        raise ValueError("Only failed/dead-letter jobs can be retried")
    job.status = "queued"
    job.cancellation_requested = False
    job.dead_lettered_at = None
    job.finished_at = None
    job.error = None
    job.worker_id = None
    job.lease_expires_at = None
    job.progress_percent = 0
    job.progress_message = "Повторно поставлено в очередь"
    # A manual replay starts a fresh retry budget but preserves recovery history separately.
    job.attempt_count = 0
    _fence_old_delivery(job)
    db.commit()
    db.refresh(job)
    return job


def prepare_orphan_recovery(db: Session, job: ComputeJob, *, actor: str, confirm: str) -> ComputeJob:
    if confirm != "RECOVER_ORPHANED":
        raise JobRecoveryNotAllowed("Manual orphan recovery requires confirm=RECOVER_ORPHANED")
    if job.status != "orphaned":
        raise JobRecoveryNotAllowed("Only orphaned jobs can use the orphan recovery flow")
    if int(job.attempt_count or 0) >= int(job.max_attempts or 1):
        job.status = "dead_letter"
        job.dead_lettered_at = _now()
        job.finished_at = job.dead_lettered_at
        job.progress_message = "Retry budget exhausted during orphan recovery"
        db.commit()
        raise JobRecoveryNotAllowed("Retry budget is exhausted; job moved to dead letter")
    prior_generation = int(job.dispatch_generation or 0)
    job.status = "queued"
    job.cancellation_requested = False
    job.worker_id = None
    job.celery_task_id = None
    job.lease_expires_at = None
    job.error = None
    job.progress_message = "Ручное восстановление подтверждено; повторная доставка подготовлена"
    _fence_old_delivery(job)
    _record_recovery(
        db, job, action="manual_requeue_prepared", reason=job.recovery_reason or "orphaned job",
        actor=actor, prior_status="orphaned", prior_worker_id=None, prior_task_id=None,
        prior_generation=prior_generation,
    )
    db.commit()
    db.refresh(job)
    return job


def list_recovery_events(db: Session, *, job_id: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
    q = select(ComputeJobRecoveryEvent).order_by(ComputeJobRecoveryEvent.created_at.desc()).limit(max(1, min(int(limit), 500)))
    if job_id:
        q = q.where(ComputeJobRecoveryEvent.job_id == job_id)
    rows = db.scalars(q).all()
    return [{
        "id": row.id,
        "job_id": row.job_id,
        "recovery_number": int(row.recovery_number or 0),
        "action": row.action,
        "reason": row.reason,
        "actor": row.actor,
        "prior_status": row.prior_status,
        "prior_worker_id": row.prior_worker_id,
        "prior_celery_task_id": row.prior_celery_task_id,
        "prior_dispatch_generation": int(row.prior_dispatch_generation or 0),
        "new_dispatch_generation": row.new_dispatch_generation,
        "created_at": row.created_at.isoformat() if row.created_at else None,
    } for row in rows]


def recover_expired_leases(db: Session, *, actor: str = "scheduler", dispatch: bool = True) -> dict[str, int]:
    """Fence expired deliveries and recover only explicitly replay-safe workflows.

    Human decision-producing tasks become `orphaned` and require a confirmed admin recovery.
    Replay-safe tasks may be re-dispatched automatically. Every lease incident is auditable.
    """
    cfg = get_settings()
    now = _now()
    max_rows = max(1, min(int(cfg.job_auto_recovery_max_per_cycle), 200))
    rows = db.scalars(
        select(ComputeJob).where(ComputeJob.status == "running").order_by(ComputeJob.started_at.asc()).limit(max_rows * 4)
    ).all()
    summary = {"examined": 0, "expired": 0, "auto_requeued": 0, "manual_orphaned": 0, "dead_lettered": 0, "cancelled": 0, "dispatch_failed": 0}

    for job in rows:
        if summary["expired"] >= max_rows:
            break
        summary["examined"] += 1
        if not _lease_expired(job, now):
            continue
        summary["expired"] += 1
        prior_status = job.status
        prior_worker = job.worker_id
        prior_task = job.celery_task_id
        prior_generation = int(job.dispatch_generation or 0)
        reason = f"worker lease expired after timeout={int(job.timeout_seconds or 0)}s"
        job.recovery_count = int(job.recovery_count or 0) + 1
        job.last_recovery_at = now
        job.recovery_reason = reason
        job.worker_id = None
        job.lease_expires_at = None
        job.celery_task_id = None
        _fence_old_delivery(job)

        if job.cancellation_requested:
            job.status = "cancelled"
            job.finished_at = now
            job.progress_message = "Отменено после истечения worker lease"
            _record_recovery(db, job, action="cancelled", reason=reason, actor=actor,
                             prior_status=prior_status, prior_worker_id=prior_worker, prior_task_id=prior_task,
                             prior_generation=prior_generation)
            summary["cancelled"] += 1
            db.commit()
            continue

        if int(job.attempt_count or 0) >= int(job.max_attempts or 1):
            job.status = "dead_letter"
            job.dead_lettered_at = now
            job.finished_at = now
            job.error = "Worker lease expired and retry budget is exhausted"
            job.progress_message = "Worker lease expired; retry budget exhausted"
            _record_recovery(db, job, action="dead_lettered", reason=reason, actor=actor,
                             prior_status=prior_status, prior_worker_id=prior_worker, prior_task_id=prior_task,
                             prior_generation=prior_generation)
            summary["dead_lettered"] += 1
            db.commit()
            continue

        replay_safe = policy_for(job.kind).recovery_mode == "safe_replay"
        if bool(cfg.job_auto_recovery_enabled) and replay_safe:
            job.status = "queued"
            job.progress_message = "Восстановление после истечения worker lease"
            event = _record_recovery(db, job, action="auto_requeue", reason=reason, actor=actor,
                                     prior_status=prior_status, prior_worker_id=prior_worker, prior_task_id=prior_task,
                                     prior_generation=prior_generation)
            db.commit()
            if dispatch:
                try:
                    task = dispatch_job(job, reason="lease_recovery")
                    job.celery_task_id = task.id
                    event.new_dispatch_generation = int(job.dispatch_generation or 0)
                    db.commit()
                    summary["auto_requeued"] += 1
                except Exception as exc:
                    # Do not silently spin on broker failure. The job is fenced and requires operator review.
                    job.status = "orphaned"
                    job.error = f"Recovery dispatch failed: {type(exc).__name__}: {exc}"[:1000]
                    job.progress_message = "Автовосстановление не доставлено; требуется проверка администратора"
                    _fence_old_delivery(job)
                    _record_recovery(db, job, action="dispatch_failed", reason=str(exc) or type(exc).__name__, actor=actor,
                                     prior_status="queued", prior_worker_id=None, prior_task_id=None,
                                     prior_generation=int(job.dispatch_generation or 0))
                    db.commit()
                    summary["dispatch_failed"] += 1
            else:
                summary["auto_requeued"] += 1
            continue

        job.status = "orphaned"
        job.error = "Worker lease expired; automatic replay is not authorized for this job kind"
        job.progress_message = "Worker lease expired; manual recovery confirmation required"
        _record_recovery(db, job, action="manual_review", reason=reason, actor=actor,
                         prior_status=prior_status, prior_worker_id=prior_worker, prior_task_id=prior_task,
                         prior_generation=prior_generation)
        summary["manual_orphaned"] += 1
        db.commit()

    return summary


def workload_snapshot(db: Session) -> dict[str, Any]:
    cfg = get_settings()
    rows = db.execute(select(ComputeJob.resource_class, ComputeJob.status, func.count(ComputeJob.id)).group_by(ComputeJob.resource_class, ComputeJob.status)).all()
    matrix: dict[str, dict[str, int]] = {}
    for resource, status, count in rows:
        matrix.setdefault(resource or "unknown", {})[status or "unknown"] = int(count)
    dlq = int(db.scalar(select(func.count(ComputeJob.id)).where(ComputeJob.status == "dead_letter")) or 0)
    orphaned = int(db.scalar(select(func.count(ComputeJob.id)).where(ComputeJob.status == "orphaned")) or 0)
    cancel_pending = int(db.scalar(select(func.count(ComputeJob.id)).where(ComputeJob.cancellation_requested == True, ComputeJob.status == "running")) or 0)  # noqa: E712
    recoveries = int(db.scalar(select(func.count(ComputeJobRecoveryEvent.id))) or 0)
    expired_running = sum(1 for x in db.scalars(select(ComputeJob).where(ComputeJob.status == "running")).all() if _lease_expired(x))
    return {
        "resource_classes": matrix,
        "dead_letter_jobs": dlq,
        "orphaned_jobs": orphaned,
        "expired_running_leases": expired_running,
        "recovery_events": recoveries,
        "running_cancel_requested": cancel_pending,
        "project_limits": {
            "default": int(cfg.job_project_default_concurrency),
            "cad": int(cfg.job_project_cad_concurrency),
            "ai": int(cfg.job_project_ai_concurrency),
        },
        "recovery": {
            "automatic_enabled": bool(cfg.job_auto_recovery_enabled),
            "max_per_cycle": int(cfg.job_auto_recovery_max_per_cycle),
            "lease_grace_seconds": int(cfg.job_worker_lease_grace_seconds),
            "safe_replay_kinds": sorted(k for k, p in JOB_POLICIES.items() if p.recovery_mode == "safe_replay"),
            "policy": "expired deliveries are fenced; only explicitly replay-safe jobs auto-requeue",
        },
        "queues": ["interactive", "cpu", "io", "cad", "ai", "maintenance"],
        "safe_cancellation": "queued tasks revoke immediately; running tasks stop only at cooperative boundaries",
    }


def _prepare_dispatch(db: Session, job: ComputeJob) -> str:
    if job.status not in {"queued", "retry_wait"}:
        raise ValueError(f"Job state {job.status} cannot be dispatched")
    job.dispatch_generation = int(job.dispatch_generation or 0) + 1
    job.dispatch_token = str(uuid.uuid4())
    job.last_dispatch_at = _now()
    job.celery_task_id = None
    db.commit()
    db.refresh(job)
    return str(job.dispatch_token)


def dispatch_job(job: ComputeJob, *, reason: str = "dispatch"):
    """Persist a new delivery fence before publishing to Celery.

    A worker must present the exact token embedded in this dispatch. Any older delivery is
    unable to mutate the PostgreSQL ledger after a retry/recovery generation is issued.
    """
    from app.workers.tasks import ingest_document_task, run_design_review_task

    if not circuit_allows("redis"):
        raise CircuitOpenError("redis")
    db = object_session(job)
    if db is None:
        raise RuntimeError("ComputeJob must be attached to a Session before dispatch")
    req = job.request_json or {}
    if job.kind == "document_ingest":
        document_id = str(req.get("document_id") or "")
        if not document_id:
            raise ValueError("document_ingest job is missing document_id")
        token = _prepare_dispatch(db, job)
        try:
            task = ingest_document_task.apply_async(
                args=[document_id, job.id, token], queue=job.queue, priority=int(job.priority or 4),
            )
        except Exception as exc:
            record_failure("redis", exc)
            raise
        record_success("redis")
        return task
    if job.kind == "design_review":
        token = _prepare_dispatch(db, job)
        try:
            task = run_design_review_task.apply_async(
                args=[
                    job.id, str(req.get("part_number") or ""), str(req.get("revision") or ""),
                    req.get("baseline_revision"), job.user, list(req.get("allowed_document_ids") or []), token,
                ],
                queue=job.queue, priority=int(job.priority or 4),
            )
        except Exception as exc:
            record_failure("redis", exc)
            raise
        record_success("redis")
        return task
    raise ValueError(f"Managed dispatch is not implemented for job kind: {job.kind}")
