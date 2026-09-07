# MGC Engineering AI Local v6.3.8 — Data Lifecycle, Retention & Compliance

## Purpose
v6.3.8 adds a controlled lifecycle layer for engineering evidence without changing PLM/MES authority. PostgreSQL + local evidence storage remain authoritative; Qdrant and Neo4j remain rebuildable projections.

## Core invariants
- Archival is metadata/state management and does **not** delete authoritative engineering records.
- Active legal hold blocks purge request creation and purge execution.
- Released Engineering Release Packages are immutable retention evidence and are not normal purge targets.
- Projection purge deletes only rebuildable search/graph projections; PostgreSQL `document_search_chunks`, Document row, and local evidence file remain intact.
- Authoritative purge is disabled by default (`DATA_LIFECYCLE_AUTHORITATIVE_PURGE_ENABLED=false`).
- Authoritative purge, when explicitly enabled, is limited in v6.3.8 to unreferenced Document evidence after retention expiry and policy approval.
- Purge is 4-eyes: maker cannot authorize or execute own request; service accounts cannot act as checker/executor.
- A purge request is bound to an entity SHA-256 snapshot. Any entity change invalidates the authorized request.
- Lifecycle events are append-only and hash-chained. Database triggers reject UPDATE/DELETE of lifecycle event rows.

## New data model
- `engineering_retention_policies`
- `engineering_legal_holds`
- `engineering_data_lifecycle_states`
- `engineering_purge_requests`
- `engineering_lifecycle_events`

## Retention policy
A policy can be scoped by entity type, project and manufacturing area. It defines archive timing, minimum retention, immutable minimum retention and whether authoritative purge may ever be considered.

Policy resolution is most-specific-first: project+area → project → global entity-type policy.

## Legal hold
Legal hold may target a specific entity or a broader project/area/entity-type scope. Holds can have an expiry or remain active until explicitly released. Legal hold never silently expires a purge already in progress: execution re-checks active holds.

## Controlled purge workflow
`request → second-person authorization → execution`

### Projection-only purge
Supported for Document in v6.3.8. It calls the SearchPort and GraphProjectionPort deletion contracts. Core PostgreSQL chunks and local evidence are preserved, making re-index/rebuild possible.

### Authoritative purge
Fail-closed gates:
1. global switch enabled;
2. entity type supported (`document` only in v6.3.8);
3. matching retention policy exists;
4. policy explicitly allows authoritative purge;
5. retention period elapsed;
6. no active legal hold;
7. entity snapshot unchanged since authorization;
8. document is not referenced by release package, WI/layout source, BOM source or controlled relationship evidence.

Only after all gates can the file, authoritative chunks and Document row be removed.

## Storage quota
Optional quotas are disabled by default (`0 = unlimited`). Quota checks are applied to interactive engineering-document upload and external connector ingestion. Quotas can be set at project and manufacturing-area level.

## Evidence lineage
Admin lineage API exposes controlled references from documents to WI/layout/relationships, release package snapshots and lifecycle hash-chain events. The goal is explainable retention decisions before any destructive operation.

## Operations / monitoring
Lifecycle posture is included in Operations Summary and Support Bundle. Prometheus exports:
- `mgc_lifecycle_purge_requests{state=...}`
- `mgc_lifecycle_active_legal_holds`
- `mgc_lifecycle_authoritative_purge_enabled`

Authorized-but-not-executed purge work raises Operations Summary to AMBER without making Core readiness RED.

## Non-goals
- no automatic deletion scheduler in v6.3.8;
- no legal/compliance certification claim;
- no qualified electronic signature claim;
- no PLC/robot/machine-control operation;
- no automatic PLM/MES mutation;
- no purge of released package evidence.
