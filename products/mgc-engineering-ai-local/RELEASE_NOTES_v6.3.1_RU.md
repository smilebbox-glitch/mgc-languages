# MGC Engineering AI Local v6.3.1
## Ports & Adapters + Manufacturing Intelligence Hardening

v6.3.1 — технический patch-релиз поверх v6.3.0. Новых пользовательских разделов не добавляет. Цель релиза — убрать остаточную зависимость application-логики от конкретной инфраструктуры и усилить управляемость нового контура BOM translation / Work Instructions / layouts / station intelligence.

## Главное

- введены technology-neutral порты: `SearchPort`, `GraphProjectionPort`, `ObjectStoragePort`, `AIAnalysisPort`, `TranslationProviderPort`;
- конкретные Qdrant/Neo4j/MinIO/OpenAI-compatible реализации перенесены за adapter boundary;
- `ingest`, global RAG, BOM/WI translation и WI-RAG работают через dependency injection;
- Core использует deterministic lexical/no-op adapters и не требует импорта advanced client packages;
- runtime contract показывает фактически выбранные adapters;
- HTTP Intelligence/Search surface больше не знает конкретные vector/graph implementation modules;
- optional dependency health probes также вынесены за infrastructure adapter boundary.

## Work Instruction governance

- Approved Work Instruction revision теперь immutable: содержимое нельзя менять в той же ревизии;
- разрешён lifecycle-переход Approved → Obsolete;
- изменения требуют создания новой ревизии;
- перевод иностранной WI привязан SHA-256 fingerprint к исходному тексту и шагам;
- изменение source/steps переводит ранее проверенный перевод в `stale`;
- stale translation блокирует human approval до повторного перевода и review;
- AI/translation provider не получает полномочий approval.

## Совместимость

- Application version: `6.3.1`;
- Database schema marker: `6.3.0`;
- миграция БД не требуется;
- все 193 method/path API v6.3.0 сохранены;
- все 181 legacy API v6.2.0 также сохранены.

## Проверка

- полный backend test inventory: 348/348 PASS при sharded execution;
- Ports & Adapters preflight: 25/25 PASS;
- architecture: 27/27 PASS;
- dependency profiles: 18/18 PASS;
- context ownership: 21/21 PASS;
- API compatibility: 5/5 PASS;
- Docker static security: 38/38 PASS;
- Compose/access/runtime security: 100/100 PASS;
- Enterprise Security: 23/23 PASS;
- Corporate Deployment: 13/13 PASS;
- Observability: 16/16 PASS;
- Game Day: 15/15 PASS;
- UX: 9/9 PASS;
- API authorization: 248 guarded human-facing routes; 4 explicit exceptions;
- source secret scan: 0 findings;
- frontend TSX transpile: PASS;
- build preflight: PASS.
- build manifest: 573/573 PASS;
- ZIP integrity: PASS.

Реальный Docker build, resolved dependency lock/SBOM, CVE/image scan, OIDC/TLS negative tests, PostgreSQL migration/backup-restore rehearsal и corporate UAT остаются target-host gates и не заменяются packaging verification.
