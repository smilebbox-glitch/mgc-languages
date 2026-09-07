# MGC Engineering AI Local v6.3.15
## Operational Resilience & Self-Diagnostics

v6.3.15 — технический hardening-релиз поверх v6.3.14. Цель — не допускать, чтобы отказ Redis, Qdrant, локального AI/VLM или CAD gateway превращал локальную проблему enrichment/фоновой обработки в недоступность всего Engineering Digital Thread.

## Граница релиза

- application version: **6.3.15**;
- database schema: **6.3.13** — миграция БД не требуется;
- PostgreSQL и authoritative evidence storage остаются источниками инженерной истины;
- automotive business rules, approval/release authority и инженерные решения не расширены;
- отдельного инженерного UI-модуля не добавлено: resilience остаётся Platform/Operations функцией.

## Что добавлено

- process-local circuit breakers со состояниями `closed/open/half_open` и bounded failure threshold/cooldown;
- brownout-mode для optional runtime dependencies;
- Qdrant failure → автоматический fallback на PostgreSQL lexical search;
- Qdrant indexing failure больше не блокирует authoritative document ingestion;
- LLM failure → evidence-only RAG без выдуманного AI-синтеза;
- VLM failure → deterministic drawing analysis остаётся доступным;
- native CAD gateway failure ограничивается conversion capability и не выключает документы/BOM/WI/Digital Thread;
- Redis/Celery publish защищён breaker-ом; managed job ledger остаётся в PostgreSQL;
- новая административная диагностика `GET /api/v1/operations/resilience`;
- resilience snapshot добавлен в readiness, Operations summary и privacy-safe support bundle;
- Prometheus-метрики circuit state, consecutive failures, trips и brownout;
- default v6.3.15 readiness отделяет Core availability от optional dependency health;
- корпоративный strict режим может вернуть fail-closed dependency readiness через `RESILIENCE_STRICT_DEPENDENCY_READINESS=true`.

## Почему это важно

Инженер не должен терять доступ к BOM, рабочей инструкции, change history или подтверждающим документам только потому, что временно недоступны векторный поиск, LLM или CAD-converter. v6.3.15 вводит controlled degradation: система явно показывает AMBER/BROWNOUT, отключает только повреждённую capability и сохраняет deterministic engineering core.

## Verification

- backend regression: **453/453 PASS**;
- test files: **88/88 PASS**;
- new v6.3.15 resilience unit tests: **6/6 PASS**;
- Operational Resilience preflight: **23/23 PASS**;
- Data Consistency & DR: **45/45 PASS**;
- Architecture Simplification: **27/27 PASS**;
- Dependency Profiles: **18/18 PASS**;
- Ports & Adapters: **25/25 PASS**;
- Projection Reliability: **26/26 PASS**;
- Domain Integrity: **25/25 PASS**;
- Revision & Conflict: **28/28 PASS**;
- Approval & Release Governance: **28/28 PASS**;
- Enterprise Identity: **38/38 PASS**;
- Release Handover Safety: **46/46 PASS**;
- Data Lifecycle: **33/33 PASS**;
- Performance & Scale: **18/18 PASS**;
- Read Models & Cache: **22/22 PASS**;
- Workload Isolation: **29/29 PASS**;
- Execution Recovery & Job Lease Safety: **35/35 PASS**;
- bounded-context ownership: **21/21 PASS**, **247 routes**;
- legacy API method/path contract: **181/181 preserved**;
- API authorization: **310 guarded human-facing routes**, 4 explicit system exceptions;
- Docker static security: **38/38 PASS**;
- Compose/runtime security: **108/108 PASS**;
- Enterprise Security: **23/23 PASS**;
- Observability: **16/16 PASS**;
- Corporate Deployment: **13/13 PASS**;
- Game Day: **15/15 PASS**;
- UX: **9/9 PASS**;
- Python compileall / shell syntax / Compose YAML: **PASS**;
- deterministic source secret scan: **0 findings**.

## Ограничения packaging environment

Source package остаётся **CONDITIONAL**, не Production GO. Здесь не выполнялись real Docker BuildKit build, corporate CVE/SCA/image acceptance, live Redis/Qdrant/AI/CAD fault-injection under representative concurrent load, target PostgreSQL backup→restore/PITR drill, live OIDC/PKI/mTLS negative tests или production reconciliation с PLM/PDM/ERP/MES/QMS. Brownout/circuit behavior должен быть дополнительно сертифицирован на целевой инфраструктуре компании.
