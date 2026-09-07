# v6.3.4 Engineering Revision & Conflict Management

The database remains authoritative and optimistic locking remains fail-closed. v6.3.4 adds controlled revision snapshots, idempotent-write receipts, edit-conflict history and explicit human-reviewed visual diffs. New Work Instruction/Layout revisions clone controlled content into Draft state with lineage; approval/translation review is never silently inherited where re-review is required. Automatic merge of controlled engineering content remains disabled. See `docs/REVISION_CONFLICT_MANAGEMENT_v6.3.4.md`.

# v6.3.3 Database & Domain Integrity Hardening

PostgreSQL remains the engineering source of truth. Human-edited controlled records now use optimistic row versions, stale-write detection and explicit Unit-of-Work boundaries. Critical engineering writes and their audit/event evidence commit atomically; database constraints enforce basic BOM and manufacturing invariants. See `docs/DOMAIN_INTEGRITY_v6.3.3.md`.

# v6.3.2 Transaction & Projection Reliability

PostgreSQL is the only authoritative transaction boundary. Document ingest persists engineering state, `document_search_chunks` and projection outbox requests in one commit. Qdrant, Neo4j and MinIO are rebuilt asynchronously through idempotent adapters with retry/DLQ/receipt semantics. See `docs/TRANSACTIONAL_OUTBOX_v6.3.2.md`.

# v6.3.1 Ports & Adapters + Manufacturing Intelligence Hardening

The modular monolith now applies dependency inversion at the application/infrastructure boundary. `ingest`, RAG, engineering translation and Work Instruction RAG depend on technology-neutral ports. Runtime-selected adapters provide deterministic Core behavior or optional Qdrant/Neo4j/MinIO/local-model enrichment. Concrete advanced client packages do not appear in application/delivery modules.

For governed Work Instructions, an approved revision is immutable. Foreign-language translation review is bound to a SHA-256 fingerprint of the source text and steps; changing the source invalidates the reviewed translation (`stale`) and requires a new translation/review before approval. Database schema remains v6.3.0.

# v6.3.0 Manufacturing Work Instructions & Station Intelligence

The manufacturing-quality bounded context now owns a governed station-instruction layer: `ManufacturingLine → ProcessStation → ProcessOperation → WorkInstruction`, plus `ManufacturingLayout → StationLayoutPlacement`. Translation is a cross-cutting evidence/view service and never mutates authoritative BOM or partner documents. Instruction RAG is ACL/area filtered before retrieval and generation. The application remains a modular monolith; no new microservice is introduced.

# v6.2.2 Bounded-Context Router Decomposition

The v6.2.0 modular-monolith boundary is now reflected in the HTTP source tree. Legacy handlers are split across six physical bounded-context modules under `backend/app/api/contexts/`; `context_shared.py` centralizes ACL/visibility helpers; `context_registry.py` composes active contexts by runtime capability envelope. Public URLs remain stable and authorization remains independent from profile composition. Database schema remains 6.2.0.

# v6.2 Architecture Simplification

The primary architecture is now a modular monolith with six bounded contexts. PostgreSQL is the core authoritative MGC store; Qdrant/Neo4j are optional derived projections. New cross-context work uses Object 360, EvidenceRef, normalized Action/Decision and EngineeringEnvelope contracts. Existing APIs/tables remain backward compatible. See `docs/ARCHITECTURE_SIMPLIFICATION_v6.2.md`.

# Architecture — MGC Engineering AI Local v6.0.9

## v6.0.9 — Production Operations Acceptance & Game Days

The operations-acceptance layer is evidence-only. It records approved failure-drill plans, timestamps, RTO/MTTR/RPO, runtime gate evidence and final recommendations. It never injects faults, never bypasses runbooks and never authorizes production deployment.

## v6.0.8 — Action-first UX and feedback closure

```text
Authorized Digital Thread / Engineering OS
              |
              v
        Role UI focus only
              |
     +--------+---------+
     |        |         |
  Attention Decisions Guided workflow
   <= 5      <= 3       <= 3
     |        |         |
     +--------+---------+
              |
              v
      Collapsed evidence drill-down

Pilot aggregate feedback -> Usability issue -> Remediation -> UAT verification -> Verified/Closed
```

