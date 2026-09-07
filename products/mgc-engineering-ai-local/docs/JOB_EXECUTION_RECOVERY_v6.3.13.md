# Job Execution Recovery & Lease Safety — v6.3.13

## Goal

Make background engineering work recoverable after worker/process/broker failures without allowing a delayed Celery delivery to overwrite a newer execution or silently duplicate a human engineering decision.

PostgreSQL remains the authoritative job ledger. Redis/Celery remains execution transport and may be lost/restarted without becoming engineering truth.

## Delivery fencing

Every managed dispatch receives a random `dispatch_token` and increments `dispatch_generation` in PostgreSQL **before** the message is published. The token travels with the Celery message. Progress, cancellation checkpoints, success and failure writes validate the token against the authoritative ledger.

When recovery or manual replay occurs, the old token is fenced. A delayed message from an earlier generation therefore cannot update the job ledger after ownership changed.

## Worker lease

A running job owns a PostgreSQL lease (`lease_expires_at`). Admission writes worker identity, heartbeat and lease. Progress refreshes heartbeat and lease. A duplicate delivery cannot enter while the current lease is active.

The default lease horizon is the job's declared timeout plus `JOB_WORKER_LEASE_GRACE_SECONDS=120`. Housekeeping inspects expired leases in bounded batches.

## Recovery policy

Automatic replay is explicit allowlist behavior, not the default.

- `document_ingest`: `safe_replay`. Current ingestion writes converge by replacing document-derived chunks/BOM rows and using existing projection idempotency controls. An expired job may be fenced and requeued automatically.
- `design_review`: `manual`. A design review can create engineering decision evidence, so infrastructure does not silently execute it twice. An expired run becomes `orphaned`.
- other registered heavy/AI/CAD/integration/maintenance classes: `manual` until their side-effect/idempotency contract is independently proven.

An orphaned job requires Engineering Admin to call the recovery endpoint with the exact confirmation `RECOVER_ORPHANED`. Recovery still respects the existing retry budget; an exhausted budget moves the job to DLQ.

## Recovery audit

`compute_job_recovery_events` records each lease incident/recovery decision with recovery number, action, reason, actor, prior status/worker/task ID, prior dispatch generation and, when available, the new generation.

Engineering Admin APIs:

- `POST /api/v1/operations/workload/{job_id}/recover?confirm=RECOVER_ORPHANED`
- `GET /api/v1/operations/workload/recovery-events`

## Operations and metrics

The workload snapshot now includes:

- orphaned jobs;
- expired running leases;
- recovery-event count;
- automatic-recovery switch and bounded cycle size;
- lease grace;
- explicit safe-replay job kinds.

Prometheus adds:

- `mgc_compute_orphaned_jobs`;
- `mgc_compute_expired_running_leases`;
- `mgc_compute_recovery_events_total`.

Orphaned jobs or expired leases make Operations AMBER. They do not make Redis/Celery authoritative and do not convert infrastructure health into an engineering release decision.

## Safety invariants

1. No stale delivery may write progress/result/failure after fencing.
2. No second delivery may acquire an active lease.
3. Automatic replay is opt-in per job kind.
4. Human decision-producing work is not automatically duplicated.
5. Retry/DLQ limits remain bounded.
6. Recovery activity is auditable in PostgreSQL.
7. No SIGKILL-based cancellation is introduced.
8. Recovery does not authorize engineering approval, release, PLM/MES write-back, or production equipment control.
