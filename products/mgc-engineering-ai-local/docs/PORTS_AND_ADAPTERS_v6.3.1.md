# Ports & Adapters — v6.3.1

## Purpose

v6.3.1 applies dependency inversion inside the existing modular monolith. The goal is not to introduce microservices, but to stop application/domain services from knowing concrete infrastructure technologies.

## Application ports

Technology-neutral contracts live under `backend/app/ports/`:

- `SearchPort` — indexing/deletion/retrieval;
- `GraphProjectionPort` — optional derived graph synchronization/neighborhood;
- `ObjectStoragePort` — optional evidence mirroring;
- `AIAnalysisPort` — controlled evidence-grounded text synthesis;
- `TranslationProviderPort` — machine-translation provider only.

Translation memory, engineering token validation, ACL, evidence visibility, approval and document lifecycle remain outside the provider adapter.

## Runtime adapters

`backend/app/adapters/registry.py` selects adapters from the runtime profile/capabilities.

### Core

- Search: deterministic PostgreSQL metadata/lexical adapter;
- Graph: no-op adapter;
- Object storage: local-evidence/no-op mirroring adapter;
- AI analysis: disabled adapter;
- Machine translation: disabled adapter, while exact approved glossary + translation memory remain available.

Core must start without importing `qdrant_client`, `sentence_transformers`, `neo4j` or `minio`.

### AI

- semantic search can select the Qdrant adapter;
- local OpenAI-compatible model adapter can provide evidence synthesis and translation;
- application services do not know endpoint/client implementation details.

### Advanced

- Neo4j graph projection and MinIO evidence mirroring can be selected as optional adapters;
- these remain derived/optional infrastructure, not engineering source-of-truth systems.

## Refactored application paths

The following no longer import concrete Qdrant/Neo4j/MinIO/model HTTP clients:

- document ingest;
- global engineering RAG;
- engineering/BOM translation;
- Work Instruction translation;
- Work Instruction RAG;
- Intelligence/Search HTTP delivery surface;
- optional operational health probes.

## Dependency injection

Critical application functions accept optional port parameters. This allows deterministic unit testing with fake adapters and prevents tests from requiring production infrastructure.

## Source of truth

Ports/adapters do not change authority rules:

- PLM/PDM remains authoritative for product structure where configured;
- MES/ERP/QMS remain authoritative for their external transactions/records;
- PostgreSQL + evidence storage remain MGC's authoritative internal controlled set;
- Qdrant and Neo4j remain rebuildable projections;
- AI/translation output never becomes approval by itself.

## Deployment invariant

Runtime profile composition is capability composition, not authorization. Project / Manufacturing Area / Document ACL is still applied independently and fail-closed.
