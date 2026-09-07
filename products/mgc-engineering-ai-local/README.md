# MGC Engineering AI Local v6.3.34

## v6.3.34 Multi-Vehicle Product Applicability

v6.3.34 extends the existing engineering Digital Thread across Passenger Car, LCV, Truck, Bus, Special Vehicle and Component programs. It standardizes vehicle class/configuration attributes and explicit per-variant applicability on the existing `VehicleVariant` + `ConfigurationApplicability` model; DB schema stays 6.3.13 and source-system/human-approval boundaries remain unchanged. The demo now includes both a passenger BEV/AWD Rev C->D case and a 6x4 truck Rev A->B case. See `docs/MULTI_VEHICLE_PRODUCT_APPLICABILITY_v6.3.34.md`.

## v6.3.33 Pilot Readiness & UX Simplification

v6.3.33 turns the existing engineering platform into a clearer pilot-ready product without adding another domain module: five primary engineer workspaces, an evidence-backed bounded Action Center, a focused Project Workspace and progressive disclosure for advanced engineering/IT evidence. DB schema remains 6.3.13 and all authoritative/human-approval boundaries are preserved. See `docs/PILOT_READINESS_UX_SIMPLIFICATION_v6.3.33.md`.

## v6.3.32 Resilience Certification & Recovery Baselines

v6.3.32 promotes signed live resilience-drill evidence into human-approved recovery baselines and approved drill campaigns, then compares current per-scenario RTO against the approved previous-release baseline. Release certification fails closed on missing scenarios, invalid/tampered signatures, bootstrap/simulated evidence, threshold regression or RTO ceiling breach. A technical `GO` is required for production rollout but never self-authorizes production. See `docs/RESILIENCE_CERTIFICATION_RECOVERY_BASELINES_v6.3.32.md`.

## v6.3.31 Resilience Drill Orchestration

v6.3.31 adds bounded, operator-confirmed resilience drills for API replica loss, CPU-worker loss, Redis/Qdrant brownout and an integration gateway outage. Live injection uses only allowlisted Docker Compose actions, always attempts recovery, blocks dependency faults in production by default, and emits canonical privacy-safe drill evidence. Evidence can be bound to v6.3.30 incident evidence by SHA-256 + bounded signal codes without copying raw signal payloads or claiming root cause. See `docs/RESILIENCE_DRILL_ORCHESTRATION_v6.3.31.md`.

## v6.3.30 Production Observability & Automated Incident Evidence

v6.3.30 adds deterministic privacy-safe incident evidence over readiness/SLO/queue/integration/workload/HA snapshots, canonical SHA-256 integrity, bounded signal fingerprints, support-bundle evidence and opt-in incident materialization. Automatic destructive recovery, automatic incident resolution and production self-authorization remain forbidden. See `docs/PRODUCTION_OBSERVABILITY_INCIDENT_EVIDENCE_v6.3.30.md`.

## v6.3.29 Target-Host Deployment Assurance

v6.3.29 adds a privacy-safe per-node target-host probe, deterministic host-envelope certification, canonical SHA-256 evidence and a fail-closed deployment gate for rolling/blue-green rollout. A real deployment requires a PASS target-host assurance report; host PASS is deliberately not a load, CVE/SCA, integration or production authorization. See `docs/TARGET_HOST_DEPLOYMENT_ASSURANCE_v6.3.29.md`.

## v6.3.28 Integration Runtime Assurance

v6.3.28 bounds PLM/PDM/ERP/MES/QMS cached-data staleness, blocks stale cached reads, adds opt-in recovery sync and fixes successful `IntegrationRun.status=ok` reliability accounting. See `INTEGRATION_RUNTIME_ASSURANCE_v6.3.28.md`.

## v6.3.27 Real Integration Certification

v6.3.27 formalizes vendor-neutral PLM/PDM/ERP/MES/QMS adapter contracts with bounded read-only live probes, deterministic repeated-read/idempotency checks, privacy-safe fingerprints and fail-closed degraded cached-read posture. Source-system writeback remains disabled. Use `./mgcctl certify integration ...`. See `docs/REAL_INTEGRATION_CERTIFICATION_v6.3.27.md`.

## v6.3.26 Operations Consolidation & mgcctl

v6.3.26 consolidates operator-facing workflows behind the safe `mgcctl` facade while retaining existing Makefile/script entry points and fail-closed deployment/DR/certification logic. See `docs/OPERATIONS_CONSOLIDATION_v6.3.26.md`.

## v6.3.25 External Trust Anchoring & Evidence Retention Governance

v6.3.25 extends the append-only release provenance ledger with bounded signing-key validity, minimum-retention/legal-hold policy, verified registry checkpoints, external tip-hash anchoring, WORM/Object-Lock receipt integration and offline auditor bundles. External anchor/WORM evidence is fail-closed when required; missing optional corporate trust evidence remains `CONDITIONAL`. Technical trust never self-authorizes production. See `docs/EXTERNAL_TRUST_RETENTION_v6.3.25.md`.

## v6.3.24 Acceptance Evidence Registry & Release Provenance Ledger

v6.3.24 adds an append-only content-addressed registry for signed release acceptance, approved baselines, load/failover evidence and public-key trust events. The registry verifies event/object SHA-256, replays key registration/revocation state, supports cross-version regression queries and audit reports, and can receive acceptance/baseline artifacts directly from the existing release pipeline. Technical evidence never self-authorizes production. See `docs/ACCEPTANCE_EVIDENCE_REGISTRY_v6.3.24.md`.

## v6.3.22 Production Load Certification Harness

v6.3.22 adds a reproducible target-host load harness for the v6.3.21 production-acceptance contract: controlled concurrency 15/30/100, domain-aware Object 360/BOM/WI/Digital Thread/RAG workload, p50/p95/p99 and error-budget measurement, DB/queue saturation evidence, canonical SHA-256 and detached OpenSSL signatures. Signed load evidence is verified and ingested directly by `production_certify.py`; unsigned evidence remains `CONDITIONAL`, and technical `GO` never self-authorizes production. See `docs/PRODUCTION_LOAD_CERTIFICATION_v6.3.22.md`.

## v6.3.21 Production Topology Certification & SLO Enforcement

v6.3.21 converts the 15/30/100-engineer topology references into a fail-closed technical acceptance contract: topology/authority/SLO/RTO/RPO evidence, DB-pool headroom/backpressure, Engineering Admin certification diagnostics, target-host evidence evaluation and a separate human-approved deployment guard. SLO burn blocks new rollout/GO rather than causing an LB cascade. Technical `GO` never self-authorizes production. See `docs/PRODUCTION_CERTIFICATION_SLO_v6.3.21.md`.

## v6.3.20 Multi-host Production Topology & External Load-Balancer Safety

