# MGC Engineering AI Local v6.3.16
## Rolling Upgrade & Deployment Safety

v6.3.16 — технический hardening-релиз поверх v6.3.15 без изменения automotive-domain модели и без миграции БД. Цель — сделать обновление API/worker/scheduler безопасным для длинных инженерных задач и исключить молчаливое выполнение задач несовместимыми runtime-версиями.

## Главное

- application version: **6.3.16**;
- database schema: **6.3.13** — новая migration не требуется;
- каждое новое Celery-сообщение получает `mgc_app_version`, `mgc_schema_version`, `mgc_deployment_profile`;
- worker проверяет runtime envelope **до task body / side effect**;
- допустимое rolling-window правило по умолчанию: одинаковые major/minor + одинаковая schema + patch skew не более 1;
- переход `6.3.15 ↔ 6.3.16` при schema `6.3.13` разрешён;
- более старый `6.3.14 ↔ 6.3.16` или schema mismatch блокируется fail-closed;
- legacy сообщения без envelope временно принимаются только через явный transition flag `ROLLING_UPGRADE_ALLOW_LEGACY_TASK_ENVELOPES=true`;
- workers получили role-prefixed identities (`interactive@`, `cpu@`, `io@`, `cad@`, `ai@`);
- drain-команда прекращает приём новых задач и ждёт завершения active work перед recreate;
- worker Docker stop grace period — 10 минут по умолчанию;
- Celery Beat запускается через singleton guard с PostgreSQL advisory lock;
- потеря DB session, которая держит scheduler lock, немедленно завершает Beat fail-closed;
- API/worker/beat публикуют privacy-safe ephemeral heartbeat в Redis;
- известный несовместимый component version/schema блокирует `/health/ready`;
- недоступность самого Redis component registry **не** блокирует deterministic Core;
- добавлен Engineering Admin endpoint `GET /api/v1/operations/deployment-safety`;
- deployment safety добавлен в Operations status, Prometheus и support bundle;
- добавлены `make rolling-upgrade-preflight` и `make rolling-upgrade`;
- rollout order: **workers → singleton Beat → API → frontend/gateway**;
- обычный `docker compose build` по-прежнему поддерживается;
- production authorization остаётся отдельным human/corporate gate.

## Почему порядок обновления именно такой

v6.3.15 producer ещё не добавляет version envelope. Новый v6.3.16 worker умеет временно принимать такое legacy сообщение. Поэтому сначала безопасно обновляется worker fleet, и только после этого новый v6.3.16 API начинает публиковать versioned tasks. Обратный порядок мог бы позволить новому API отправить versioned работу старому worker-у, который ещё не умеет enforcing compatibility contract.

## Worker drain

Пример внутри worker container:

```bash
python -m app.workers.drain_cli --prefix cpu@ --timeout 600
```

Drain отменяет consumers на этом worker-е и ждёт `active=0`. Если timeout исчерпан, normal rolling script завершается ошибкой вместо SIGKILL.

## Scheduler safety

`beat` теперь запускается как:

```text
python -m app.workers.singleton_beat
```

PostgreSQL session-level advisory lock доказывает единственность активного scheduler-а. Standby Beat не публикует periodic tasks. Если lock-owning DB session теряется, leader завершается и должен заново получить lock после restart.

## Запуск controlled rollout

После подготовки/импорта target images:

```bash
make rolling-upgrade-preflight
make rolling-upgrade
```

Source script не заявляет zero-downtime single-node Compose deployment и не подменяет корпоративный orchestrator/change approval.

## Проверено в packaging environment

- backend regression: **463/463 PASS**;
- test files: **89/89**;
- Rolling Upgrade & Deployment Safety preflight: **37/37 PASS**;
- API bounded-context routes: **247**;
- legacy v6.2 API contracts: **181/181 preserved**;
- human-facing API authorization: **311 guarded routes**, 4 explicit system exceptions;
- Docker static security: **38/38 PASS**;
- Compose/runtime security: **108/108 PASS**;
- Enterprise Security: **23/23 PASS**;
- Compose YAML parse: **15/15 PASS**;
- source secret scan: **0 findings**.

## Ограничения

Релиз не заявляет completed corporate Production GO. На целевом build/deployment host всё ещё обязательны approved dependency artifacts, real Docker/BuildKit image build, CVE/SCA/image scans, OIDC/PKI negative tests, representative workload certification и реальная rehearsal процедуры rolling upgrade/rollback.