The role layer never changes Project/Manufacturing Area/Document authorization. Usability records are workflow-level aggregate evidence; critical unresolved usability issues block controlled GO, and closure requires explicit remediation plus verification evidence.

## v6.0.6 — Controlled Pilot evidence layer

The pilot layer sits above the existing Engineering Intelligence OS and does not become an HR/productivity system. It stores pilot definitions, role/scenario outcomes and aggregate UX telemetry only. Formal controlled-pilot evaluation consumes existing reconciliation/security evidence and explicit corporate runtime gates; the final deployment decision remains human.

## v6.0.5 — Security & Enterprise Deployment Hardening

```text
Corporate Browser
      | TLS 1.2/1.3
      v
Enterprise Edge -> OIDC Proxy -> Gateway -> API
                                      |
                                      +-> runtime PostgreSQL role (DML only)

Schema Migration Job ----------------+-> migration PostgreSQL role (one-shot DDL)

PLM/ERP/MES/QMS webhook client
      | mTLS + per-source HMAC
      v
Machine Edge -> Webhook Gateway -> Integration Contract / Quarantine
```

Security remains defense-in-depth: network segmentation does not replace backend authorization; mTLS does not replace webhook HMAC; SBOM/static gates do not replace the build-host CVE scan or penetration testing.


## v6.0.4 — Performance, Scale & Load Certification

```text
Production-shaped engineering data
        |
        +-- BOM / relationships
        +-- VIN / genealogy
        +-- series quality
        +-- integration objects / mappings
        |
        v
Composite read-path indexes
        |
        v
Benchmark / load harness
        |
        +-- p50 / p95 / p99
        +-- throughput / error rate
        +-- capacity envelope
        +-- Pilot / Enterprise profiles
        |
        v
Human IT/SRE performance acceptance
```

Performance optimization is subordinate to security and evidence correctness. No benchmark mode bypasses ACL, provenance, source-of-truth conflict handling or human approval. CI synthetic results validate the harness only; real certification is executed on the target PostgreSQL/Redis/Qdrant deployment.

## v5.5 Configuration & Release Assurance layer

```text
PLM/PDM (authoritative EBOM)
          |
          v
      AS-DESIGNED
          |
          +---- Variant applicability / effectivity
          |
          v
ERP/Manufacturing (authoritative MBOM)
          |
          v
       AS-PLANNED ---- Change Cut-In / PPAP / stock disposition
          |
          v
MES/import (authoritative AS-BUILT observation)
          |
          v
Configuration & Release Assurance
          |
          +-- EBOM↔MBOM deterministic diff
          +-- 150%→100% configuration
          +-- VIN/plant/date effectivity
          +-- Buildability + Handover gate
          +-- Release Package / Baseline / Drift
          +-- Cross-system consistency
```

The v5.5 database rows are controlled local evidence/shadow records, not replacement masters for PLM/PDM, ERP or MES. Configuration-authority writes through the human API require Engineering Admin. AS-BUILT records are imported observations and are never used to issue production commands. `UNKNOWN` applicability fails closed. Release Baseline schema `mgc-release-baseline-v3` freezes visible manufacturing BOM, effectivity, cut-in and supersession state in addition to the prior engineering snapshot.

## v5.2 Engineering Knowledge Memory

The Digital Thread now has an explicit reusable-memory layer. Historical ECR/ECO, 8D, defects, Design Reviews and Validation Issues are normalized into ACL-filtered case views. Deterministic CPU-only similarity ranks analogues and exposes the reasons for the score. Human-curated `EngineeringLesson` records preserve reusable problem/decision/outcome summaries with explicit draft/validated/archived governance. Portfolio search is permission-preserving: project, manufacturing-area and document evidence are filtered before a case is eligible for ranking.

