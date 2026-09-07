# MGC Engineering AI Local v6.3.17
## Blue/Green Cutover & Automated Rollback Safety

v6.3.17 — технический эксплуатационный hardening-релиз поверх v6.3.16. Automotive-domain поведение и схема БД не меняются: application `6.3.17`, schema `6.3.13`.

### Главное

- обычный `docker compose up` сохраняет прежний stable topology;
- добавлен отдельный `docker-compose.bluegreen.yml` с внутренними `api-candidate` и `frontend-candidate` без host ports;
- gateway получает параметризуемые `API_UPSTREAM` / `FRONTEND_UPSTREAM`, но по умолчанию остаётся на canonical `api` / `frontend`;
- runtime heartbeat теперь содержит `deployment_slot=stable|candidate`;
- candidate должен пройти несколько последовательных readiness samples до traffic switch;
- после switch выполняется отдельное окно acceptance;
- корпоративный synthetic/SLO probe можно подключить через `CUTOVER_SLO_PROBE_CMD`;
- серия post-switch failures запускает guarded automatic rollback;
- rollback fail-closed при schema mismatch, major/minor skew, слишком большом patch-skew или попытке отката на более новую версию;
- для v6.3.17 сертифицирован rollback target v6.3.16 при общей schema 6.3.13;
- после rollback candidate остаётся изолированным для диагностики;
- finalization остаётся явной human-triggered операцией и повторно использует worker drain / singleton Beat / task-envelope fencing;
- добавлен Engineering Admin endpoint `GET /api/v1/operations/cutover-safety`;
- support bundle дополнен privacy-safe `cutover-safety.json`;
- новых DB migrations нет.

### Проверка исходного пакета

- backend regression: **473/473 PASS**, **90/90 test-файлов**;
- v6.3.17 Blue/Green preflight: **40/40 PASS**;
- v6.3.16 Rolling Upgrade gate: **37/37 PASS**;
- legacy API contract: **181/181 сохранены**;
- bounded-context API: **247 routes**;
- API authorization: **312 human-facing routes**, 4 explicit system exceptions;
- Docker static security: **38/38 PASS**;
- Compose/runtime security: **108/108 PASS**;
- Enterprise Security: **23/23 PASS**;
- Compose YAML parse: **16/16 PASS**;
- deterministic secret scan: **0 findings**;
- SBOM: **37 components**;
- BUILD_INPUTS: **57/57 verified**.

### Ограничения packaging environment

Docker CLI/daemon отсутствует, поэтому реальный live traffic cutover/rollback/finalize drill здесь не заявляется выполненным. Аналогично source package не заявляет corporate dependency/image CVE acceptance, immutable registry digest certification или Production GO. Эти проверки остаются обязательными на целевом корпоративном build/deployment host.
