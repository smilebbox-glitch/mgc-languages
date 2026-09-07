# MGC Engineering AI Local v6.3.21 — Production Topology Certification & SLO Enforcement

## Что изменилось

v6.3.21 превращает topology reference для 15/30/100 инженеров из v6.3.20 в проверяемый production-acceptance contract.

- профили `15`, `30`, `100` теперь задают минимальную failure-domain redundancy, SLO availability, HTTP p95/error-rate, DB-pool headroom и RTO/RPO;
- добавлен Engineering Admin endpoint `/api/v1/operations/production-certification`;
- runtime report учитывает topology, authoritative DB/evidence fencing, DB-pool saturation, dependency health samples и critical incidents;
- отсутствие измерений даёт `CONDITIONAL`, нарушение обязательного gate — `NO_GO`;
- SLO violation не выбивает уже работающий API из external LB, а блокирует новый rollout/GO;
- добавлен DB-pool admission control: при критической saturation новые mutating HTTP requests получают 503 `DB_POOL_SATURATED`; read traffic остаётся доступным;
- добавлен target-host certification CLI и fail-closed deployment guard;
- даже технический `GO` никогда не выставляет `production_authorized=true` автоматически;
- support bundle содержит `production-certification.json`;
- схема БД остаётся 6.3.13, миграция не требуется.

## Проверка

Финальный post-hardening backend regression: **529/529 PASS**, **94/94 test-файла**, failures/errors/skips — 0.

Новый Production Certification preflight: **18/18 PASS**.

Сохранены все прежние ключевые gates: Architecture 27/27, Dependency Profiles 18/18, Ports & Adapters 25/25, Projection 26/26, Domain Integrity 25/25, Revision 28/28, Governance 28/28, Enterprise Identity 38/38, Handover 46/46, Lifecycle 33/33, Performance 18/18, Cache 22/22, Workload 29/29, Job Recovery 35/35, DR 45/45, Resilience 23/23, Rolling 37/37, Blue/Green 40/40, Application HA 41/41, DB/Evidence HA 45/45, Multi-host 30/30 и bounded contexts 21/21.

API: 247 bounded-context routes, 181/181 legacy contracts сохранены. Access preflight: 316 human-facing routes защищены `get_identity`, 5 system exceptions.

Security: Docker 38/38, Compose/runtime 119/119, Enterprise Security 23/23, Observability 16/16, Corporate Deployment 13/13, Game Day 15/15, UX 9/9, secret scan 0 findings, 19/19 Compose YAML PASS.

## Supply chain

SBOM: 37 компонентов. `BUILD_INPUTS.json` отслеживает 83 file inputs и 14 image refs; 76 file inputs присутствуют и хешированы, 7 корпоративных lock/wheelhouse artifacts отсутствуют по design. Поэтому supply-chain status остаётся `CONDITIONAL`, `production_authorized=false`.

## Что ещё требуется на целевом сервере

Для реального production acceptance необходимо заменить example evidence фактическими результатами:

- live HTTP/load test профиля 15/30/100;
- external-LB host-loss drill без non-idempotent replay;
- PostgreSQL failover/ST​ONITH drill;
- evidence-storage failover/integrity verification;
- измеренные RTO/RPO;
- DBA review connection-pool capacity;
- человеческое изменение/GO approval.

Packaging environment не считается production target и не может выдать Production GO.