```text
Corporate engineer browser
      |
      v
Corporate OIDC / oauth2-proxy
 engineering-group gate
      |
      v
Internal gateway (no host port)
      |
      v
FastAPI OIDC + group re-check
      |
      v
+------------------------ AIR-GAPPED BACKEND NETWORK -------------------------+
|                                                                             |
|   FastAPI / Celery ---- Qdrant ---- PostgreSQL ---- Neo4j ---- MinIO        |
|         |                                                                   |
|         +---- /models/embeddings  (local BGE-M3)                            |
|         +---- /models/reranker    (local CrossEncoder)                      |
|         +---- /models/docling     (local layout/OCR/table artifacts)         |
|         |                                                                   |
|         +---- http://model-server:8000/v1                                   |
|                         |                                                   |
|                         v                                                   |
|                 vLLM + local multimodal weights                             |
|                 /models/generative                                          |
|                                                                             |
+-----------------------------------X-----------------------------------------+
                                    X public internet not required
```


## v5.1 Engineering Change Intelligence layer

```text
Proposed engineering change
        |
        v
Digital Thread (ACL-filtered)
        |
        +-- deterministic impact categories
        +-- freshness/stale registry
        +-- action queue
        +-- variant/workshop impact
        +-- traceability coverage
        +-- full baseline diff
        |
        +-- optional local RAG synthesis for Ask Digital Thread
```

The simulator is read-only. It does not persist scenario changes, change product structure, edit ECR/ECO, approve PPAP/sourcing or alter Release Readiness. New baselines store schema `mgc-release-baseline-v2` with process/cost/architecture/interface snapshots inside the existing JSON field, so no database migration is required.

## v5.0 Engineering Digital Thread layer

The Digital Thread Explorer is a deterministic application service above the existing relational engineering model. It does not require Neo4j and does not ask the LLM/VLM to infer relationships. Neo4j remains optional GraphRAG infrastructure.

```text
Visible project context after ACL
      |
      v
Engineering Digital Thread service
      |
      +-- Part/BOM + Document/CAD
      +-- Requirements/V&V
      +-- Process/Work Instruction
      +-- Supplier/Localization + Cost
      +-- ECR/ECO + Validation issues
      +-- Vehicle Architecture/Interfaces
      +-- Variants + Release Baselines
      |
      v
Project Thread / focused Part Impact Thread
```

Evidence-bearing objects fail closed if their referenced evidence is outside the caller's visible-document set. The service returns only explicit stored links, plus trace gaps for missing evidence. Cross-domain coverage is advisory and is deliberately not wired into Release Readiness.

## Engineer-only identity boundary

Production has two independent authorization layers: the OIDC edge proxy permits only engineering groups, then FastAPI validates the signed access token and repeats the engineering-group check. The base gateway/API/model-server are not published to the host. Document ACL is evaluated only after the caller has passed this service-level engineer gate.

Human-facing API routes are checked by `scripts/api_access_preflight.py` so a future endpoint cannot silently omit `Depends(get_identity)`. The machine webhook is separately protected by timestamped HMAC validation.

## Document activity trail

Each document has an append-only application timeline with user, UTC time, action, summary and details. Events form a SHA-256 previous-event chain plus a separate per-document head/count anchor and are verified when history is read. This provides tamper evidence; production deployments that require stronger non-repudiation should export the audit stream to immutable corporate logging/SIEM.

## Inference path

Engineering Copilot and drawing vision use the same internal OpenAI-compatible endpoint by default. A future split deployment can point `VLM_BASE_URL` at a second internal service without changing application code.

## Retrieval path

1. local parsing / Docling;
2. local embeddings;
3. Qdrant dense + BM25 hybrid retrieval;
4. local reranker;
5. evidence is passed to local vLLM;
6. answer is returned with citations.

## Engineering Vision / CAD path

1. Vector PDF text and drawing primitives are extracted with coordinates before OCR fallback.
2. Structured engineering entities retain page/bbox/method/confidence provenance.
3. The local VLM is a verification layer and cannot silently overwrite deterministic facts.
4. STEP/STP geometry remains deterministic through OCCT/CadQuery, with B-Rep topology, surface/edge descriptors and AP242/PMI semantic signal inspection.
5. STEP faces are exposed as addressable B-Rep features with exact cylinder parameters, center, axis and bounding boxes.
6. Drawing entities are linked to STEP candidates as `linked_unique`, `linked_multiple` or `unmatched`; repeated equal features remain ambiguous instead of being guessed.
7. DXF is parsed as deterministic 2D vector geometry; STL remains mesh evidence.
8. Native КОМПАС-3D and T-FLEX CAD use vendor-aware licensed Windows gateways to create traced STEP/PDF/DXF derivatives; the same contract remains extensible to CATIA/NX/Creo/JT/SOLIDWORKS.

