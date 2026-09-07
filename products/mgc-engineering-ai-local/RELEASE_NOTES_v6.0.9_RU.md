# MGC Engineering AI Local v6.0.9 — Production Operations Acceptance & Game Days

## Назначение

v6.0.9 — девятый шаг production-hardening после Engineering Intelligence OS. Релиз не добавляет новый automotive-домен. Цель — превратить эксплуатационные требования в воспроизводимые failure-drills с измеряемыми RTO/MTTR/RPO, evidence и формальным Operations GO / CONDITIONAL_GO / NO_GO.

## Ключевая граница

MGC **не выполняет destructive fault injection**. Отключение PostgreSQL/Redis/Qdrant, остановка worker, тест истёкшего сертификата, OIDC failure и другие воздействия выполняются только авторизованным инфраструктурным оператором на approved non-production / controlled-pilot стенде. MGC хранит план, timestamps, evidence и результат acceptance.

Даже при `GO` ответ содержит:

```text
human_go_live_required = true
deployment_authorized = false
fault_injection_performed_by_application = false
```

## Обязательные game-day drills

1. `postgres_outage` — fail-closed readiness, recovery, schema/data verification, RTO/RPO.
2. `redis_outage` — queue/retry/idempotency recovery.
3. `qdrant_outage` — explicit search/AI degradation and recovery without changing authoritative facts.
4. `worker_crash_restart` — worker health, queue age, retry/idempotency.
5. `integration_outage` — freshness/data-confidence degradation and catch-up without duplicate ingest.
6. `expired_tls_certificate` — TLS fail-closed, alert, renewal/reload.
7. `oidc_failure` — issuer/JWKS/audience negative scenario and recovery.
8. `queue_overload` — queue-age/capacity behavior under approved synthetic load.
9. `backup_restore` — isolated restore, checksums, schema readiness and measured RTO/RPO.

## Evidence и метрики

Для каждого drill фиксируются:

- fault/start timestamp;
- detection timestamp;
- mitigation timestamp;
- recovered timestamp;
- verified timestamp;
- target/actual RTO;
- actual MTTR;
- target/actual RPO;
- runbook/evidence reference;
- final exercise status.

Метрики вычисляются детерминированно. AI score не используется.

## Decision policy

### Rehearsal

Может вернуть только:

- `PRECHECK_PASS`;
- `PRECHECK_FAIL`.

Rehearsal никогда не даёт production GO.

### Controlled

- missing/non-verified required drill → `NO_GO`;
- RPO target breach → `NO_GO`;
- critical RTO breach → `NO_GO`;
- open `CRITICAL` production incident → `NO_GO`;
- missing required external runtime gate → `NO_GO`;
- небольшой non-critical RTO miss → максимум `CONDITIONAL_GO`;
- open `HIGH` production incident → максимум `CONDITIONAL_GO`;
- все обязательные evidence gates PASS → `GO`.

## Внешние mandatory gates для Controlled GO

- Docker runtime acceptance;
- resolved CVE scan;
- approved dependency-lock resolution;
- OIDC negative tests;
- mTLS negative tests;
- monitoring/alert routing verification;
- Pilot performance profile.

## Operations API

Добавлены Engineering Admin endpoints:

```text
GET    /api/v1/operations/game-days
POST   /api/v1/operations/game-days
POST   /api/v1/operations/game-days/{run_id}/start
GET    /api/v1/operations/game-days/{run_id}
PATCH  /api/v1/operations/game-days/{run_id}/exercises/{exercise_code}
PATCH  /api/v1/operations/game-days/{run_id}/external-gates
GET    /api/v1/operations/game-days/{run_id}/evaluation
POST   /api/v1/operations/game-days/{run_id}/finalize?confirm=FINALIZE_OPERATIONS_ACCEPTANCE
```

Финализация сохраняет snapshot решения и администратора, но не разрешает production deployment.

## UI

`Production Support · v6.0.9` в IT/admin workspace теперь показывает также последнюю Operations Acceptance decision и coverage обязательных game-day drills. Детальные действия остаются в admin API/runbook, чтобы интерфейс не превращался в destructive infrastructure console.

## Runbooks

Добавлены:

- `docs/GAME_DAY_RUNBOOK.md`;
- `docs/OPERATIONS_ACCEPTANCE.md`.

## Local verification

Финальные локальные результаты зафиксированы в `VERIFICATION_v6.0.9.md`. Реальные fault-injection drills, Docker runtime, CVE/Dockle, AD/OIDC/PKI и backup→restore на target-host остаются корпоративными runtime gates.
