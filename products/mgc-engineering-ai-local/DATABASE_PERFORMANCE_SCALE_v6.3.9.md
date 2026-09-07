# MGC Engineering AI Local v6.3.9 — Database Performance & Scale Hardening

## Scope
v6.3.9 hardens the existing modular-monolith platform for larger controlled engineering teams without introducing microservices or changing PLM/MES authority. PostgreSQL remains the source of truth; Qdrant/Neo4j remain rebuildable projections.

## Database pool governance
For PostgreSQL, SQLAlchemy now uses bounded pool configuration:
- `DB_POOL_SIZE` (default 15)
- `DB_MAX_OVERFLOW` (default 15)
- `DB_POOL_TIMEOUT_SECONDS` (default 30)
- `DB_POOL_RECYCLE_SECONDS` (default 1800)

SQLite/dev retains its native pool behavior.

## Privacy-safe query telemetry
The SQLAlchemy engine records:
- query latency histogram;
- sanitized SQL operation + table only;
- slow-query count above `DB_SLOW_QUERY_MS`;
- statement count and DB time per HTTP request;
- connection-pool saturation.

Raw SQL text and bind values are not retained in performance telemetry.

## Query/N+1 budget
Default request budget:
- 40 SQL statements;
- 500 ms cumulative DB time.

Budget violations produce metrics/warnings. Hard enforcement is controlled by `DB_QUERY_BUDGET_ENFORCEMENT_ENABLED` and is **false by default**. It should only be enabled after representative PostgreSQL load testing.

## Composite indexes
v6.3.9 adds idempotent indexes for dominant access paths including:
- project/area/document keyset browsing;
- part/revision/document lookup;
- BOM parent/revision/child traversal;
- WI project/area/station/status;
- manufacturing line/station/operation ordering;
- engineering change status/priority;
- workflow status/due date;
- projection outbox claiming;
- handover/purge operational queues;
- audit keyset pagination;
- document search chunk ordering.

No engineering rows are rewritten by this migration.

## Cursor pagination
Legacy `GET /audit` is unchanged. New admin endpoint `GET /audit/cursor` uses keyset pagination over `(created_at, id)` and returns an opaque cursor. This avoids high OFFSET cost for large audit tables.

## Bulk ingestion
BOM CSV ingestion and authoritative search-chunk persistence now use bounded bulk INSERT batches. `BULK_INGEST_BATCH_SIZE` defaults to 500 and is capped internally at 5000.

## Scale reference profiles
These are benchmark targets, not production capacity guarantees:

| Profile | Named engineers | Target concurrent | Pool reference | Purpose |
|---|---:|---:|---:|---|
| `pilot_15` | 15 | 5 | 10 + 10 overflow | small controlled pilot |
| `pilot_30` | 30 | 10 | 15 + 15 overflow | department pilot |
| `enterprise_100` | 100 | 30 | 30 + 30 overflow | enterprise reference; mandatory target-host certification |

A real production claim requires representative dataset/load testing on the target PostgreSQL/Redis/Qdrant host.

## Operations
Engineering Admin endpoint `GET /operations/performance` exposes only aggregate performance posture, scale reference and pool state. Operations Summary/Support Bundle include the same sanitized performance block. Pool saturation >=90% marks operations AMBER but does not turn Core source-of-truth readiness RED.
