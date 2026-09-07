# MGC Engineering AI Local v6.3.11
## Background Jobs, Scheduler & Workload Isolation

v6.3.11 — технический reliability/performance-релиз поверх v6.3.10. Новых automotive business-domain функций не добавляет. Цель — изолировать тяжёлые CAD/OCR/ingestion/AI/rebuild задачи от интерактивного API и не позволять одному проекту монополизировать compute capacity.

## Главное
- шесть resource classes: `interactive`, `cpu`, `io`, `cad`, `ai`, `maintenance`;
- отдельные worker pools в Compose; AI worker только для `ai/advanced` profiles;
- PostgreSQL `ComputeJob` стал authoritative job ledger: project/area, priority, progress, cancellation, retry budget, timeout, heartbeat и DLQ;
- per-project concurrency: default 2, CAD 1, AI 1;
- PostgreSQL advisory-lock admission для конкурентных project/resource jobs;
- cooperative cancellation без SIGKILL внутри инженерной операции;
- bounded exponential retry + dead-letter + explicit Engineering Admin replay;
- async document ingestion и async design review переведены на managed jobs;
- Beat housekeeping отслеживает overdue heartbeat, но не делает опасный automatic duplicate dispatch;
- Operations/Prometheus/Support Bundle получили workload/DLQ telemetry;
- legacy queue labels `heavy/default/background` агрегируются в новый monitoring для безопасного перехода.

## API
Добавлены additive endpoints:
- `GET /api/v1/compute/tasks`
- `POST /api/v1/compute/tasks/{job_id}/cancel`
- `GET /api/v1/operations/workload`
- `POST /api/v1/operations/workload/{job_id}/retry`

Имеющийся `GET /api/v1/compute/tasks/{job_id}` сохранён и расширен progress/resource metadata.

## Versions
- Application: `6.3.11`
- Schema: `6.3.11`
- bounded-context routes: 245
- legacy v6.2.0 routes preserved: 181/181