See `docs/ENGINEERING_VISION.md`, `docs/DRAWING_CAD_LINKING.md` and `docs/KOMPAS_TFLEX_INTEGRATION.md`.

## External enterprise systems

PLM/PDM/ERP integrations from v3 remain available, but an air-gapped deployment should expose only approved internal endpoints. Network shares should preferably be mounted read-only on the host and then passed into the container.

## Engineering Change Management

v3.8 adds a governed change layer above deterministic engineering evidence:

```text
Revision Compare + BOM + Issues + Relationships
                 |
                 v
          Change Impact
                 |
       canonical impact digest
                 |
ECR -> Technical Review -> Final Approval -> ECO -> Implementation
                 |
                 v
        ChangeEvent hash chain
                 |
                 +----> affected DocumentActivity timelines
```

Final approval re-runs deterministic impact analysis. If its canonical digest or source SHA-256 evidence differs from the reviewed snapshot, the ECR returns to `impact_review`. High/Critical risk requires an approved Design Review. See `docs/ENGINEERING_CHANGE_MANAGEMENT.md`.

## v3.9 project layer

`Project` is now the engineering-program shell above Part/Document/BOM/Design Review/Change Request. `ProjectMilestone` stores project gates. `project_workspace.py` computes an explainable advisory readiness score from visible authoritative evidence only. Project ACL is evaluated first, while document ACL remains stronger and prevents hidden evidence from being promoted into the project view. Release readiness never performs or substitutes final human release approval.

## v4.0 automotive manufacturing-area layer

`ProjectArea` adds a controlled manufacturing dimension on top of the existing Project/Document ACL model. `Document.manufacturing_area` is the primary evidence classification; `ProjectMilestone.manufacturing_area` scopes release milestones. Parts/issues/changes are projected into an area through their visible document evidence rather than by granting new authority.

The UI uses one area context selector; RAG forwards the selected area into the Qdrant payload filter. Area ACL never overrides Document ACL.

## v4.1 Automotive Quality Digital Thread

The Project Workspace now has a Core Tools layer:

```text
Project / Manufacturing Area
        |
        +--> APQP deliverables
        +--> Special Characteristics --> PFMEA --> Control Plan
        +--> PPAP evidence/submission
        +--> 8D --> optional ECR/ECO
```

Quality data is structured, but never treated as an authority that can release a product. The core authorization invariant remains: Project/Area visibility cannot widen Document ACL. Quality source/evidence IDs are filtered through visible engineering evidence before returning them to a caller.


## v4.2 Process Digital Thread

```text
Project / Manufacturing Area
        |
        v
Manufacturing Line
        |
        v
Station -> Operation -> Equipment / Tooling
                 |
                 +-> Process Parameter -> Special Characteristic
                 |                         |
                 +-----------------------> PFMEA -> Control Plan
                 |
                 +-> Process Defect -> 8D -> ECR/ECO
```

The process model is an engineering digital thread, not a control plane. No API in this module writes to PLCs, robots, torque controllers, paint equipment or other production machinery. Machine integration, if ever required, must be a separately reviewed read-only evidence connector before any wider scope is considered.

Manufacturing-area ACL and document ACL remain authoritative even in the aggregate **All zones** project view. Process, quality and milestone objects from an area outside the caller's allowed area groups are excluded before readiness calculation and timeline rendering.


## v4.3 Launch & Plant Readiness

