# MGC Engineering AI Local v6.3.2
## Transaction & Projection Reliability

v6.3.2 — технический reliability-релиз поверх v6.3.1/v6.3.0. Новых пользовательских business-domain разделов не добавляется. Релиз закрывает риск частично выполненной операции, когда PostgreSQL уже сохранил инженерное состояние, а Qdrant/Neo4j/MinIO обновились не полностью или были недоступны.

## Главное

- PostgreSQL закреплён как единая transaction boundary для engineering state + projection requests;
- добавлен transactional outbox `projection_outbox_events`;
- добавлен idempotent delivery ledger `projection_delivery_receipts`;
- добавлен PostgreSQL-authoritative источник semantic projection `document_search_chunks`;
- Qdrant/Neo4j/MinIO удалены из критической транзакции document ingest;
- projection worker работает через Celery background queue и Celery Beat;
- PostgreSQL claim использует `FOR UPDATE SKIP LOCKED`;
- worker lease возвращает зависшие `processing` события в retry;
- exponential retry + конечный retry budget + dead-letter queue;
- ручной DLQ replay только через Engineering Admin;
- stale projection event получает `superseded`, если authoritative document уже изменился;
- Qdrant point IDs стали deterministic UUIDv5;
- Neo4j projection стала replacement/convergent для MGC-owned HAS_DOCUMENT/CONTAINS edges;
- legacy documents до v6.3.2 backfill'ятся перед rebuild из authoritative evidence/metadata;
- Core lexical search теперь читает PostgreSQL chunks, сохраняя metadata fallback для legacy records;
- projection backlog/DLQ/lag добавлены в Prometheus, Operations Summary, readiness diagnostics и support bundle;
- projection degradation не является Core readiness gate.

## Delivery semantics

v6.3.2 сознательно не заявляет невозможное network-level exactly-once. Реальная гарантия:

`at-least-once delivery + idempotent consumers + unique idempotency key + delivery receipt = effectively-once logical projection processing`.

## Новая schema

Application version: `6.3.2`

Schema version: `6.3.2`

Новые additive tables:

- `document_search_chunks`;
- `projection_outbox_events`;
- `projection_delivery_receipts`.

Существующие Work Instructions, layouts, BOM translation и остальные v6.3.0 сущности не переписываются.

## Operations API

```text
GET  /api/v1/operations/projections
GET  /api/v1/operations/projections/outbox
POST /api/v1/operations/projections/process
POST /api/v1/operations/projections/rebuild
POST /api/v1/operations/projections/dlq/{event_id}/replay
```

Все пять endpoint требуют существующий Engineering Admin authorization.

## Compatibility

- все 181 legacy v6.2.0 method/path сохранены;
- все 12 additive v6.3.0 bounded-context routes сохранены;
- Work Instructions/BOM translation/layout/station workflows v6.3.0 сохранены;
- Ports & Adapters v6.3.1 сохранены;
- новый reliability API additive и не меняет существующие URL;
- Project / Manufacturing Area / Document ACL остаются сильнее runtime profile и projections.

## Corporate build-host gates

До production GO по-прежнему обязательны реальный `docker compose build`, resolved dependency lock/wheelhouse, container CVE scan, image hardening scan, PostgreSQL migration/rollback rehearsal, backup→restore, OIDC/TLS negative tests, representative projection-failure Game Day и human UAT/Operations approval.
