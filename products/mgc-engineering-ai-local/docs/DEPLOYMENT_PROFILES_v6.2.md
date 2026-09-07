# Deployment Profiles — v6.2

v6.2 introduces three runtime profiles. Profiles change runtime composition; they **do not change authorization**.

## Core

Required:

- PostgreSQL;
- Redis for transient background jobs;
- local evidence storage;
- API / worker / beat / frontend / gateway.

Not required:

- Qdrant;
- Neo4j;
- local LLM/VLM;
- MinIO.

Search degrades to deterministic lexical/metadata discovery. Engineering workflows, BOM/change/configuration/quality logic remain usable.

Start:

`make profile-core`

## AI

Recommended controlled-pilot profile. Adds:

- Qdrant;
- embeddings/reranker;
- local LLM;
- local VLM where configured.

Start:

`make profile-ai`

CPU/GPU selection remains automatic through the existing runtime script.

## Advanced

Adds optional advanced services/capabilities:

- Neo4j graph projection;
- optional object store;
- native CAD gateway extensions;
- advanced Field/Cost/Program surfaces.

Start:

`make profile-advanced`

## Backup semantics

PostgreSQL and evidence storage are authoritative. Qdrant snapshot is optional. Neo4j and Redis are rebuildable/transient. A Core backup therefore does not fail because Qdrant is absent.


## v6.2 hardening: fail-closed composition

- Unknown `DEPLOYMENT_PROFILE` values are rejected instead of silently widening to `advanced`.
- `FEATURES_ENABLED` cannot promote a lower profile to a higher-profile capability. Select `ai` or `advanced` explicitly.
- Core invariants (`postgres_core`, evidence storage, platform operations, Evidence contract) cannot be disabled.
- Legacy advanced routes are hidden by one declarative capability gate. The pre-auth response is a generic 404; authenticated runtime posture is visible through `/api/v1/runtime`.
- Object 360 is profile-aware: Core exposes Part, VIN/Build, Change, Defect and Requirement; Supplier appears only when `supplier_field` is active. VIN remains available in Core but field-claim evidence is omitted when Supplier/Field is disabled.