v6.3.20 adds explicit per-node identity/failure-domain metadata, multi-host anti-affinity diagnostics, a sanitized external-LB eligibility contract, per-node Compose overlay, HAProxy reference, placement-only certification profiles for 15/30/100 engineers, fail-closed deployment guard and a disruptive external-LB host-loss drill harness. PostgreSQL/evidence fencing from v6.3.19 remains authoritative; topology telemetry is operational evidence only and never authorizes production. See `docs/MULTI_HOST_TOPOLOGY_v6.3.20.md`.

## v6.3.19 Database & Evidence Storage HA

v6.3.19 adds fail-closed PostgreSQL writer/schema/cluster fencing and active evidence-generation fencing across HTTP, ORM, Celery and maintenance writes. MGC does not perform PostgreSQL promotion/ST​ONITH; corporate HA infrastructure remains responsible for quorum, writer endpoint and storage replication. See `docs/DATABASE_EVIDENCE_STORAGE_HA_v6.3.19.md`.

## v6.3.18 High Availability & Failover Coordination

v6.3.18 adds application-tier API/worker/Beat/frontend redundancy, health-aware gateway failover and single-leader scheduler coordination. It deliberately does not claim physical host, database or evidence-storage HA. See `docs/HIGH_AVAILABILITY_FAILOVER_v6.3.18.md`.

## v6.3.17 Blue/Green Cutover & Automated Rollback Safety

v6.3.17 adds stable/candidate API revisions, consecutive candidate readiness, guarded gateway cutover, observation/SLO hooks and fail-closed rollback compatibility checks. See `docs/BLUE_GREEN_CUTOVER_ROLLBACK_v6.3.17.md`.

## v6.3.16 Rolling Upgrade & Deployment Safety

v6.3.16 adds task version/schema envelopes, worker-side runtime fencing, graceful drain, singleton Beat leadership and adjacent-patch rolling upgrade orchestration. See `docs/ROLLING_UPGRADE_DEPLOYMENT_SAFETY_v6.3.16.md`.

## v6.3.15 Operational Resilience & Self-Diagnostics

v6.3.15 adds process-local circuit breakers and controlled brownout behavior for Redis/Celery, Qdrant, local LLM/VLM and native CAD gateway dependencies. PostgreSQL and authoritative evidence storage remain the engineering sources of truth; optional infrastructure failure falls back to deterministic Core behavior where safe. Engineering Admin diagnostics are exposed through Operations, Prometheus and the privacy-safe support bundle. See `docs/OPERATIONAL_RESILIENCE_v6.3.15.md`.

## v6.3.14 Data Consistency & Disaster Recovery

v6.3.14 adds consistency-verified backup/restore, authoritative DB/evidence fingerprints, Digital Thread integrity checks and fail-closed restore/PITR readiness. See `docs/DATA_CONSISTENCY_DR_v6.3.14.md`.

## v6.3.13 Job Execution Recovery & Lease Safety

v6.3.13 hardens the v6.3.11 workload layer with PostgreSQL worker leases, per-dispatch fencing generations and auditable orphan recovery. Late Celery deliveries cannot write over a newer execution. Only explicitly replay-safe ingestion may auto-requeue; design-review and other decision-producing work requires confirmed Engineering Admin recovery. See `docs/JOB_EXECUTION_RECOVERY_v6.3.13.md`.

## v6.3.12 Supply Chain & Reproducible Builds

v6.3.12 adds a strict fail-closed corporate build path: profile-specific hashed Python locks/wheelhouses, approved npm lock + offline cache, immutable container/base-image digests, a SHA-256 verified offline OS-package bundle, `build.network: none`, build-input provenance hashes, OCI provenance labels and post-build attestation evidence. The source package intentionally remains `CONDITIONAL` until those artifacts are generated against the company's approved registries; no hashes or digests are fabricated. See `docs/SUPPLY_CHAIN_REPRODUCIBLE_BUILDS_v6.3.12.md`.

## v6.3.11 Background Jobs, Scheduler & Workload Isolation

v6.3.11 separates interactive/CPU/IO/CAD/AI/maintenance workloads, adds per-project concurrency, cooperative cancellation, retry/DLQ, managed progress and workload observability while keeping Core CPU-first. See `docs/WORKLOAD_ISOLATION_v6.3.11.md`.


## v6.3.7 Engineering Release Handover & Integration Safety

v6.3.7 adds a separate controlled outbound handover boundary for released engineering packages. PLM/PDM/MES write-back remains disabled by default (`HANDOVER_WRITE_ENABLED=false`) and target allowlists are empty. Handover jobs are immutable command records, dry-run by default, require idempotency-capable targets, maker-checker authorization and explicit identity-policy enforcement before controlled write. Delivery receipts and reconciliation hash-proof are stored as evidence. No PLC/robot/torque-controller or other machine-control path is introduced. See `docs/RELEASE_HANDOVER_SAFETY_v6.3.7.md`.

## v6.3.6 Enterprise Identity & Policy Enforcement

v6.3.6 binds approval/release governance to sanitized corporate identity assurance: OIDC subject/groups/issuer/ACR/auth-time/client-id, scoped allow/deny policies, human-only privileged actions, controlled approval delegation, production re-authentication and tamper-evident identity snapshots in approval evidence. Service accounts cannot approve or perform Final Release. A canonical SHA-256 Release Manifest is available for controlled PLM/MES handover without automatic production write-back. Optional PostgreSQL RLS is intentionally limited to the new identity-policy/delegation tables until the broader corporate DB-role model is certified. See `docs/ENTERPRISE_IDENTITY_POLICY_v6.3.6.md`.

## v6.3.5 Engineering Approval & Release Governance

v6.3.5 adds configurable approval matrices by project/manufacturing area/entity type, maker-checker / 4-eyes enforcement, segregation of duties, hash-chained approval evidence, and controlled Engineering Release Packages. Release Packages revalidate WI/layout/change/BOM evidence snapshots before production handover, obsolete superseded MGC-owned WI/layout revisions, and never mutate PLM/PDM-owned BOM/document evidence or send production-equipment commands.

Direct Work Instruction approval is disabled by default (`ALLOW_LEGACY_DIRECT_WI_APPROVAL=false`); use the controlled approval workflow. Approval records are tamper-evident engineering evidence and are not claimed to be a qualified electronic signature. See `docs/APPROVAL_RELEASE_GOVERNANCE_v6.3.5.md`.

---

## v6.3.4 Engineering Revision & Conflict Management

v6.3.4 turns the optimistic-locking foundation from v6.3.3 into a controlled multi-user engineering workflow. HTTP 409 `EDIT_CONFLICT` now returns the current authoritative record so the UI can show **current server version vs my unsaved changes** without automatic merge. Approved/obsolete Work Instructions and Manufacturing Layouts can create controlled Draft revisions with lineage and revision snapshots; foreign-language WI translation approval never carries into a new revision. Write idempotency receipts protect selected retry-prone mutation APIs, duplicate change-approval stages are rejected at database level, and Engineering Admin receives integrity/conflict observability.

