# MGC Engineering AI Local v6.3.14
## Data Consistency & Disaster Recovery

v6.3.14 — технический hardening-релиз поверх v6.3.13. Цель — не допустить ситуации, когда backup выглядит успешным, но PostgreSQL, evidence storage и Digital Thread относятся к разным состояниям, а также не позволять restore открыть инженерам систему только потому, что контейнеры снова отвечают на health-check.

## Граница релиза

- application version: **6.3.14**;
- database schema: **6.3.13** — миграция БД не требуется;
- automotive business behavior и инженерные approval/release rules не расширены;
- пользовательский интерфейс инженера не усложняется: DR остаётся Platform/Operations обязанностью.

## Что добавлено

- maintenance-grade consistency scanner для PostgreSQL + authoritative evidence storage + Digital Thread references;
- deterministic logical SHA-256 по ORM-таблицам и PostgreSQL sequence state;
- полная SHA-256 проверка evidence tree с повторным использованием file-hash cache для больших CAD/3D/PDF;
- проверка `Document.sha256`, размера, существования и запрет path escape/symlink в authoritative storage;
- проверка ссылок на документы, включая JSON-списки;
- проверка tamper-evident `DocumentActivity` и `ChangeEvent` chains;
- `BACKUP_MANIFEST.json` v2 с consistency epoch, DB/storage fingerprints и quiesce evidence;
- backup по умолчанию закрывает gateway/beat, дожидается безопасной границы managed jobs и останавливает **все** worker-классы: interactive, CPU, IO, CAD и AI;
- restore сначала восстанавливает PostgreSQL/evidence, затем выполняет exact consistency comparison и только после PASS открывает API/workers/gateway;
- mismatch оставляет систему в maintenance-state — fail-closed;
- legacy v1/unquiesced recovery требует отдельного явного acceptance;
- optional `docker-compose.pitr.yml` для PostgreSQL WAL archiving и PITR readiness;
- recovery evidence фиксирует текущий WAL LSN, но не раскрывает значение `archive_command`;
- supply-chain BUILD_INPUTS переведён на текущую версию и включает DR/PITR control files.

## Почему это важно

В Engineering Digital Thread исходный документ, BOM, рабочая инструкция, change history и evidence должны восстанавливаться как согласованный набор. Потеря одного файла или восстановление БД на другой момент времени не должна тихо превращаться в «зелёный» сервис. v6.3.14 делает восстановленное инженерное состояние самостоятельным проверяемым артефактом, а не выводом из доступности контейнеров.

## Verification

- backend regression: **447/447 PASS**;
- test files: **87/87 PASS**;
- Data Consistency & DR: **45/45 PASS**;
- new v6.3.14 unit tests: **5/5 PASS**;
- bounded-context ownership: **21/21 PASS**, **247 routes**;
- legacy API method/path contract: **181/181 preserved**;
- API authorization: **309 guarded human-facing routes**, 4 explicit system exceptions;
- Docker static security: **38/38 PASS**;
- Compose/runtime security: **108/108 PASS**;
- Enterprise Security: **23/23 PASS**;
- Observability: **16/16 PASS**;
- Corporate Deployment: **13/13 PASS**;
- Game Day: **15/15 PASS**;
- UX: **9/9 PASS**;
- build preflight: **PASS**;
- Python compileall / shell syntax / Compose YAML: **PASS**;
- deterministic source secret scan: **0 findings**.

## Ограничения packaging environment

Source package остаётся **CONDITIONAL**, не Production GO. Здесь не выполнялись реальный Docker BuildKit build, корпоративный CVE/SCA/image scan, target PostgreSQL backup→restore drill, WAL retention/PITR drill, измерение RPO/RTO, live OIDC/PKI/mTLS negative tests или production reconciliation с PLM/PDM/ERP/MES/QMS. Эти доказательства должны быть получены на корпоративном target host.
