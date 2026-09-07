# Engineering Compute Manager — v3.7

The CPU/GPU runtime now separates work into logical queues:

| Queue | Priority | Examples |
|---|---:|---|
| `interactive` | 9 | reserved for short engineer-facing jobs |
| `heavy` | 6 | Design Review, document ingestion/CAD-heavy work |
| `default` | 4 | normal asynchronous work |
| `background` | 1 | PLM/ERP/file-share synchronization |

Celery uses `worker_prefetch_multiplier=1`, late acknowledgement and Redis priority routing. A worker therefore does not reserve a large batch of background jobs while an engineer is waiting.

## Asynchronous Design Review

`POST /api/v1/design-reviews/async` creates a protected `ComputeJob` and queues the review. The UI polls `GET /api/v1/compute/tasks/{job_id}` and shows a simple progress message.

A job belongs to the engineer who created it. Another engineer receives 404 for that job; engineering administrators can inspect jobs for support. This prevents asynchronous result IDs becoming an ACL bypass.

## CPU behaviour

CPU mode defaults to one compute worker (`CPU_WORKER_CONCURRENCY=1`) to avoid RAM/CPU oversubscription. `make cpu-check` remains the recommended sizing command before increasing concurrency.