No AI/CRDT auto-merge is allowed for controlled engineering content. Safety, quality, tooling and operation-step conflicts require explicit human resolution. See `docs/REVISION_CONFLICT_MANAGEMENT_v6.3.4.md`.

## v6.3.3 Database & Domain Integrity Hardening

v6.3.3 protects collaborative engineering writes from lost updates. Work Instructions, Process Stations, Manufacturing Layouts and Change Requests now carry optimistic `row_version` values; UI/API write flows can send `expected_version`, and stale edits fail with HTTP 409 `EDIT_CONFLICT` instead of overwriting a colleague's changes. Critical WI/station/layout writes and their audit records share a Unit of Work, while ECR/ECO state changes and the hash-chained change-event ledger are committed atomically. Fresh and upgraded databases enforce core BOM/station/WI numeric invariants; migration fails closed if invalid legacy data is detected.

See `docs/DOMAIN_INTEGRITY_v6.3.3.md`.

## v6.3.2 Transaction & Projection Reliability

v6.3.2 moves optional Qdrant/Neo4j/MinIO updates out of the authoritative engineering transaction. PostgreSQL now commits engineering state, authoritative `document_search_chunks` and transactional outbox events together; background workers then update rebuildable projections with idempotency keys, worker leases, exponential retry, DLQ/replay, stale-event suppression and delivery receipts. Core lexical search reads the PostgreSQL chunks directly.

Projection backlog/DLQ/lag is exposed to Operations/Prometheus but does not become a Core readiness gate. See `docs/TRANSACTIONAL_OUTBOX_v6.3.2.md`.


## v6.3.1 Ports & Adapters + Work Instruction Governance Hardening

v6.3.1 is a no-schema-change technical hardening release on top of v6.3.0. Application services now depend on technology-neutral Search, Graph Projection, Object Storage, AI Analysis and Translation ports; Qdrant, Neo4j, MinIO and OpenAI-compatible HTTP clients live behind runtime-selected adapters. Core therefore keeps deterministic lexical/no-op adapters without importing advanced infrastructure packages.

Work Instructions are hardened as controlled engineering records: approved revisions are immutable (new revision or obsolete transition only), and a reviewed Russian translation is tied to a fingerprint of the foreign source text/steps. Any source edit automatically makes the translation `stale` and blocks approval until re-translation and human review. See `docs/PORTS_AND_ADAPTERS_v6.3.1.md`.

## v6.3.0 Manufacturing Work Instructions & Station Intelligence

v6.3.0 adds an area-scoped engineering workspace for BOM translation, controlled electronic work instructions (EWI), shop/line/station layouts and instruction RAG. The source BOM/document is immutable; translations are separate reviewed views. Work instructions are governed records with revision/status, station/operation assignment, safety/quality checkpoints, tools/PPE, operator role, cycle time and evidence. Layouts expose who does what at each station without becoming PLC/MES machine control.

Primary flow: **Цех → линия → станция → операция → рабочая инструкция**. Manufacturing areas remain isolated through existing Project/Area/Document ACL. See `docs/WORK_INSTRUCTIONS_v6.3.0.md` and `docs/TRANSLATION_GOVERNANCE_v6.3.0.md`.

## v6.2.2 Service Dependency Decomposition

Core/AI/Advanced now have separate Python dependency envelopes. Service implementations and bounded-context routers are lazy-loaded, so Core startup does not require Qdrant, Sentence Transformers, Neo4j or MinIO clients. Docker build uses `DEPLOYMENT_PROFILE` and the runtime refuses to exceed the image's baked dependency profile. See `docs/DEPENDENCY_PROFILES_v6.2.2.md`.

## v6.2.2 Context Router Decomposition

v6.2.2 is a no-schema-change architecture patch on top of v6.2.0. The former 3,218-line legacy API route monolith is physically decomposed into six bounded-context handler modules while preserving the `/api/v1` contract. Runtime composition mounts only contexts backed by the selected capability profile; Core keeps deterministic Intelligence/Search through `lexical_search`, while Supplier/Field is not mounted unless its capabilities are active. See `docs/API_BOUNDED_CONTEXTS_v6.2.2.md`.

## v6.2.0 Architecture Simplification

v6.2 keeps the full engineering lifecycle but simplifies the product into a modular monolith with six bounded contexts and four cross-cutting platform contracts: Object 360, Evidence, Action/Decision and Connector Envelope. PostgreSQL is the core store; Qdrant and Neo4j are optional/rebuildable. The default Compose surface is Core, while `make profile-ai` is the recommended controlled-pilot profile and `make profile-advanced` enables the full optional envelope. Legacy APIs remain compatible.

Primary commands:

```bash
make profile-core      # deterministic core, no Qdrant/LLM/Neo4j required
make profile-ai        # Core + semantic/local AI enrichment
make profile-advanced  # AI + graph/advanced optional capabilities
```

See `docs/ARCHITECTURE_SIMPLIFICATION_v6.2.md`, `docs/OBJECT_360_v6.2.md` and `docs/DEPLOYMENT_PROFILES_v6.2.md`.


## v6.1.0 Corporate Deployment & Pilot Launch Kit

v6.1.0 packages the production-hardening work into a corporate deployment kit for a controlled 15–30 engineer automotive pilot: deterministic reference sizing, firewall/port matrix, AD/OIDC and source-system checklists, target-host launch readiness and a six-week rollout plan. Reference sizing never replaces target-host performance certification and no deployment status authorizes production.

## v6.0.9 Production Operations Acceptance & Game Days

v6.0.9 adds evidence-backed controlled operations game days for PostgreSQL, Redis, Qdrant, workers, integrations, TLS/OIDC, queue overload and backup/restore. MGC calculates RTO/MTTR/RPO and Operations GO/CONDITIONAL_GO/NO_GO, but fault injection and final production authorization remain outside the application.

## v6.0.8 Observability, Reliability & Production Support

v6.0.8 adds bounded-cardinality Prometheus/OTel operational metrics, dependency SLI/SLO/error budgets, queue/integration lag, operator incident evidence and a privacy-safe support bundle. It does not add an automotive business domain and does not automate destructive recovery or production authorization.


**Automotive Engineering Digital Thread + local AI, fully local / air-gapped.**


## v6.0.8 UX Simplification & Pilot Feedback Closure

v6.0.8 is the seventh production-readiness step. It does not add a new automotive domain. It turns the Project Workspace into an action-first, role-focused surface and adds a governed usability-feedback closure loop.

