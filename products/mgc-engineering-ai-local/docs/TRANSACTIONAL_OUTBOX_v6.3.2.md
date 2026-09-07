# MGC Engineering AI Local v6.3.2 — Transactional Outbox & Projection Reliability

## 1. Purpose

v6.3.2 makes PostgreSQL the explicit transaction boundary for authoritative engineering state and all requests to update rebuildable projections. Qdrant, Neo4j and MinIO are not participants in a distributed transaction and are never allowed to decide whether an engineering record can be committed.

The reliability model is:

```text
Engineering write / document ingest
            |
            v
+-----------------------------------+
| PostgreSQL transaction            |
| - engineering state               |
| - document_search_chunks          |
| - projection_outbox_events        |
+-----------------------------------+
            |
          COMMIT
            |
            v
Celery projection dispatcher
   |          |          |
   v          v          v
 Qdrant     Neo4j      MinIO
   |          |          |
   +------ idempotent consumers ----+
            |
            v
projection_delivery_receipts
```

There is deliberately no XA/2PC transaction across PostgreSQL and the derived stores.

## 2. Authoritative projection source

`document_search_chunks` stores the deterministic chunks produced during ingest in PostgreSQL. These rows are the source used to rebuild the semantic index. This changes the disaster-recovery property from “Qdrant snapshot preferred” to “Qdrant can be deleted and reconstructed from PostgreSQL + evidence storage”.

Legacy documents created before v6.3.2 are backfilled during a controlled rebuild. The service first attempts to reparse the local evidence file. If the rich parser is unavailable, it persists a clearly marked metadata-based fallback rather than claiming full text extraction.

## 3. Outbox event state machine

```text
pending
  |
  v
processing ---- worker lease expires ----> retry
  |                                    ^
  | success                            |
  v                                    |
succeeded                         exponential backoff
  |
  +--> delivery receipt

processing -- repeated failure --> dead_letter
processing -- newer source ------> superseded
```

Important properties:

- one `idempotency_key` per logical projection operation;
- PostgreSQL unique constraint prevents duplicate logical enqueue;
- worker claims use `FOR UPDATE SKIP LOCKED` on PostgreSQL;
- a bounded worker lease recovers abandoned `processing` rows;
- exponential retry with a maximum delay;
- finite retry budget and explicit dead-letter queue;
- administrator-controlled DLQ replay;
- stale events never overwrite a newer authoritative document state;
- manual rebuild uses a unique rebuild generation while preserving the current authoritative source fingerprint.

## 4. Delivery semantics

The transport guarantee is **at-least-once delivery**. Logical processing is **effectively once per idempotency key** through delivery receipts plus idempotent adapter behavior.

This wording is intentional. A network process can always fail after a remote side effect succeeds but before PostgreSQL records the receipt. Therefore v6.3.2 does not make an incorrect literal “exactly once over the network” claim.

The adapters converge safely under retries:

- **Qdrant** — delete-and-replace document projection plus deterministic UUIDv5 point IDs;
- **Neo4j** — replacement of MGC-owned `HAS_DOCUMENT` / `CONTAINS` edges followed by `MERGE`;
- **MinIO** — stable object key `documents/{document_id}/{filename}`.

## 5. Unit-of-Work boundary

Document ingest no longer performs Qdrant/Neo4j/MinIO I/O before the authoritative commit.

The successful ingest transaction contains:

1. parsed/extracted document state;
2. authoritative search chunks;
3. Part/Revision/Relationship registration;
4. BOM rows when applicable;
5. outbox events for active projections.

If the PostgreSQL transaction rolls back, the engineering changes, chunks and outbox requests roll back together.

`register_document(..., commit=False)` and `ingest_bom_csv(..., commit=False)` are used by this UoW while preserving their original commit-by-default behavior for legacy callers.

## 6. Runtime profiles

### Core

Core performs PostgreSQL lexical retrieval directly from `document_search_chunks` and metadata. No semantic projection event is required when Qdrant is disabled. Graph and object-storage projection events are also omitted when their capabilities are inactive.

### AI

AI can enqueue Qdrant search projection events. Qdrant outage produces projection backlog/retry without invalidating the PostgreSQL engineering transaction.

### Advanced

Advanced can additionally enqueue Neo4j and MinIO projection events. Both remain rebuildable/optional from the perspective of engineering source-of-truth.

## 7. Operations and monitoring

Engineering Admin API:

```text
GET  /api/v1/operations/projections
GET  /api/v1/operations/projections/outbox
POST /api/v1/operations/projections/process
POST /api/v1/operations/projections/rebuild
POST /api/v1/operations/projections/dlq/{event_id}/replay
```

Prometheus metrics:

```text
mgc_projection_outbox_backlog
mgc_projection_outbox_dead_letter
mgc_projection_outbox_oldest_age_seconds
```

Projection status is included in Operations Summary and Support Bundle. A lagging or DLQ-bearing pipeline makes operations AMBER, but it does not make Core readiness fail when PostgreSQL/evidence are healthy.

## 8. Rebuild procedure

A controlled projection rebuild should be executed by Engineering Admin after the target store is prepared/emptied as required:

```text
POST /api/v1/operations/projections/rebuild?target=search
POST /api/v1/operations/projections/rebuild?target=graph
POST /api/v1/operations/projections/rebuild?target=object_storage
```

The call only creates outbox work. Workers perform the actual projection. Operators should watch backlog, DLQ and oldest-event age until the rebuild generation drains.

## 9. Safety boundary

Projection workers do not approve engineering changes, Work Instructions, BOM translations or release decisions. They only reproduce derived representations of already committed controlled evidence.

PostgreSQL, local controlled evidence, Project/Manufacturing Area/Document ACL and human engineering approvals remain authoritative.
