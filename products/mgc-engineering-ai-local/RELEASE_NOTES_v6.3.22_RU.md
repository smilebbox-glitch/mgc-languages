# MGC Engineering AI Local v6.3.22 — Release Notes (RU)

## Production Load Certification Harness

v6.3.22 превращает production-acceptance из проверки заранее подготовленных цифр в воспроизводимый измерительный процесс. Версия приложения — **6.3.22**, схема БД остаётся **6.3.13**, миграция не требуется.

### Что добавлено

- controlled concurrency профили **15 / 30 / 100**;
- минимальные объёмы измеряемых запросов и отдельный warm-up;
- автомобильный mixed workload: Object 360, BOM, Work Instructions, Digital Thread, RAG search и RAG ask;
- p50 / p95 / p99 / max latency и requests/sec;
- global/per-operation error rate и error-budget burn;
- сбор DB-pool saturation, queue depth, oldest-job age, DLQ/orphaned/expired-job indicators;
- явное подтверждение `MGC_LOAD_CERTIFY_CONFIRM=YES` перед live run;
- отдельный opt-in `MGC_LOAD_ALLOW_AUDITED_POSTS=YES` для RAG audited-read POST;
- ephemeral API key / bearer token через environment, без сохранения credentials в evidence;
- SHA-256 target/fixture fingerprints вместо raw project/part/target identifiers;
- canonical SHA-256 для evidence;
- detached OpenSSL signature;
- public-key verification непосредственно в `production_certify.py`;
- автоматический импорт измеренных p95/error-rate/DB-pool значений в v6.3.21 acceptance flow;
- unsigned evidence остаётся `CONDITIONAL`; tampered/invalid signature и обязательные SLO/saturation failures блокируют технический GO;
- даже технический `GO` не выставляет `production_authorized=true` автоматически.

### Default workload mix

- Object 360 — 25%;
- BOM versions — 20%;
- Work Instructions — 20%;
- Digital Thread — 15%;
- RAG search — 12%;
- RAG ask — 8%.

Default plan не выполняет инженерные domain writes. RAG POST используются только как audited reads и требуют отдельного подтверждения.

### Профили

- 15 инженеров: concurrency 15, минимум 1,000 measured requests, warm-up 50, p95 <= 500 ms, error <= 1.0%;
- 30 инженеров: concurrency 30, минимум 5,000 measured requests, warm-up 100, p95 <= 500 ms, error <= 1.0%;
- 100 инженеров: concurrency 100, минимум 10,000 measured requests, warm-up 200, p95 <= 750 ms, error <= 0.5%.

Это acceptance thresholds, а не заявление о фактической производительности конкретного сервера.

### Verification

- backend: **542/542 PASS**, 95/95 test-файлов;
- Production Load Certification: **24/24 PASS**;
- Production Certification: **22/22 PASS**;
- focused v6.3.21↔v6.3.22 compatibility: **47/47 PASS**;
- криптографический E2E: canonical load evidence → detached RSA/OpenSSL signature → public-key verification → technical `GO` — PASS;
- legacy API: **181/181 сохранены**;
- bounded-context routes: **247**, без новых automotive business routes.

### Ограничения

В packaging environment реальный target-host load test 15/30/100 не выполнялся. Не заявляются production throughput, production RTO/RPO, multi-host failover под нагрузкой, корпоративный CVE/image acceptance или Production GO. Supply-chain статус остаётся **CONDITIONAL**.

Подробности: `docs/PRODUCTION_LOAD_CERTIFICATION_v6.3.22.md` и `docs/VERIFICATION_v6.3.22.md`.