- role landing shows at most 5 primary actions, 3 human decisions and 3 guided workflows;
- specialized v5.x engineering modules remain available under one collapsed evidence drill-down;
- role selection changes presentation only and never changes ACL;
- pilot usability issues are aggregate workflow/interface records, not employee-performance records;
- open critical usability issues block controlled GO; open high-severity issues can only yield CONDITIONAL_GO;
- verified/closed feedback requires documented remediation and UAT verification evidence.

Key docs: `docs/UX_SIMPLIFICATION_AND_FEEDBACK_CLOSURE.md` and `docs/ROLE_GUIDED_WORKFLOWS.md`. Run `make ux-acceptance-preflight` to validate the UX governance harness.

## v6.0.6 Controlled Automotive Pilot & User Acceptance

v6.0.6 is the sixth production-readiness step. It adds a privacy-preserving controlled-pilot/UAT evidence layer rather than a new engineering domain: deterministic golden dataset, role/scenario outcomes, aggregate-only UX telemetry, explicit KPI thresholds and a human GO / CONDITIONAL GO / NO-GO evidence gate. Synthetic data can never authorize production GO.

Key docs: `docs/CONTROLLED_AUTOMOTIVE_PILOT.md`, `docs/PILOT_KPI_DEFINITION.md`, `docs/PILOT_GO_NO_GO.md`, `docs/GOLDEN_DATASET.md`. Run `make pilot-acceptance-preflight` to validate the harness; this preflight is not a real pilot decision.

## v6.0.5 Security & Enterprise Deployment Hardening

v6.0.5 is the fifth production-readiness step. It adds no new automotive business domain. It hardens identity, TLS/mTLS, runtime privileges, audit governance and the software-supply-chain gates required before an enterprise pilot.

- production OIDC fail-closed policy: HTTPS issuer/JWKS, audience, asymmetric algorithm allowlist, bounded skew and no parser-error disclosure;
- production trusted headers disabled by default; explicit proxy secret required for legacy opt-in;
- one-shot `schema-migrate` container with separate migration DB identity; long-running API/worker run without startup DDL in enterprise mode;
- TLS 1.2/1.3 browser/SSO edge and separate mTLS machine webhook edge;
- admin-only audit export with redaction + SHA-256 export chain, and guarded retention policy;
- offline CycloneDX-style declared-component SBOM, deterministic source secret scan and build-host Trivy/Grype hook;
- threat model, least-privilege service-account guidance and enterprise deployment runbook;
- enterprise deployment template forbids floating `:latest` image references.

Packaging does **not** claim a completed CVE scan or dependency-lock certification. Those fail-closed gates must run against the actual corporate mirror/wheelhouse and built images. See `docs/ENTERPRISE_SECURITY_DEPLOYMENT.md`, `docs/THREAT_MODEL_v6.0.5.md` and `docs/LEAST_PRIVILEGE_SERVICE_ACCOUNTS.md`.

## v6.0.4 Performance, Scale & Load Certification

v6.0.4 added the repeatable capacity/load certification harness, 9 high-cardinality indexes and explicit CI/Pilot/Enterprise performance profiles. Packaging-container performance numbers remain non-enterprise claims; real Pilot/Enterprise certification must run on the target PostgreSQL/Redis/Qdrant topology.


## v6.0.2 Integration Hardening & Data Confidence

v6.0.2 is the second production-readiness step. It hardens real PLM/PDM/ERP/MES/QMS ingestion rather than adding another automotive business module.

- versioned integration contract with source domain, required fields and freshness SLA;
- immutable ingest-event ledger and payload-aware idempotency;
- explainable schema/completeness/freshness/identity/provenance confidence;
- quarantine/DLQ with explicit Engineering-Admin replay;
- immutable quarantine bytes and revalidation before replay;
- structured `record_mode` for MES/QMS/ERP JSON records;
- new `mes_rest` and `qms_rest` connector types;
- Prometheus integration confidence/quarantine gauges;
- compact Admin UI quality status; no source-system ownership changes.

See `docs/INTEGRATION_HARDENING_DATA_CONFIDENCE.md` and `docs/INTEGRATION_HARDENING_PILOT_ACCEPTANCE.md`.


## v6.0.1 Production Hardening Foundation

v6.0.1 does not add another engineering domain. It hardens the v6.0 operating system for a real pilot:

- separate liveness/readiness probes with dependency-safe output;
- PostgreSQL advisory lock for startup schema work plus explicit schema marker;
- worker-specific Celery healthcheck (the worker no longer inherits the API HTTP probe);
- privacy-minimized request IDs/structured operational request logs;
- Prometheus readiness/dependency gauges;
- checksum-verified PostgreSQL + evidence storage + Qdrant backup;
- guarded restore workflow with pre-restore safety backup and readiness validation;
- production operations and DR runbooks.

Operational commands:

```bash
make health
make backup
MGC_RESTORE_CONFIRM=RESTORE make restore BACKUP=/approved/path/to/backup
make dr-preflight
```

The backup intentionally excludes `.env`/secrets, model weights and container images; those remain under corporate secret/artifact-management policy.

## v6.0 Engineering Intelligence Operating System

v6.0 is the architectural consolidation release. It does not replace the v5.0–v5.8 domain engines; it provides one role-focused operating layer across them.

- Role-based Decision Cockpit for Engineering, Manufacturing, Quality, Supplier, Program, Field and Leadership views.
- Unified Action Inbox derived from controlled Digital Thread, Change, Program, Configuration, Build/Launch, Series and Field evidence.
- Decision Queue for items that require explicit human review/approval.
- Cross-domain Engineering Workflow Cases with deterministic stage progression and auditable evidence.
- Role selection is a UI/work focus only and **never** grants additional access. Project / Manufacturing Area / Document ACL remain authoritative.
- CPU-only deterministic core; local LLM remains optional for explanation, never approval.

Primary API:

```text
GET  /api/v1/projects/{project_code}/engineering-os
POST /api/v1/projects/{project_code}/engineering-os/ask
POST /api/v1/projects/{project_code}/engineering-os/workflows
PATCH /api/v1/projects/{project_code}/engineering-os/workflows/{workflow_id}
```

See `docs/ENGINEERING_INTELLIGENCE_OS.md`.

## v5.8 Field Reliability & Product Lifecycle Intelligence

- Field/warranty failure intelligence linked to VIN genealogy, part revision, supplier and engineering history.
- Deterministic reliability metrics plus two-parameter Weibull with grouped right-censored exposure; insufficient evidence fails explicitly.
- Design FMEA feedback, validation coverage gaps and revision-level observed field effectiveness.
- VIN-level TSB / field-containment applicability without replacing DMS/Warranty systems.
- Campaign/recall assessment is advisory only and always requires Quality/Engineering/Legal/Homologation/Management authority.
- Field investigations feed Engineering Knowledge Memory only as controlled evidence; causal claims remain human-confirmed.

## v5.7 Series Quality & Manufacturing Intelligence