```text
Project / Manufacturing Area
          |
          +-- Process Digital Thread (line/station/operation/assets)
          +-- Quality Core Tools (APQP/PFMEA/CP/PPAP/8D)
          +-- ECR/ECO / milestones / documents
          |
          v
Launch Readiness Engine
  +-- tooling & equipment
  +-- supplier & PPAP
  +-- Run@Rate / capacity
  +-- pilot build / DV / PV
  +-- packaging & logistics
  +-- people / training
  +-- Safe Launch
          |
          v
Advisory SOP readiness + evidence-backed blockers
```

The engine is read/evidence oriented. It does not start equipment, alter PLC setpoints, or authorize SOP automatically.


## v4.4 Automotive Requirements & Verification Matrix

```text
OEM / Regulatory / Customer / Internal Requirement
        |
        +--> source document + clause/reference
        +--> system / function
        +--> part(s) / Special Characteristic(s)
        +--> verification plan
                 |
                 +--> analysis / inspection / measurement / simulation
                 +--> DV / PV / Run@Rate / demonstration
                 +--> approved Design Review
                 +--> evidence documents
        |
        +--> ECR/ECO linkage
        |
        v
Evidence-backed traceability state
```

A `passed` status is not sufficient by itself. The backend requires visible evidence, a passed Launch Trial, or an approved Design Review before a verification can be recorded as passed through the API. The verification captures a snapshot of the requirement update timestamp and source-document SHA-256; later requirement/source changes make the prior verification stale until re-reviewed. Project/Manufacturing-Area/Document ACLs are applied before the matrix is calculated. The matrix is advisory traceability and does not claim legal, OEM, homologation, functional-safety, or other compliance certification.

## Supplier & Localization Digital Thread — v4.5

```text
Localization Item
  -> Technical Package / RFQ / Nomination
  -> Tooling / Equipment
  -> Capacity / Run@Rate
  -> PPAP
  -> Incoming Quality
  -> Supplier 8D / ECR-ECO
  -> Supplier Readiness + Evidence Pack
```

Localization percentage is stored as an informational project KPI and is deliberately separated from supplier-readiness scoring. Existing PPAP, LaunchTrial and 8D records are reused rather than duplicated. Project, manufacturing-area and document ACL checks remain authoritative for aggregation.


## Cost & Engineering Economics v4.6

The cost layer is a separate advisory domain. `CostBaseline`, `CostLine` and `SupplierQuotation` are ACL-scoped by project/manufacturing area and only expose visible project parts/evidence. Deterministic cost calculations are kept separate from Project Release Readiness. ERP/Finance remains the financial system of record. Change baselines can reference ECR/ECO to calculate unit and annual cost deltas without changing the engineering approval workflow.


## Vehicle / System Architecture & Interface Management

The v4.8 layer models an automotive product hierarchy without replacing PLM/PDM authority:

```text
Vehicle
  -> System
     -> Subsystem
        -> Assembly
           -> Component / Part
```

Interfaces are first-class records between architecture nodes. Supported semantic classes are mechanical, electrical, fluid, thermal, data, control, packaging and other. A critical/safety/regulatory interface is not considered verified merely because a user selects PASSED: accessible evidence or a valid linked requirement verification is required. The verification stores a fingerprint of both endpoint nodes, interface specification and linked requirements; later interface/endpoint changes make the previous verification stale.

Architecture data is advisory and ACL-scoped. Project access never promotes hidden part/document evidence, and the interface layer does not issue automatic engineering release approval.

## v4.8 Vehicle Variant & Configuration Management

The configuration layer is advisory and sits above the existing product/system architecture. `VehicleVariant` represents named derivatives; `ConfigurationApplicability` stores explicit applicability to engineering entities. Missing applicability is UNKNOWN, never implicit inclusion. Explicit part-level applicability takes precedence over inferred interface-level applicability. Project, manufacturing-area and document ACL checks remain authoritative.


## v4.9 Engineering Traceability & Release Baseline

`ReleaseBaseline` is an immutable evidence snapshot over the visible engineering state at a controlled checkpoint. Its `snapshot_json` is canonicalized and SHA-256 fingerprinted. There is intentionally no update endpoint: later state is represented by another baseline. Baseline visibility is fail-closed if any contributing source document is no longer visible to the caller.

