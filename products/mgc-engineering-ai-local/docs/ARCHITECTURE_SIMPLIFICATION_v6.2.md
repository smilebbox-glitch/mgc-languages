# MGC v6.2 — Architecture Simplification

v6.2 does not remove engineering capabilities. It reduces the number of architectural concepts an engineer, developer and operator must understand at the same time.

## Primary model

MGC is a **modular monolith** with six bounded contexts:

1. Engineering Core
2. Configuration & Change
3. Manufacturing & Quality
4. Supplier & Field
5. Intelligence & Search
6. Platform & Operations

Existing v3–v6.1 APIs remain compatible. New development should depend on context/platform facades instead of importing feature services across domains.

## Four platform primitives

The preferred cross-context primitives are:

- **Object 360** — read-only engineering object view;
- **EvidenceRef** — one provenance contract;
- **Action/Decision** — one attention/decision contract;
- **EngineeringEnvelope** — one connector ingestion envelope.

This replaces parallel domain-specific alert/evidence/connector shapes over time without a destructive schema rewrite.

## Data ownership

### Authoritative external
PLM/PDM, ERP, MES and QMS remain authoritative for their source records.

### MGC authoritative
Workflow state, decision records, mapping confirmation, pilot evidence and operational incidents are owned by MGC.

### Derived/rebuildable
Embeddings, Qdrant indexes, Neo4j projection, risk signals and summaries may be rebuilt from authoritative evidence.

PostgreSQL is the core platform store. Neo4j and Qdrant are never allowed to become hidden sources of engineering truth.

## Compatibility strategy

v6.2 is an incremental refactor, not a big-bang rewrite:

- legacy APIs remain mounted;
- legacy tables are not duplicated;
- new simplified APIs are additive;
- advanced routes are hidden only when the deployment profile disables the capability;
- ACL remains authoritative regardless of role or profile.

## Non-goals

v6.2 does not introduce Kafka, a BPMN engine, microservices, another database, autonomous engineering decisions or a new AI model dependency.
