# MGC Engineering AI Local v6.3.10 — Cache, Read Models & Object 360 Performance

## Design boundary

PostgreSQL engineering-domain records and authoritative evidence remain the source of truth. `engineering_read_models` contains only rebuildable derived aggregates. Redis is optional acceleration and is never required for correctness, disaster recovery or release evidence.

## Surfaces

- **Work Instruction coverage read model**: precomputed counts and station coverage per Project + Manufacturing Area. It intentionally excludes WI text, document content, protected BOM values and other user-visible evidence.
- **Object 360 acceleration**: optional Redis full-payload cache keyed by runtime profile + object identity + ACL fingerprint.
- **Project Workspace / WI Workspace acceleration**: optional Redis cache keyed by ACL fingerprint and project/area scope.
- **Conditional GET**: Object 360, Project Workspace and WI Workspace return private ETags and honor `If-None-Match`.

## Invalidation

Business changes create `read_model_invalidate` events in the existing transactional Projection Outbox. Document ingestion also emits an invalidation event. The worker marks matching PostgreSQL read models stale and evicts `mgc:v6310:*` Redis entries.

Read paths fail closed against stale acceleration: while a read-model invalidation event is pending/retrying/processing, shared cache is bypassed and the response is rebuilt from authoritative PostgreSQL/evidence data.

## Operations

`GET /api/v1/operations/read-models` reports fresh/stale counts, pending invalidations and model metadata.

`POST /api/v1/operations/read-models/rebuild` rebuilds supported derived models and clears acceleration cache. It does not mutate authoritative engineering data.

## Failure semantics

- Redis outage → cache miss; request still executes from PostgreSQL.
- Lost/slow worker → pending invalidation forces cache bypass.
- Read-model table deleted → read model is rebuilt on demand.
- Qdrant/Neo4j state is unrelated to read-model correctness and remains rebuildable projection state.

## Security

Full-payload cache keys include an ACL fingerprint derived from visible document IDs and groups. Read-model persistence stores only safe aggregates and hashes; no WI text or raw document content is persisted there.
