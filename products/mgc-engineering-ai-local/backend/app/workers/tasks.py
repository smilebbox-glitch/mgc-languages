from datetime import datetime, timedelta, timezone
import socket

from celery.exceptions import MaxRetriesExceededError
from sqlalchemy import select

from app.core.config import get_settings
from app.core.operational_health import readiness_snapshot
from app.db.models import ComputeJob, Document, ExternalSystem
from app.db.session import SessionLocal
from app.integrations.sync import IntegrationSyncBusy, sync_external_system
from app.services.ingest import ingest_document
from app.services.design_review import run_design_review
from app.services.production_support import capture_health_samples, incident_evidence_snapshot, reconcile_automated_incident_evidence
from app.services.projection_outbox import drain_projection_outbox
from app.services.background_jobs import (
    ActiveJobLease, JobCancelled, ProjectConcurrencyBusy, StaleJobDelivery,
    acquire_execution_slot, check_cancelled, mark_failure, mark_success,
    recover_expired_leases, set_progress,
)
from app.workers.celery_app import celery


def _worker_id(task) -> str:
    return str(getattr(task.request, "hostname", None) or socket.gethostname())


def _retry_countdown(job: ComputeJob) -> int:
    cfg = get_settings()
    exp = max(int(job.attempt_count or 1) - 1, 0)
    return min(int(cfg.job_retry_max_seconds), int(cfg.job_retry_base_seconds) * (2 ** min(exp, 8)))


def _defer_for_project_slot(task, job: ComputeJob):
    try:
        raise task.retry(countdown=max(5, min(30, _retry_countdown(job))), max_retries=None)
    except MaxRetriesExceededError:
        return {"status": "deferred", "reason": "project_concurrency"}


@celery.task(name="ingest_document", bind=True)
def ingest_document_task(self, document_id: str, job_id: str | None = None, dispatch_token: str | None = None):
    with SessionLocal() as db:
        doc = db.get(Document, document_id)
        if not doc:
            return {"error": "not found"}
        job = db.get(ComputeJob, job_id) if job_id else None
        if job:
            try:
                acquire_execution_slot(db, job, worker_id=_worker_id(self), dispatch_token=dispatch_token)
            except JobCancelled:
                return {"status": "cancelled"}
            except StaleJobDelivery:
                return {"status": "stale_delivery"}
            except (ProjectConcurrencyBusy, ActiveJobLease):
                return _defer_for_project_slot(self, job)
            job.celery_task_id = self.request.id
            db.commit()
            set_progress(db, job, 5, "Подготовка документа", dispatch_token=dispatch_token)
        try:
            ingest_document(db, doc)
            result = {"id": doc.id, "status": doc.status.value, "error": doc.error}
            if job:
                if doc.status.value == "failed":
                    raise RuntimeError(doc.error or "document ingestion failed")
                check_cancelled(db, job, dispatch_token=dispatch_token)
                mark_success(db, job, result, dispatch_token=dispatch_token)
            return result
        except JobCancelled:
            return {"status": "cancelled"}
        except StaleJobDelivery:
            return {"status": "stale_delivery"}
        except Exception as exc:
            if not job:
                raise
            try:
                terminal = mark_failure(db, job, exc, dispatch_token=dispatch_token)
            except StaleJobDelivery:
                return {"status": "stale_delivery"}
            if terminal:
                raise
            raise self.retry(exc=exc, countdown=_retry_countdown(job), max_retries=max(int(job.max_attempts or 1), 1))


@celery.task(name="sync_external_system")
def sync_external_system_task(system_id: str):
    cfg = get_settings()
    with SessionLocal() as db:
        system = db.get(ExternalSystem, system_id)
        if not system or not system.enabled:
            return {"status": "skipped", "reason": "missing_or_disabled"}
        if system.connector_type == "cad_gateway":
            return {"status": "skipped", "reason": "converter_not_source"}
        try:
            return sync_external_system(db, system, system.acl_groups or ["all"], cfg.integration_sync_page_limit, cfg.integration_sync_max_pages)
        except IntegrationSyncBusy:
            return {"status": "skipped", "reason": "sync_already_active", "system": system.code}