- series-production health from imported MES/QMS/SPC observation buckets;
- Cp/Cpk/Pp/Ppk snapshots with explainable capability bands and degradation trend;
- deterministic two-window quality change-point signals with `correlation_only=true` and `causal_claim=false`;
- VIN suspect-population builder from actual build genealogy, supplier lot, revision, plant, variant and date;
- human-controlled containment cases and inspection progress;
- PFMEA ↔ Control Plan ↔ actual series-defect review loop;
- control effectiveness / escape-rate indicators;
- supplier-lot, shift and station investigation signals without operator/supplier blame;
- tooling/calibration signals linked to capability and process assets;
- field/warranty feedback and advisory Cost of Poor Quality;
- field cases feed ACL-safe Engineering Knowledge Memory;
- deterministic CPU-only Ask Series Intelligence and one compact Project Workspace card.

See `docs/SERIES_QUALITY_MANUFACTURING_INTELLIGENCE.md` and `docs/SERIES_QUALITY_PILOT_ACCEPTANCE.md`.

## v5.6 Vehicle Build & Launch Intelligence

- Pilot Build / pre-series / Safe Launch build context at VIN/build level;
- part/revision/supplier/lot/serial genealogy;
- exact-variant genealogy coverage and missing-part detection;
- links to existing Process Defect / 8D / ECO without duplicating QMS records;
- recurrence clusters by failure mode, part, supplier and variant;
- deterministic Safe Launch exit criteria with mandatory human exit approval;
- Build → Defect → 8D/ECO → later-build feedback paths with `causal_claim=false`;
- strict fail-closed Project/Area/Document ACL;
- CPU-only deterministic core and one compact Project Workspace card.

See `docs/VEHICLE_BUILD_LAUNCH_INTELLIGENCE.md` and `docs/VEHICLE_BUILD_LAUNCH_PILOT_ACCEPTANCE.md`.

## v5.5 Configuration & Release Assurance

- deterministic EBOM ↔ MBOM reconciliation;
- explicit 150% → 100% vehicle configuration; UNKNOWN applicability is never silently included;
- effectivity by variant / plant / market / supplier / VIN / serial / date;
- Change Cut-In readiness with old-stock disposition, logistics and PPAP gates;
- AS-DESIGNED → AS-PLANNED → AS-BUILT consistency and approved-deviation handling;
- supersession / interchangeability / retrofit / stock-use engineering rules;
- Buildability + human-only Manufacturing Handover;
- SHA-256 Configuration Release Package and `mgc-release-baseline-v3`;
- release drift across engineering + MBOM/effectivity/cut-in/supersession evidence;
- read-only cross-system consistency, Variant/Plant Matrix and deterministic CPU-only Ask Configuration;
- one compact Project Workspace card; no automatic PLM/ERP/MES/warehouse writes and no automatic release.

See `docs/CONFIGURATION_RELEASE_ASSURANCE.md` and `docs/CONFIGURATION_RELEASE_ASSURANCE_PILOT_ACCEPTANCE.md`.

## v5.5 Configuration & Release Assurance

- EBOM ↔ MBOM reconciliation with added/missing/revision/quantity/unit/supplier mismatch detection; MBOM remains an imported/shadow view of the authoritative manufacturing source.
- 150% product structure → explicit 100% Vehicle Variant configuration; UNKNOWN applicability is never silently treated as included.
- Controlled effectivity by variant, plant, supplier, VIN/serial and effective date windows.
- Change Cut-In readiness with old-stock disposition, logistics confirmation and approved PPAP checks for the new revision.
- AS-DESIGNED → AS-PLANNED → AS-BUILT assurance with approved deviation handling and VIN-scoped effectivity resolution.
- Buildability and Engineering → Manufacturing Handover gate with explainable blockers/review items.
- Configuration Release Package v2 with SHA-256 fingerprint over engineering + manufacturing/configuration evidence.
- Release Baseline schema v3 freezes MBOM, effectivity, cut-in and supersession state so post-release manufacturing-configuration drift is detectable.
- Cross-system consistency, Variant/Plant Matrix, supersession rules and deterministic Ask Configuration.
- CPU-only deterministic core, strict Project/Area/Document ACL, no automatic release, stock transaction, ERP/MES/PLM write-back or machine control.

See `docs/CONFIGURATION_RELEASE_ASSURANCE.md` and `docs/CONFIGURATION_RELEASE_PILOT_ACCEPTANCE.md`.

## v5.4 Engineering Program Control / Launch Command Center

- Deterministic Engineering Program Control on top of existing milestones, V&V, PPAP, ECR/ECO, launch, risk and quality evidence.
- Controlled milestone dependency graph with cycle prevention and explicit lag/criticality.
- Explainable critical dependency chain based on due-date/dependency slack; not falsely labelled formal CPM without authoritative planning durations.
- Design Freeze / Release / SOP gate forecast with days-to-gate, propagated slip and blocker reasons.
- Engineering maturity by Product, Program, V&V, Manufacturing/Launch, Supplier/PPAP, Changes, Quality and Risk.
- Manufacturing-area maturity heatmap for assembly, welding, paint, components, logistics and other configured areas.
- Read-only milestone-slip what-if simulation; no schedule dates are silently rewritten.
- Compact Engineering Command Brief and top-action queue; no new global navigation item.
- Program Control is advisory and does not replace PLM, ERP, MES, QMS or the authoritative corporate program-management system.

See `docs/PROGRAM_CONTROL.md`.

## v5.3 Closed-Loop Engineering Intelligence

- Engineering Decision Records with alternatives, rationale, expected result and human-controlled status;
- post-change Production Feedback with observed defect rate and planned-vs-actual engineering deltas;
- human-confirmed Change Effectiveness Reviews that feed Engineering Knowledge Memory;
- quantity/time-bounded Deviation / Waiver records with explicit expiry and approval provenance;
- Engineering Risk Register with initial/residual P×S×D scoring and human risk acceptance;
- deterministic Defect Root-Cause Explorer that returns investigation candidates, never an automatic causal claim;
- Supplier Quality Closed Loop across localization, PPAP, incoming quality and 8D;
- Risk-Based Validation Planner, Early Warning Signals, Release Confidence and compact Engineering Pulse;
- Project/Manufacturing Area/Document ACL remains fail-closed across all new cross-domain views;
- CPU-first deterministic core; no MES/SCADA/QMS/PLM replacement and no automatic release/waiver/root-cause approval.

See `docs/CLOSED_LOOP_ENGINEERING_INTELLIGENCE.md` and `docs/CLOSED_LOOP_PILOT_ACCEPTANCE.md`.

## v5.2 Engineering Knowledge Memory

