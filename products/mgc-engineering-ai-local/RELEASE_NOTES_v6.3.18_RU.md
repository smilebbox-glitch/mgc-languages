# MGC Engineering AI Local v6.3.18
## High Availability & Failover Coordination

v6.3.18 — эксплуатационный hardening-релиз поверх v6.3.17. Automotive-domain поведение и схема БД не меняются: application **6.3.18**, schema **6.3.13**.

### Главное

- базовый single-instance Compose сохранён и остаётся режимом по умолчанию;
- добавлен опциональный `docker-compose.ha.yml`;
- HA overlay добавляет второй stable API, резервные worker-роли, второй Beat и второй frontend;
- API получил локальный readiness healthcheck;
- HA gateway балансирует два API/frontend upstream и выполняет bounded passive failover;
- blind retry non-idempotent HTTP-запросов намеренно не включён;
- candidate API не считается stable HA-репликой;
- draining API не считается активной HA-репликой;
- under-replication переводит Operations в `DEGRADED`, но не создаёт cascading readiness failure оставшегося API;
- два активных Beat-лидера считаются `UNSAFE` split-brain risk;
- PostgreSQL advisory lock остаётся authority для scheduler leadership;
- дублированные workers используют существующие late-ack/reject-on-worker-lost и PostgreSQL execution fencing;
- добавлен `GET /api/v1/operations/high-availability`;
- support bundle дополнен `high-availability.json`;
- добавлены HA Prometheus gauges;
- добавлены `make ha-preflight`, `make ha-up`, `MGC_HA_DRILL_CONFIRM=YES make ha-drill`;
- новых DB migrations нет.

### Проверка исходного пакета

- backend regression: **485/485 PASS**, **91/91 test-файлов**;
- v6.3.18 HA/Failover preflight: **41/41 PASS**;
- v6.3.17 Blue/Green gate: **40/40 PASS**;
- Rolling Upgrade gate: **37/37 PASS**;
- legacy API contract: **181/181 сохранены**;
- bounded-context API: **247 routes**;
- API authorization: **313 human-facing routes**, 4 explicit system exceptions;
- Docker static security: **38/38 PASS**;
- Compose/runtime security: **108/108 PASS**;
- Enterprise Security: **23/23 PASS**;
- Compose YAML parse: **17/17 PASS**;
- deterministic secret scan: **0 findings**;
- SBOM: **37 components**;
- BUILD_INPUTS: **61/61 verified**.

### Граница HA

Этот релиз предоставляет **application-tier redundancy**, а не полную инфраструктурную HA-сертификацию. PostgreSQL failover, физически shared evidence storage, внешний load balancer/entrypoint и multi-host/multi-zone orchestration остаются внешними корпоративными инфраструктурными требованиями.

### Ограничения packaging environment

В packaging environment отсутствует Docker CLI/daemon. Поэтому live `ha-failover-drill` здесь **не заявляется выполненным**. Реальная остановка API/worker/Beat и проверка failover обязательны на целевом корпоративном deployment host.

Supply-chain status остаётся **CONDITIONAL**: отсутствующие approved npm/Python/OS artifacts, immutable image digests и CVE/image scan evidence не фабрикуются. `production_authorized=false` остаётся отдельным human change-control gate.