@celery.task(name="sync_all_integrations")
def sync_all_integrations_task():
    cfg = get_settings()
    now = datetime.now(timezone.utc)
    results = []
    with SessionLocal() as db:
        systems = db.scalars(select(ExternalSystem).where(ExternalSystem.enabled == True)).all()  # noqa: E712
        for system in systems:
            if system.connector_type == "cad_gateway":
                continue
            config = system.config_json or {}
            if config.get("sync_enabled", True) is False:
                continue
            interval_min = int(config.get("sync_interval_minutes", cfg.integration_sync_default_minutes))
            due = not system.last_sync_at or system.last_sync_at <= now - timedelta(minutes=max(interval_min, 1))
            if not due:
                continue
            try:
                results.append({"system": system.code, **sync_external_system(db, system, system.acl_groups or ["all"], cfg.integration_sync_page_limit, cfg.integration_sync_max_pages)})
            except IntegrationSyncBusy:
                results.append({"system": system.code, "status": "skipped", "reason": "sync_already_active"})
    return {"systems": results, "count": len(results)}


@celery.task(name="run_design_review", bind=True)
def run_design_review_task(self, job_id: str, part_number: str, revision: str, baseline_revision: str | None, user: str, allowed_document_ids: list[str], dispatch_token: str | None = None):
    with SessionLocal() as db:
        job = db.get(ComputeJob, job_id)
        if not job:
            return {"error": "job not found"}
        try:
            acquire_execution_slot(db, job, worker_id=_worker_id(self), dispatch_token=dispatch_token)
        except JobCancelled:
            return {"status": "cancelled"}
        except StaleJobDelivery:
            return {"status": "stale_delivery"}
        except (ProjectConcurrencyBusy, ActiveJobLease):
            return _defer_for_project_slot(self, job)
        job.celery_task_id = self.request.id
        db.commit()
        set_progress(db, job, 10, "Сбор engineering evidence", dispatch_token=dispatch_token)
        try:
            review = run_design_review(db, part_number, revision, baseline_revision, user, set(allowed_document_ids))
            result = {
                "id": review.id, "part_number": review.part_number, "revision": review.revision,
                "baseline_revision": review.baseline_revision, "status": review.status.value,
                "risk_score": review.risk_score, "summary": review.summary, "findings": review.findings,
                "evidence_document_ids": review.evidence_document_ids, "report": review.report_json,
            }
            check_cancelled(db, job, dispatch_token=dispatch_token)
            mark_success(db, job, result, dispatch_token=dispatch_token)
            return result
        except JobCancelled:
            return {"status": "cancelled"}
        except StaleJobDelivery:
            return {"status": "stale_delivery"}
        except Exception as exc:
            try:
                terminal = mark_failure(db, job, exc, dispatch_token=dispatch_token)
            except StaleJobDelivery:
                return {"status": "stale_delivery"}
            if terminal:
                raise
            raise self.retry(exc=exc, countdown=_retry_countdown(job), max_retries=max(int(job.max_attempts or 1), 1))


@celery.task(name="capture_operational_health")
def capture_operational_health_task():
    with SessionLocal() as db:
        try:
            readiness = readiness_snapshot()
            result = capture_health_samples(db, readiness)
            report = incident_evidence_snapshot(db, readiness=readiness)
            result["incident_evidence"] = {
                "status": report["status"],
                "signal_count": report["signal_count"],
                "highest_severity": report["highest_severity"],
                "payload_sha256": report["integrity"]["payload_sha256"],
            }
            if get_settings().automated_incident_materialization_enabled:
                result["incident_reconciliation"] = reconcile_automated_incident_evidence(
                    db, report, actor="system-observer", materialize=True
                )
            return result
        except Exception:
            return {"status": "failed", "reason": "health_snapshot_unavailable"}


@celery.task(name="process_projection_outbox")
def process_projection_outbox_task(limit: int | None = None):
    return drain_projection_outbox(SessionLocal, limit=limit)


@celery.task(name="workload_housekeeping")
def workload_housekeeping_task():
    """Recover expired worker leases using PostgreSQL fencing and replay policy.

    Old deliveries are fenced before any requeue. Only explicitly replay-safe job kinds are
    automatically re-dispatched; engineering decision jobs become `orphaned` for admin review.
    """
    with SessionLocal() as db:
        return recover_expired_leases(db, actor="scheduler", dispatch=True)
