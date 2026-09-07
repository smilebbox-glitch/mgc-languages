# MGC Engineering AI Local v6.3.13
## Execution Recovery & Job Lease Safety

v6.3.13 — технический hardening-релиз поверх v6.3.12. Основная задача — безопасно восстанавливать тяжёлые фоновые инженерные задания после потери worker/process/broker, не допуская записи результата от запоздалой/дублированной Celery-доставки и не повторяя автоматически инженерные решения.

## Главное

- application version: **6.3.13**;
- database schema: **6.3.13** — additive/idempotent migration поверх 6.3.11;
- PostgreSQL остаётся authoritative ledger для managed compute jobs; Redis/Celery остаются transport/execution;
- каждому dispatch выдаётся новый `dispatch_token`, а `dispatch_generation` увеличивается **до** публикации сообщения;
- progress/success/failure/cancellation checkpoints проверяют fencing token и отклоняют stale delivery;
- running job получает PostgreSQL worker lease (`lease_expires_at`), который обновляется на heartbeat/progress;
- duplicate delivery не может войти, пока активный lease принадлежит другой доставке;
- housekeeping теперь восстанавливает expired lease вместо простого наблюдения;
- automatic replay работает только по явному allowlist;
- `document_ingest` — первый `safe_replay` workflow;
- `design_review` и остальные decision/side-effect workflows при потере lease переходят в `orphaned` и требуют подтверждения Engineering Admin;
- ручное восстановление требует точного `confirm=RECOVER_ORPHANED`;
- новый `compute_job_recovery_events` хранит recovery audit trail;
- Operations/Prometheus показывают orphaned jobs, expired leases и recovery events;
- API bounded contexts: **247 routes**, все **181/181** legacy v6.2 method/path contracts сохранены.

## Почему это важно для Engineering Digital Thread

Тяжёлые процессы — document ingestion/OCR, BOM extraction, CAD/3D, AI/translation, индексация — не должны зависеть от того, пережил ли конкретный worker рестарт Redis, контейнера или узла. Одновременно инфраструктура не должна сама создавать второе инженерное решение только потому, что потеряла heartbeat первого запуска.

v6.3.13 разделяет эти случаи: технически идемпотентная обработка может быть безопасно восстановлена, а decision-producing операция останавливается на human recovery gate.

## Новые административные API

- `POST /api/v1/operations/workload/{job_id}/recover?confirm=RECOVER_ORPHANED`
- `GET /api/v1/operations/workload/recovery-events`

## Новые настройки

```text
JOB_WORKER_LEASE_GRACE_SECONDS=120
JOB_AUTO_RECOVERY_ENABLED=true
JOB_AUTO_RECOVERY_MAX_PER_CYCLE=25
```

## Совместимость

- существующие Core/AI/Advanced профили сохранены;
- plain `docker compose build` сохранён;
- strict reproducible/offline build controls v6.3.12 сохранены и переведены на release metadata v6.3.13;
- legacy queue aliases `heavy/background/default` сохранены на transition period;
- новых автоматических PLM/PDM/ERP/MES/QMS write-back или production-equipment command paths нет.

## Verification

- backend regression: **442/442 PASS**;
- test files: **86/86 PASS**;
- Execution Recovery preflight: **35/35 PASS**;
- Workload Isolation: **29/29 PASS**;
- API contract: **181/181 legacy contracts preserved**, **247 current routes**;
- API authorization: **309 guarded human-facing routes**, 4 explicit system exceptions;
- architecture/security/governance/lifecycle/performance/cache gates remain green.

Полный verification scope и ограничения packaging environment указаны в `VERIFICATION_v6.3.13.md`.