- historical analogue search across ECR/ECO, 8D, process defects, Design Review and validation issues;
- deterministic CPU-only similarity with explicit `why_similar`;
- project or ACL-safe accessible-portfolio scope;
- recurrence signals for new/open engineering problems;
- human-curated Lessons Learned with draft → validated → archived governance;
- whole-case fail-closed behavior when any linked evidence is hidden;
- Ask Engineering Memory works without GPU/LLM;
- no new global navigation and no automatic engineering/release decision.

See `docs/ENGINEERING_KNOWLEDGE_MEMORY.md` and `docs/KNOWLEDGE_MEMORY_PILOT_ACCEPTANCE.md`.

## v5.1 Engineering Change Intelligence

- Change Impact Simulator: revision/material/thickness/geometry/supplier/quantity/cost what-if analysis without modifying engineering records;
- automatic evidence freshness states: CURRENT / REVIEW_REQUIRED / STALE / MISSING / UNKNOWN;
- Engineering Action Queue from stale evidence, trace gaps and High/Critical open changes;
- Variant Impact Matrix and workshop/manufacturing-area impact;
- explicit Traceability Coverage by drawing/CAD/requirements/process/supplier/PPAP/release;
- Full Digital Thread Diff across BOM/documents/V&V/supplier/PPAP/process/cost/architecture/interfaces/configuration;
- Ask Digital Thread combines deterministic graph facts with local document RAG;
- no new global navigation, CPU-first deterministic core, no automatic approval/release.

See `docs/ENGINEERING_CHANGE_INTELLIGENCE.md` and `docs/CHANGE_INTELLIGENCE_PILOT_ACCEPTANCE.md`.

## v5.0 Engineering Digital Thread Explorer

- one deterministic cross-domain thread across Part/BOM, documents/CAD, requirements/V&V, manufacturing process, supplier/localization, engineering cost, ECR/ECO, quality issues, vehicle architecture/interfaces, variants and immutable release baselines;
- Project Thread plus focused Part Impact Thread with depth 1–5;
- explainable impact routes and explicit trace gaps instead of AI-invented relationships;
- fail-closed reuse of Project / Manufacturing Area / Document ACL;
- advisory coverage metric that does **not** alter technical Release Readiness;
- compact Project Workspace card, no new global navigation item;
- CPU-first: the Explorer uses local SQL/in-memory graph construction and does not require LLM/VLM or GPU.

See `docs/ENGINEERING_DIGITAL_THREAD_EXPLORER.md` and `docs/DIGITAL_THREAD_PILOT_ACCEPTANCE.md`.

## v4.6 Cost & Engineering Economics

- engineering cost baselines: current / target / change / localization / scenario;
- deterministic part-cost breakdown from mass, material price, scrap, conversion, logistics, packaging and tooling amortization;
- supplier quotation registry with validity/evidence;
- target-vs-current variance and annualized impact;
- ECR/ECO cost scenarios linked to engineering changes;
- Cost Evidence Pack snapshot;
- advisory-only governance: ERP/Finance remains financial system of record and the module does not approve sourcing/investment/release decisions.


## Supplier & Localization Engineering v4.5

Project Workspace includes one compact **Поставщики и локализация** card. Localization percentage is an informational KPI and never grants supplier readiness by itself. The new readiness layer links technical package/RFQ/nomination/tooling/capacity to existing PPAP, Run@Rate, incoming quality and 8D evidence. High/critical incoming supplier issues without 8D and defect rates above configured limits create blockers. A Supplier Localization Evidence Pack freezes the readiness snapshot for review/audit.

See `docs/SUPPLIER_LOCALIZATION_ENGINEERING.md`.

## Requirements & Verification Matrix v4.4

Project Workspace now includes one compact **Требования и подтверждение** card. It links OEM/regulatory/customer/internal requirements to system/function, visible parts, Special Characteristics, source documents, DV/PV/Run@Rate/inspection evidence and ECR/ECO. A verification marked `passed` counts only when visible evidence exists; changing the requirement after verification marks the prior evidence as stale. The matrix is traceability/evidence infrastructure, **not automatic compliance certification**.

See `docs/REQUIREMENTS_VERIFICATION_MATRIX.md`.

## Launch & Plant Readiness v4.3

- one compact **Готовность к SOP** card inside Project Workspace;
- tooling/equipment, supplier/PPAP, capacity/Run@Rate, pilot build, DV/PV, packaging/logistics, people/training and Safe Launch gates;
- reuses Process Digital Thread assets, PPAP, 8D and ECR/ECO instead of duplicating facts;
- Run@Rate captures target vs actual rate and exposes capacity mismatch as a launch blocker;
- launch score is advisory only: `human_sop_approval_required=true`;
- no PLC/MES/SCADA write controls are introduced.

## Process Digital Thread v4.2

Project Workspace now includes one compact **Производственный процесс** card that connects manufacturing area → line → station → operation → equipment/tooling → process parameter → Special Characteristic → PFMEA → Control Plan → defect/8D. PFMEA and Control Plan items can reference a stable `process_operation_id`, so process-impact analysis no longer depends on free-text step names.

The process layer is engineering/advisory only: it does **not** act as MES/SCADA and never sends commands to machines or PLCs. Process gaps (missing work instruction/PFMEA/Control Plan, overdue gauge calibration, missing reaction plan, high/critical defects without 8D) feed the advisory Project Readiness gate. The aggregate “All zones” view still enforces each manufacturing-area ACL and document ACL.

See `docs/PROCESS_DIGITAL_THREAD.md`.

## Automotive Manufacturing Workspace v4.0

## Automotive Quality & Industrialization v4.1

Project Workspace now includes a compact, area-aware quality layer: APQP deliverables, Special Characteristics, PFMEA, Control Plan (including Safe Launch phase), PPAP evidence/submission tracking, and 8D problem solving. Core Tools gaps are linked and feed the advisory project quality gate. The implementation stores an open data model and does not embed proprietary AIAG/VDA forms or rating tables; customer-specific requirements must be configured by the organization.


The project workspace is now automotive-aware. Each engineering project can be viewed by manufacturing zone without creating separate applications or overloaded dashboards. Built-in zones include **R&D / Product Engineering, Stamping, Body/Welding, Paint, Assembly, Components, Logistics, Quality, Manufacturing Engineering and Testing/Validation**.

The selected zone scopes project data, documents, parts, checks and AI retrieval. Project-common documents remain available as shared evidence where appropriate. Each zone also exposes a short automotive review focus (for example welding geometry/fixtures, paint/coating requirements, assembly interfaces, logistics packaging/material flow). These focus items are advisory checklists, not automatic approvals.

The UI remains intentionally compact: one global **Zone** selector plus one project-level zone switch. IT/admin settings stay outside the engineer workflow.

See `docs/AUTOMOTIVE_MANUFACTURING_WORKSPACE.md`. Existing Project Workspace and ECR/ECO capabilities remain available.

