from celery import Celery
from celery.signals import before_task_publish, heartbeat_sent, worker_ready, worker_shutting_down, worker_shutdown
from kombu import Queue
from app.core.config import get_settings
from app.core.deployment_safety import record_component_heartbeat, remove_component_heartbeat, task_publish_headers

cfg = get_settings()
celery = Celery(
    "mgc_engineering",
    broker=cfg.redis_url,
    backend=cfg.redis_url,
    include=["app.workers.tasks"],
    task_cls="app.workers.version_guard:VersionGuardedTask",
)

# Resource classes are queues, not permissions. They isolate capacity so a large CAD/OCR
# workload cannot starve interactive engineering HTTP flows or maintenance projections.
#
# v6.3.11 compatibility window: older producers may still publish directly to the
# historical queue names. Workers consume these aliases, while all current internal
# task routing uses the resource-class queues below. Keep this map as migration evidence
# until legacy producers are retired.
LEGACY_TASK_ROUTES = {
    "run_design_review": {"queue": "heavy", "priority": 6},
    "sync_all_integrations": {"queue": "background", "priority": 1},
}
celery.conf.update(
    task_track_started=True,
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_default_queue="cpu",
    task_default_priority=4,
    task_queues=tuple(Queue(name) for name in ("interactive", "cpu", "io", "cad", "ai", "maintenance", "heavy", "background", "default")),
    task_routes={
        "run_design_review": {"queue": "cpu", "priority": 7},
        "ingest_document": {"queue": "cpu", "priority": 6},
        "sync_external_system": {"queue": "io", "priority": 2},
        "sync_all_integrations": {"queue": "io", "priority": 1},
        "capture_operational_health": {"queue": "maintenance", "priority": 1},
        "process_projection_outbox": {"queue": "maintenance", "priority": 2},
        "workload_housekeeping": {"queue": "maintenance", "priority": 1},
    },
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    task_time_limit=7200,
    task_soft_time_limit=6900,
    broker_transport_options={
        "priority_steps": [0, 1, 3, 4, 6, 7, 9],
        "queue_order_strategy": "priority",
    },
)

beat_schedule = {}
if cfg.projection_worker_enabled:
    beat_schedule["process-projection-outbox"] = {
        "task": "process_projection_outbox",
        "schedule": max(cfg.projection_worker_interval_seconds, 5),
    }
if cfg.integration_sync_enabled:
    beat_schedule["sync-enabled-engineering-integrations"] = {
        "task": "sync_all_integrations",
        "schedule": max(cfg.integration_sync_interval_seconds, 60),
    }
if cfg.operational_sampling_enabled:
    beat_schedule["capture-operational-health"] = {
        "task": "capture_operational_health",
        "schedule": max(cfg.operational_sampling_interval_seconds, 30),
    }
if cfg.job_scheduler_enabled:
    beat_schedule["workload-housekeeping"] = {
        "task": "workload_housekeeping",
        "schedule": max(cfg.job_scheduler_interval_seconds, 30),
    }
if beat_schedule:
    celery.conf.beat_schedule = beat_schedule


# v6.3.16 runtime envelope and ephemeral component registry. These hooks are protection and
# diagnostics only; Redis never becomes engineering truth.
@before_task_publish.connect
def _mgc_publish_runtime_headers(headers=None, **_kwargs):
    if headers is not None:
        headers.update(task_publish_headers())


def _worker_node(sender) -> str:
    eventer = getattr(sender, "eventer", None)
    return str(
        getattr(sender, "hostname", None)
        or getattr(sender, "nodename", None)
        or getattr(eventer, "hostname", None)
        or "worker@unknown"
    )[:255]


@worker_ready.connect
def _mgc_worker_ready(sender=None, **_kwargs):
    record_component_heartbeat("worker", node=_worker_node(sender), state="active")


@heartbeat_sent.connect
def _mgc_worker_heartbeat(sender=None, **_kwargs):
    record_component_heartbeat("worker", node=_worker_node(sender), state="active")


@worker_shutting_down.connect
def _mgc_worker_draining(sender=None, **_kwargs):
    record_component_heartbeat("worker", node=_worker_node(sender), state="draining")


@worker_shutdown.connect
def _mgc_worker_shutdown(sender=None, **_kwargs):
    remove_component_heartbeat("worker", node=_worker_node(sender))
