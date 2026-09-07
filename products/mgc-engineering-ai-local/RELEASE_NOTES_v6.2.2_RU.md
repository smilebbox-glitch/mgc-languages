# MGC Engineering AI Local v6.2.2
## Service Dependency Decomposition

v6.2.2 — patch-релиз архитектурного упрощения поверх v6.2.1. Новых automotive business-domain функций и миграции БД нет. Цель релиза — сделать runtime-профили `core / ai / advanced` реальными не только на уровне capability flags, но и на уровне Python imports и устанавливаемых dependency envelopes.

## Главное

- `context_shared.py` больше не импортирует service layer целиком при старте приложения;
- bounded-context handlers используют lazy service bindings: конкретный service module загружается только при фактическом вызове функции;
- `context_registry` импортирует только активные bounded contexts, а не все шесть заранее;
- Qdrant и Sentence Transformers в `vector_store.py` импортируются только когда semantic search действительно используется;
- Python dependencies разделены на `requirements-core.txt`, `requirements-ai.txt`, `requirements-advanced.txt`;
- Core image не включает `qdrant-client`, `sentence-transformers`, `neo4j` и `minio`;
- AI image = Core + Qdrant + embeddings/reranker dependencies;
- Advanced image = AI + Neo4j + MinIO clients;
- `docker compose build` автоматически передаёт текущий `DEPLOYMENT_PROFILE` в backend build;
- image сохраняет `MGC_BUILD_PROFILE`; runtime fail-closed отклоняет профиль, который шире dependency envelope образа;
- SBOM и dependency-lock tooling понимают layered requirements и не теряют зависимости из отчётности.

## Совместимость

- Application version: `6.2.2`;
- DB schema marker: `6.2.0`;
- legacy public API: 181/181 method+path contracts сохранены относительно v6.2.0;
- v6.2.1 handler AST contract сохранён — рефакторинг не меняет handler bodies;
- ACL/Identity/Capability Gate semantics не расширяются.

## Профили зависимостей

### Core

Deterministic platform: FastAPI/PostgreSQL/Redis, document parsing, deterministic CAD/document processing, audit, integrations, manufacturing/configuration functions и lexical/metadata fallback. Не требует Qdrant, sentence-transformers, Neo4j или MinIO Python clients для старта.

### AI

Core + Qdrant client + sentence-transformers. Semantic retrieval/model enrichment остаются optional runtime capabilities и не становятся authority source.

### Advanced

AI + Neo4j client + MinIO client для optional graph/object-store projections.

## Fail-closed build/runtime compatibility

Образ, собранный как Core, нельзя запустить с `DEPLOYMENT_PROFILE=ai` или `advanced` без rebuild. Приложение завершает startup с понятной ошибкой вместо частично работающего mixed-profile runtime.

## Deployment boundary

v6.2.2 не является Production GO. На корпоративном build/target host остаются обязательными реальные `docker compose build`, resolved wheelhouse/lock evidence, CVE/container scan, AD/OIDC и PKI negative tests, backup→restore, integration reconciliation, performance/load certification, controlled UAT и human change approval.