## Fast build — no manual Python/npm package installation

From the project root:

```bash
docker compose build
```

This command now builds the API/worker, frontend and gateway using correct Docker build contexts. Python, npm and required Linux runtime packages are installed inside the images.

After one-time corporate `.env`/SSO/model/image-pin configuration, build and start the production stack with one operator command:

```bash
make start
```

or:

```bash
./START.sh
```

See `docs/ONE_COMMAND_BUILD.md`.

## Engineering Compute Manager v3.7

Heavy Design Review jobs now run through protected asynchronous `ComputeJob` records and prioritized Celery queues. The UI remains usable while the review runs; background synchronization has lower priority. Job results are visible only to the engineer who started them or an engineering administrator. See `docs/COMPUTE_MANAGER.md`.

## Docker build and launch

The application images are **built on a connected staging/build workstation**, then exported into the air-gap bundle. The offline target server does not need internet access and does not build Python/npm dependencies from the public internet.

### 1. Initial application-image build (connected build workstation)

```bash
cp .env.airgap.example .env
make build
```

Equivalent Docker Compose command:

```bash
docker compose \
  -f docker-compose.airgap.yml \
  -f docker-compose.build.yml \
  build api frontend gateway webhook-edge
```

For a clean rebuild:

```bash
make build-no-cache
```

The resulting local images are:

```text
mgc-engineering-ai-api:5.5.0-local
mgc-engineering-ai-frontend:5.5.0-local
mgc-engineering-ai-gateway:5.5.0-local
mgc-engineering-ai-webhook-edge:5.5.0-local
```

`worker` uses the same API image, so it does not require a separate Docker build.

### 2. Run the stack locally after the images and model weights exist

```bash
make up
```

Runtime-aware launch:

```bash
make up       # auto GPU -> CPU fallback
make cpu      # force CPU / llama.cpp
make gpu      # force NVIDIA / vLLM
```

Check status:

```bash
make ps
```

Logs:

```bash
make logs
```

### 3. Build a transferable air-gap bundle

On the connected staging workstation, after preparing the approved model weights:

```bash
make bundle
```

This builds the application images, verifies the model manifest, refuses floating/placeholder air-gap image references, pulls/uses the approved pinned infrastructure images, and writes `docker-images.tar` plus the model files and checksums to `dist/mgc-airgap-bundle/`.

### 4. Offline target server

After transfer through the approved corporate media path:

```bash
cd mgc-airgap-bundle
./project/scripts/airgap_import.sh .
cd project
cp .env.airgap.example .env
# edit secrets and replace the approved-image placeholders in .env
make up
make acceptance
```

**Important:** `make build` is intentionally a staging-workstation operation because the backend Dockerfile installs apt/pip dependencies and the frontend Dockerfile installs npm dependencies. A truly air-gapped target should receive prebuilt Docker images via the bundle rather than trying to resolve public package repositories.

**Fully local / air-gapped Engineering AI platform for automotive R&D and manufacturing engineering.**

**v4.8 adds Vehicle Variant & Configuration Management:** market / model year / body / engine / transmission / trim variants, explicit included/excluded applicability, UNKNOWN-safe impact analysis and ECR/ECO variant scope without replacing PLM/PDM authority.

v3.7 provides a local **dual inference runtime**. NVIDIA servers use vLLM; CPU-only servers use llama.cpp + GGUF. Both modes use local embeddings/reranker and require no public AI API at runtime.


## Locality guarantee

In `AIR_GAPPED_MODE=true`:

- LLM/VLM endpoint defaults to `http://model-server:8000/v1` inside Docker;
- embedding model must be a local directory (`/models/embeddings`);
- reranker must be a local directory (`/models/reranker`);
- Hugging Face/Transformers offline mode is forced;
- `docker-compose.airgap.yml` uses `pull_policy: never`;
- the model server has no host-published inference port;
- backend/model traffic uses an internal Docker network; only the reverse-proxy edge joins a host-facing bridge;
- `/api/v1/local-ai/health` reports the local inference state.

The model weights themselves are intentionally **not embedded in this ZIP**: a practical 8B multimodal model is many gigabytes and must pass your company's license/security approval. `scripts/prepare_models.py` and `scripts/prepare_airgap_bundle.sh` produce the complete offline transfer package on an approved connected staging machine.

## Default local AI stack

```text
                  CORPORATE ENGINEER
                             |
                  Corporate OIDC / SSO
                             |
               Engineer group gate :3000
                             |
                    MGC Engineering AI
                             |
       +---------------------+--------------------+
       |                     |                    |
       v                     v                    v
 vLLM (GPU) OR         Local BGE-M3       Local reranker
 llama.cpp (CPU)         embeddings          CrossEncoder
 local model weights     /models/embeddings /models/reranker
       |                     |                    |
       +---------------------+--------------------+
                             |
                             X
                      PUBLIC INTERNET
                       (not required)
```

GPU mode uses a vLLM-compatible multimodal model. CPU Standard uses a quantized GGUF through llama.cpp and keeps deterministic drawing/OCR/CAD analysis enabled; optional CPU Vision is available as a separate profile.

## Start on an isolated server

After importing the offline model and Docker image bundle:

```bash
cp .env.airgap.example .env
# replace passwords/model key; configure corporate OIDC and engineering groups

make up
make acceptance
```

Open:

```text
http://<configured-private-IP>:3000
```

Local AI status:

```text
GET /api/v1/local-ai/health
```

Expected core fields:

```json
{
  "air_gapped_mode": true,
  "runtime_downloads_allowed": false,
  "ready": true
}
```

## Preparing the offline package

Run these steps on a separate machine that is allowed to access model/container repositories:

```bash
python -m venv .venv
. .venv/bin/activate
pip install -r scripts/requirements-airgap-prep.txt
# CPU-only target:
make prepare-cpu
make bundle-cpu

# NVIDIA target:
make prepare-models
make bundle-gpu
```

The preparation script records exact model repository revisions and SHA-256 hashes of all model files. The bundle script exports all Docker images into `docker-images.tar` and creates checksums for transfer.

See [docs/AIR_GAP_DEPLOYMENT.md](docs/AIR_GAP_DEPLOYMENT.md).


## Real Integration Pilot & Data Reconciliation v6.0.3

v6.0.3 adds a controlled, read-only reconciliation layer over the v6.0.2 integration contracts. It compares PLM/PDM EBOM against ERP MBOM, MES VIN genealogy against provable released configuration, and QMS defects against canonical Part/VIN/Supplier entities. Exact identifiers need no alias row; non-canonical aliases require an explicit administrator-confirmed mapping, and mappings become stale when their source object fingerprint changes.

