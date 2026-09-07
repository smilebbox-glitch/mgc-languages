# MGC Engineering AI Local v6.3.11 — Background Jobs, Scheduler & Workload Isolation

## Goal
Keep heavy CAD/OCR/ingestion/AI/maintenance work out of the interactive API capacity pool without making Redis/Celery a source of engineering truth.

## Resource classes
- `interactive` — short user-triggered asynchronous actions.
- `cpu` — design review, document ingestion, OCR and other CPU-heavy work.
- `io` — external-system synchronization and network-bound tasks.
- `cad` — native/large geometry processing; default per-project concurrency is 1.
- `ai` — translation/semantic/LLM jobs; only AI/Advanced deployments need an AI worker.
- `maintenance` — projection/read-model rebuilds, health sampling and housekeeping.

Resource class is scheduling metadata, not authorization.

## Managed ComputeJob
`ComputeJob` now records project/area, resource class, queue, priority, progress, cancellation request, retry budget, timeout, worker identity, heartbeat, start/finish and dead-letter state. PostgreSQL remains the authoritative job ledger; Celery/Redis is transport/execution infrastructure.

## Per-project concurrency
Before a managed job enters `running`, PostgreSQL serializes the project/resource admission decision (PostgreSQL advisory transaction lock) and checks configured concurrency. Defaults: ordinary CPU work 2 per project, CAD 1, AI 1. A busy project slot defers the task instead of consuming another attempt.

## Cancellation
Queued/retry-wait jobs can be revoked immediately. Running jobs use cooperative cancellation at safe boundaries. MGC intentionally does not SIGKILL a worker inside database/CAD processing because that can leave partial external side effects.

## Retry and DLQ
Failures use bounded exponential retry. When the retry budget is exhausted the DB ledger enters `dead_letter`. Engineering Admin can explicitly replay a DLQ job; replay is audited and creates a fresh retry budget.

## Worker topology
The base Compose separates capacity into `worker` (interactive), `worker-cpu`, `worker-io`, `worker-cad`, and profile-gated `worker-ai`. Prefetch is 1 and tasks use late acknowledgement/reject-on-worker-lost.

## Scheduler
Celery Beat continues existing projection/integration/health schedules and adds workload housekeeping. Housekeeping is observe-only for overdue worker heartbeats: it does not automatically duplicate a possibly still-running engineering task.

## Operations
`GET /api/v1/operations/workload` exposes sanitized resource/status counts, DLQ count and concurrency policy. Prometheus/Support Bundle include workload state. DLQ or running cancellation requests make Operations AMBER but do not make authoritative Core readiness RED.
## Legacy queue transition compatibility (v6.3.12 verification)

The resource-class queues remain authoritative for new internal dispatch. During the migration window, workers also consume historical `heavy`, `background` and `default` queue aliases so older producers/automation cannot strand queued work after an upgrade. Monitoring continues to normalize these aliases into `cpu`/`maintenance`; the aliases do not reintroduce shared-capacity routing for new jobs.

