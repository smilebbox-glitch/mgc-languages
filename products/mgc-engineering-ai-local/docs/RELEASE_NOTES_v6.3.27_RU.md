# MGC Engineering AI Local v6.3.27 — Real Integration Certification

## Основное

v6.3.27 превращает существующие `plm_rest / pdm_rest / erp_rest / mes_rest / qms_rest` из просто коннекторов в формально проверяемые корпоративные integration contracts.

### Добавлено

- vendor-neutral profiles для PLM/PDM/ERP/MES/QMS;
- reference contracts `ops/integrations/contracts/*.example.json`;
- static adapter certification;
- bounded read-only live certification;
- deterministic repeated-read check;
- stable external-ID validation;
- schema/required-field validation;
- replay/idempotency-key validation;
- source/fingerprint checkpoint validation;
- явный запрет source-system writeback;
- HTTPS fail-closed для production REST gateway;
- credentials только через `*_env` references;
- `ACTIVE / DEGRADED_READ_ONLY / BLOCKED` runtime posture;
- опциональный fail-closed sync guard при degraded integration;
- Engineering Admin endpoints `certify` и `runtime-posture`;
- `mgcctl certify integration`;
- integration contract suite и v6.3.27 preflight;
- privacy-safe certification evidence с SHA-256 вместо raw external IDs.

### Сохранено

- существующий ingest/quarantine/replay;
- immutable external object history;
- EBOM/MBOM reconciliation;
- MES genealogy reconciliation;
- QMS linkage;
- human-confirmed mapping registry;
- запрет автоматического выбора source-of-truth winner;
- 247 bounded-context automotive routes;
- 181/181 legacy API contracts.

### Версии

- Application: **6.3.27**
- DB schema: **6.3.13**
- Новая DB migration: **нет**
- Rolling/Blue-Green adjacent window: **6.3.26 ↔ 6.3.27**

### Ограничение

Локальный simulator E2E подтверждает механизм certification, но не заменяет target-host проверку реальных Teamcenter/Windchill/3DEXPERIENCE/SAP/MES/QMS gateway. Production authorization остаётся человеческим решением.

## Верификация

- Backend: **620/620 PASS**, **100/100 test-файлов**.
- Integration Certification preflight: **49/49 PASS**.
- Reference contracts: **5/5 PASS**.
- Local live simulator E2E: **PASS**.
- API authorization: **319 guarded + 5 exceptions**.
- Supply-chain BUILD_INPUTS: **120/120 verified**, source package status `CONDITIONAL`.

## Упаковка

- Clean payload: **986 файлов**.
- ZIP: **987 members** с `BUILD_MANIFEST.json`.
- Первый independent ZIP→manifest pass: missing/extra/size/hash mismatch = **0**, `unzip -t` PASS.