The reconciliation cockpit also reports mapping coverage, stale/unmatched entities, freshness/sync SLO, quarantine backlog and explicit source-of-truth conflicts. `READY_FOR_CONTROLLED_PILOT` is fail-closed and still requires human go-live approval. MGC never writes reconciliation corrections back to PLM/ERP/MES/QMS. See `docs/INTEGRATION_PILOT_RECONCILIATION.md`.

## Engineering Traceability / Release Baseline v4.9

v4.9 adds immutable Design Freeze / Release / SOP snapshots and deterministic BOM version comparison. A baseline freezes source document SHA-256 values, BOM, part revisions, requirements/V&V, PPAP/supplier state, Design Review and ECR/ECO state. Vehicle-variant UNKNOWN applicability remains explicit and prevents a clean release-candidate indication. The UI adds one compact Project Workspace card plus a Part-level BOM compare card; no new global navigation item. See `docs/RELEASE_BASELINE_BOM_COMPARE.md`.

## CPU/GPU Dual Runtime v3.7

The application can now run without a GPU. `make up` auto-selects the available runtime; `make cpu` and `make gpu` force a mode. CPU inference is provided by llama.cpp with a local GGUF model through the same OpenAI-compatible API used by the application. CPU Vision is optional via `make cpu-vision`. See `docs/CPU_RUNTIME.md`.

## Engineer-only access + Drawing Activity Timeline v3.7

v3.7 makes the production service engineering-only. The only user-facing production entry is the OIDC/SSO proxy; the base gateway, API and model server have no host-published ports. Both the edge proxy and FastAPI require an approved engineering group. Shared API-key human access is rejected in production by default. See `docs/ENGINEER_ONLY_ACCESS.md` and `docs/SSO.md`.

Every drawing/document now has a **Drawing Activity Timeline** recording who opened it, asked AI about it, parsed it, linked it to 3D, ran VLM/similarity/CAD conversion/Design Review, changed an issue, or added an engineering note. Events are append-only through the application and use a SHA-256 chain plus a separate per-document head/count anchor so row edits and tail deletion are detectable. See `docs/DRAWING_ACTIVITY_HISTORY.md`.

The **Full Design Review** action now produces a simple risk score, evidence checklist, findings and next actions using CAD, drawing, BOM, revision comparison, Drawing ↔ 3D coverage and validation/VLM signals.

## Native CAD + container hardening v3.4

v3.4 adds first-class native CAD routing for **КОМПАС-3D** (`M3D/A3D/T3D/CDW/FRW/SPW/KDW`) and **T-FLEX CAD** (`GRB`). Native source bytes remain immutable; an approved Windows gateway using the installed vendor SDK/API creates STEP/PDF/DXF derivatives with independent hashes and provenance. The default user action is simply **Подготовить для анализа**; vendor/target selection is automatic when a matching gateway is registered. See `docs/KOMPAS_TFLEX_INTEGRATION.md`.

Container hardening adds non-root runtime users, read-only root filesystems in Compose, `no-new-privileges`, dropped Linux capabilities, `tmpfs` for writable runtime paths, health checks, smaller multi-stage runtime images and removal of setuid/setgid permissions from MGC-owned images. `scripts/docker_security_preflight.py` performs a source-level Dockle/CIS-aligned preflight and `scripts/dockle_scan.sh` runs real Dockle scans against built images on a Docker host. See `docs/DOCKLE_SECURITY.md`.

## Engineering Vision / CAD Intelligence v3.3

v3.3 keeps the v3.2 drawing/CAD extraction stack and adds a deterministic **Drawing ↔ CAD Linker**. Coordinate-backed drawing dimensions can now be matched to addressable STEP/OCCT B-Rep feature candidates (`face:NNNN`) using exact geometry values. Repeated equal-size features stay explicitly ambiguous until semantic PMI or spatial view mapping can disambiguate them.

The default frontend is also redesigned for normal engineers: **Главная → Спросить ИИ → Детали → Документы → Проверки**. Infrastructure terminology and raw metadata are moved into expert/IT sections. See `docs/DRAWING_CAD_LINKING.md` and `docs/USER_GUIDE.md`.

Demo assets include `samples/8450012345_REV_D_engineering_drawing.pdf` (vector engineering drawing) and `samples/8450012345_REV_D_bracket_profile.dxf` for immediate parser checks.

## Engineering capabilities retained

- PDF/DOCX/XLSX/PPTX/image ingestion via Docling/OCR pipeline;
- STEP/STP deterministic CAD analysis through OCCT/CadQuery;
- native CAD gateway contract including КОМПАС-3D, T-FLEX CAD and extensibility for CATIA/NX/Creo/JT/SOLIDWORKS;
- hybrid dense + BM25 retrieval in Qdrant;
- local BGE-M3 embeddings;
- local CrossEncoder reranking;
- evidence-first Engineering Copilot;
- drawing vision through the local multimodal model;
- Part 360 and revision comparison;
- BOM relationships and validation issues;
- Design Review, Change Impact and Evidence Pack workflows;
- PLM/PDM/ERP/network-share integration fabric;
- engineer-only OIDC/SSO gate with backend group enforcement;
- immutable source evidence/provenance controls and tamper-evident drawing activity history;
- Neo4j GraphRAG and MinIO optional modules.

## Files added for local AI

```text
docker-compose.airgap.yml
.env.airgap.example
models/README.md
scripts/prepare_models.py
scripts/verify_model_manifest.py
scripts/prepare_airgap_bundle.sh
scripts/airgap_import.sh
scripts/airgap_acceptance.sh
docs/AIR_GAP_DEPLOYMENT.md
docs/LOCAL_MODEL_GUIDE.md
docs/IT_LOCAL_AI_ACCEPTANCE.md
```

## Important distinction

This project does not train a foundation model from scratch. It runs approved open-weight models **inside the company**. Corporate documents are retrieved locally at query time and are not sent to a public model provider.

For the IT acceptance criterion, do not accept "on-prem" based only on architecture diagrams. Disable public egress and run `scripts/airgap_acceptance.sh`; then upload local evidence and generate an answer.
### v6.3.18 deployment safety
For controlled patch deployment, v6.3.18 supports an optional blue/green candidate overlay. `make blue-green-cutover` starts an internal candidate, requires repeated readiness, switches the gateway, and performs post-switch acceptance with guarded automatic rollback. `make blue-green-finalize` remains an explicit operator action after the observation/change-approval window. Ordinary `docker compose up` is unchanged.


## v6.3.26 — Operations Consolidation & `mgcctl`

Operator-facing workflows are now consolidated behind `./mgcctl`: `status`, `verify`, `deploy`, `rollback`, `backup`, `restore`, `certify`, `provenance`, and `diagnose`. Existing Makefile targets/scripts remain supported. Destructive operations require exact confirmation tokens and the CLI delegates with `shell=False`; diagnostics intentionally omit raw command output. See `OPERATIONS_CONSOLIDATION_v6.3.26.md`.