BOM version comparison uses `BOMItem` rows tied to immutable source documents. The deterministic diff separates additions, removals, same-position replacements and field-level changes. Optional BOM columns include position, supplier and unit-price metadata.

Release baselines and BOM comparisons remain advisory evidence. PLM/PDM remains product-structure authority, ERP remains financial/transaction authority, and human release approval is mandatory.

## v6.0 — Engineering Intelligence Operating System

The v6.0 layer sits above the existing domain services and does not become a new system of record.

```text
Project / Area / Document ACL
          ↓
Existing v5.0–v5.8 domain engines
          ↓
Engineering Intelligence OS
  ├─ Role Decision Cockpit
  ├─ Unified Action Inbox
  ├─ Decision Queue
  └─ Cross-domain Workflow Orchestration
          ↓
Human engineering decision / authoritative source-system transaction
```

Role selection is applied only after authorization-scoped source contexts are built. The OS never uses a selected role to widen Project, Manufacturing Area or Document visibility. Workflow cases store coordination state and evidence references; they do not replace the corporate task/project-management platform.


## v6.0.1 — Production Hardening Foundation

The production-hardening layer is deliberately orthogonal to automotive domain logic. It adds operational contracts around the existing system:

- **Liveness** proves only that the API process is running.
- **Readiness** fails closed on required dependencies and the expected schema marker without exposing connection details.
- **Schema bootstrap** remains additive/idempotent but is serialized with a bounded PostgreSQL advisory lock.
- **Worker health** is checked through Celery rather than the API container HTTP probe.
- **Backup authority** is PostgreSQL + evidence storage + Qdrant snapshot; Redis is transient and Neo4j remains a derived projection.
- **Local inference degradation** does not make the deterministic engineering core unready.
- **Operational request logging** records route templates only, avoiding VIN/part-number leakage from concrete URLs.

This release is a foundation for pilot hardening; it does not claim PostgreSQL HA/PITR, enterprise performance certification or site-level DR without external infrastructure validation.


## v6.0.2 — Integration Hardening & Data Confidence

```text
Authoritative PLM / PDM / ERP / MES / QMS
                 ↓
        Vendor-neutral adapter
                 ↓
         MGC integration contract
  schema + identity + source timestamp
                 ↓
          immutable ingest ledger
          ↙                 ↘
   accepted evidence       quarantine / DLQ
          ↓                 ↓ explicit replay
    Digital Thread       contract revalidation
```

Freshness and completeness are evidence-quality attributes, not permission attributes and not automatic engineering decisions. Contract-invalid records are prevented from entering the controlled Digital Thread; stale but valid records remain visible with explicit confidence. When the source offers no trustworthy revision/checksum/timestamp, payload SHA-256 is used after download so idempotency cannot silently hide changed bytes.


## v6.0.3 — Real Integration Pilot & Data Reconciliation

```text
PLM / PDM EBOM ─┐
ERP MBOM ───────┼─> Integration contracts / immutable ingest evidence
MES genealogy ──┤                     ↓
QMS defects ────┘        Canonical mapping resolution
                                      ↓
                            Read-only reconciliation
                       ┌────────┬─────────┬────────┐
                       │EBOM/MBOM│MES/Release│QMS links│
                       └────────┴─────────┴────────┘
                                      ↓
                    SLO + mapping + authority conflicts
                                      ↓
                       Controlled Pilot Acceptance
                                      ↓
                         Human go-live decision
```

`IntegrationEntityMapping` stores only explicit alias resolution and verification metadata. It does not copy authoritative part/BOM/VIN/supplier state. Mapping resolution is project-scoped, fingerprint-aware and stale mappings are not applied. Canonicalization occurs on an in-memory reconciliation copy, preserving immutable source evidence.

Reconciliation reports are computed from existing `ExternalObject` integration evidence and canonical engineering entities. Multiple authority claims are surfaced as conflicts; MGC does not auto-select a winning source. The pilot gate is deliberately stricter than a weighted score: missing required roles, stale mappings, low/unknown required-source confidence, quarantine backlog, authority conflict, EBOM/MBOM mismatch or unresolved MES/release mismatch keeps the result `NOT_READY`.
