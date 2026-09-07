# v6.3.30 — Production Observability & Automated Incident Evidence

- deterministic privacy-safe incident evidence over existing readiness/SLO/queue/integration/workload/HA snapshots;
- canonical SHA-256 report integrity and bounded per-signal fingerprints;
- Engineering Admin evidence/reconciliation endpoints and support-bundle `incident-evidence.json`;
- bounded Prometheus signal counts by severity only;
- periodic evidence generation with opt-in incident materialization and open-signal deduplication;
- automatic destructive recovery, automatic incident resolution and production self-authorization remain forbidden;
- application 6.3.30 / schema 6.3.13; no DB migration; adjacent rollout window 6.3.29 ↔ 6.3.30.

# v6.3.23 — Automated Release Acceptance Pipeline

- Added signed release acceptance evidence and canonical parent-hash chain.
- Added trusted human-approved baseline promotion and explicit bootstrap contract.
- Added p95/p99/error-rate/throughput/DB-pool/RTO/RPO regression gates against the approved baseline.
- Added controlled live wrapper that runs non-destructive load certification and never injects failover without separate explicit confirmation.
- Technical GO remains separate from Production Authorization.
- Database schema remains 6.3.13; no migration.

# Changelog

## 6.3.22 — Production Load Certification Harness

- added a controlled 15/30/100-concurrency target-host HTTP load harness;
- added deterministic automotive mixed workload for Object 360, BOM, Work Instructions, Digital Thread, RAG search and RAG ask;
- added warm-up exclusion, p50/p95/p99/max latency, RPS, per-operation error rate and error-budget burn;
- added DB-pool, queue-age/depth and managed-workload safety sampling during the load window;
- default certification remains read-mostly and forbids engineering business-write replay; RAG audited reads require explicit opt-in;
- credentials are supplied ephemerally via environment and raw target/project/part identifiers are not retained in evidence;
- added canonical SHA-256 load evidence, optional detached OpenSSL signing and public-key verification;
- production certification now ingests verified load evidence directly instead of trusting manually copied p95/error-rate/pool metrics;
- missing/unsigned load evidence remains CONDITIONAL; tampered/invalid evidence and failed mandatory SLO/saturation gates fail closed;
- technical GO remains separate from human Production Authorization;
- application 6.3.22; database schema remains 6.3.13; no migration.

# v6.3.21 — Production Topology Certification & SLO Enforcement

- production acceptance profiles for 15/30/100 named engineers with topology, availability, p95/error-rate, pool-headroom and RTO/RPO thresholds;
- Engineering Admin runtime certification endpoint and support-bundle evidence;
- missing live measurements are `CONDITIONAL`, failed mandatory gates are `NO_GO`;
- DB-pool saturation backpressure rejects new mutating HTTP work at the hard threshold while preserving read traffic;
- target-host evidence evaluator and human-confirmed deployment guard; technical GO never self-authorizes production;
- application 6.3.21 / schema 6.3.13, no automotive-domain migration;
- final post-hardening backend regression: 529/529 PASS across 94 test files.

# v6.3.20 — Multi-host Production Topology & External Load-Balancer Safety

- per-node `topology_node_id`, `topology_failure_domain` and role metadata in ephemeral runtime heartbeats;
- Engineering Admin multi-host topology snapshot with API/worker failure-domain spread and identity-conflict detection;
- under-replication is operational degradation and does not make surviving API instances cascade out of readiness;
- minimal unauthenticated `/api/v1/health/lb` eligibility contract exposes no dependency/internal diagnostics;
- external HAProxy reference uses active health checks with `retries 0` and no redispatch/retry-on for write safety;
- per-node `docker-compose.multihost.yml` requires explicit node/failure-domain/bind IP and shared PostgreSQL/Redis plus DB/evidence fencing;
- topology reference inventories and placement gates for 15/30/100 engineers; these are not performance certification;
- fail-closed multi-host deployment guard refuses another drain/cutover unless current topology is HEALTHY;
- disruptive host-loss drill requires explicit confirmation and external fault-injection/recovery commands;
- application 6.3.20 / database schema 6.3.13; no automotive-domain migration.

# v6.3.18 — Rolling Upgrade & Deployment Safety

- task publications carry application/schema/profile compatibility envelopes;
- workers reject incompatible producer runtimes before task side effects;
- adjacent 6.3.15/6.3.18 patch skew is allowed only with the same 6.3.13 schema;
- explicit transitional support for legacy pre-v6.3.18 queued messages;
- worker node names are role-prefixed and drain tooling stops consumers before waiting for active work to finish;
- Docker workers receive a 10-minute warm-shutdown grace period;
- Celery Beat is guarded by a PostgreSQL advisory single-leader lock and terminates if its lock-owning DB session is lost;
- API/worker/beat runtime heartbeats provide non-authoritative deployment diagnostics;
- known incompatible runtime skew blocks readiness, while registry/Redis outage alone does not block Core;
- Engineering Admin deployment-safety API, Prometheus metrics and support-bundle evidence;
- controlled Compose rolling-upgrade script updates workers before Beat/API;
- no database schema migration: application 6.3.18 / schema 6.3.13.

# v6.3.13 — Job Execution Recovery & Lease Safety

- PostgreSQL-backed worker leases for managed engineering jobs;
- per-dispatch fencing token + generation blocks late/duplicate Celery deliveries from mutating a newer job execution;
- bounded lease recovery with explicit replay-safety policy;
- document ingestion is the only initial automatic replay-safe workflow;
- design review and other decision/side-effect workflows become `orphaned` and require confirmed Engineering Admin recovery;
- auditable `compute_job_recovery_events` ledger;
- orphaned/expired-lease/recovery Prometheus metrics and Operations visibility;
- additive schema migration to 6.3.13; 181 legacy v6.2 method/path contracts remain preserved.

# v6.3.12 — Supply Chain & Reproducible Builds

- strict fail-closed reproducible/offline build mode;
- Python hash locks + verified profile wheelhouses;
- npm package-lock + offline cache enforcement;
- immutable base/runtime image digest policy;
- SHA-256 verified offline OS package bundle bound to the approved Python base image;
- strict application build network disabled after artifact preparation;
- build-input provenance manifest and OCI labels;
- source/dependency CVE gate plus built-image CVE gate for the exact produced application images;
- corporate build attestation binds SBOM, locks, OS bundle, CVE evidence and built-image IDs;
- air-gap strict-mode integration;
- no DB schema migration (schema remains 6.3.11).

## 6.3.4 — Engineering Revision & Conflict Management

- structured 409 `EDIT_CONFLICT` responses include the current authoritative record for visual comparison;
- controlled Work Instruction and Manufacturing Layout revision creation with lineage and revision snapshots;
- foreign-language WI translation approval is reset/stale on new revision and must be reviewed again;
- human-reviewed WI/layout/change diff endpoints; no automatic merge of controlled engineering content;
- write idempotency receipts for selected retry-prone WI/layout mutation flows;
- duplicate Change Approval stage rows blocked by database uniqueness and fail-closed migration checks;
- Engineering Admin integrity dashboard and conflict history;
- all 181 v6.2.0 legacy method/path contracts preserved; six bounded contexts now expose 198 routes;
- full backend regression: 369/369 PASS across 77 test files;
- application/schema version: 6.3.4.

## 6.3.3 — Database & Domain Integrity Hardening

- Optimistic `row_version` for Change Requests, Process Stations, Work Instructions and Manufacturing Layouts.
- Optional `expected_version`/`expected_layout_version` API contracts with structured HTTP 409 `EDIT_CONFLICT`.
- Critical WI/station/layout + audit writes use a shared Unit of Work.
- ECR/ECO state and hash-chained change events commit atomically.
- Fresh/legacy DB enforcement for positive BOM quantity, valid station headcount/takt and non-negative WI cycle time.
- Full backend regression: 362/362 PASS in sharded execution.
- Application/schema version: 6.3.3.

## 6.3.2 — Transaction & Projection Reliability

- PostgreSQL transactional outbox for Qdrant/Neo4j/MinIO projection requests;
- authoritative `document_search_chunks` enables deterministic semantic-index rebuild;
- idempotency keys, delivery receipts, worker leases, exponential retry, DLQ/replay and stale-event suppression;
- deterministic Qdrant point IDs and convergent Neo4j replacement projection;
- projection lag/DLQ/backlog metrics and Engineering Admin rebuild controls;
- 356/356 backend tests PASS in sharded execution; application/schema version 6.3.2.

## 6.3.1 — Ports & Adapters + Work Instruction Governance Hardening

- introduced technology-neutral Search, Graph Projection, Object Storage, AI Analysis and Translation ports;
- moved Qdrant/Neo4j/MinIO/local-model HTTP details behind runtime-selected adapters;
- refactored ingest, global RAG, BOM/WI translation and WI-RAG to dependency injection;
- Core uses deterministic lexical/no-op adapters and imports no advanced infrastructure packages;
- runtime contract exposes active adapter composition;
- approved Work Instruction revisions are immutable except explicit obsolete transition;
- reviewed foreign-language WI translations are fingerprint-bound and become `stale` after source/step edits;
- application version 6.3.1, database schema remains 6.3.0;
- all 193 API method/path contracts preserved.

## 6.3.0 — Manufacturing Work Instructions & Station Intelligence

- optional BOM translation to Russian/English/Chinese with immutable source values and translation memory;
- area-scoped Work Instructions Center for authored and partner-provided instructions;
- controlled WI lifecycle, revision, human translation review and admin approval;
- line/station/operation model extended with operator role, headcount, work content and takt;
- manufacturing layout records with station placements and uploaded source layouts;
- instruction RAG constrained to project + manufacturing area (+ optional station/operation);
- additive v6.3 schema for work instructions, translation memory, layouts and station context;
- 12 additive APIs while preserving all 181 v6.2.0 legacy method/path contracts.

## 6.2.2 — Service Dependency Decomposition

- lazy service imports per bounded context;
- lazy bounded-context router loading;
- Core/AI/Advanced Python dependency manifests;
- profile-aware Docker build envelope and fail-closed runtime/build compatibility;
- optional Qdrant/Sentence Transformers imports moved off Core startup path;
- layered-requirements SBOM/dependency-lock tooling.

## 6.2.1 — Bounded-Context Router Decomposition

- physically split 181 legacy HTTP handlers across the six v6.2 bounded contexts;
- reduced `backend/app/api/routes.py` from 3,218 lines to a 19-line compatibility facade;
- centralized route-free ACL/visibility helpers in `context_shared.py`;
- added profile-aware `context_registry.py`; Core does not mount Supplier/Field but retains deterministic Intelligence/Search through lexical capability;
- added `active_bounded_contexts` and explicit `schema_version` to the runtime contract;
- preserved database schema marker 6.2.0 and all `/api/v1` paths;
- added context ownership documentation and 21-check decomposition preflight;
- updated API/security preflights to recursively inspect the decomposed route tree.

## 6.2.0 — Architecture Simplification

- Consolidated product architecture into six bounded contexts without removing lifecycle capability.
- Added central runtime contract and Core / AI / Advanced deployment profiles.
- Made Qdrant and Neo4j optional/rebuildable runtime dependencies; Core search degrades to deterministic metadata/lexical discovery.
- Added Object 360 as the primary read-only engineering navigation surface.
- Added shared EvidenceRef, Action/Decision and Connector Envelope contracts.
- Added profile capability gate for advanced Field/Cost/Program/Neo4j/VLM surfaces.
- Simplified top navigation while keeping legacy drill-down views available.
- Updated backup semantics so PostgreSQL + evidence storage are authoritative; Qdrant snapshot is optional.
- Preserved legacy API/schema compatibility.
- Hardened profile composition: invalid profiles fail closed and feature overrides cannot widen lower profiles.
- Made Object 360 catalog profile-aware; Supplier and Field-derived evidence are omitted when the required capability is inactive.
- Replaced ad-hoc capability path checks with a declarative legacy-route capability registry and generic pre-auth 404 behavior.

# v6.1.0 — Corporate Deployment & Pilot Launch Kit

- Added deterministic reference sizing for 15/30-user controlled pilots and enterprise-reference workloads.
- Added admin-only deployment plan, network-port and launch-readiness API.
- Added default-deny firewall matrix and AD/OIDC, PLM/ERP/MES/QMS connectivity checklists.
- Added six-week 15–30 engineer rollout plan and corporate launch runbook.
- Target-host performance/runtime/security/restore evidence remains mandatory; MGC never authorizes production.

# v6.0.9 — Production Operations Acceptance & Game Days

- Evidence-backed operations game-day runs and exercises.
- Required drills for PostgreSQL, Redis, Qdrant, workers, integrations, TLS, OIDC, queue overload and backup/restore.
- Deterministic RTO/MTTR/RPO calculation and target comparison.
- Operations GO / CONDITIONAL_GO / NO_GO with rehearsal-only PRECHECK semantics.
- Critical incident/runtime-gate fail-closed policy.
- Human Go-Live board remains mandatory; MGC never injects faults or authorizes deployment.

# v6.0.8 — Observability, Reliability & Production Support

- Added dependency SLI/SLO and explicit error-budget accounting.
- Added privacy-safe operational health history with retention.
- Added bounded-cardinality HTTP, queue, integration-lag and incident Prometheus metrics.
- Added operator incident lifecycle and privacy-safe SHA-256 support bundle.
- Added observability/incident-response runbooks and preflight.
- No automotive-domain ownership change.

# v6.0.7 — UX Simplification & Pilot Feedback Closure

- Reworked Engineering OS into an automatically loaded role landing with a bounded action-first view.
- Limited the default surface to at most 5 primary actions, 3 decisions and 3 guided workflows.
- Collapsed specialist engineering modules under a single evidence/drill-down section by default.
- Added aggregate `pilot_usability_issues` lifecycle with remediation and UAT verification evidence.
- Added critical/high UX issue gates to controlled pilot evaluation.
- Added role-specific guided workflows for Engineering, Manufacturing, Quality, Supplier, Program, Field and Leadership.
- Preserved ACL, human approval and no employee-performance scoring boundaries.

# v6.0.6 — Controlled Automotive Pilot & User Acceptance

- Added controlled/synthetic pilot study records and privacy-preserving aggregate UX telemetry.
- Added explicit UAT scenario, evidence, usability and task-time KPI gates.
- Added GO / CONDITIONAL_GO / NO_GO evaluation with mandatory human go-live authority.
- Added deterministic synthetic golden automotive dataset and pilot preflight harness.
- Synthetic pilot can only produce PRECHECK_PASS/PRECHECK_FAIL and never production GO.
- Pilot APIs remain within the engineer/admin authorization preflight.

# v6.0.5 — Security & Enterprise Deployment Hardening
- Hardened production OIDC validation: HTTPS issuer/JWKS, required audience, asymmetric algorithm allowlist, bounded clock skew and generic token errors.
- Disabled production trusted-header auth by default; legacy opt-in requires an independent proxy secret.
- Added explicit CORS method/header allowlists.
- Added one-shot schema migration mode and enterprise split between `mgc_migrator` and runtime DB identities.
- Added TLS 1.2/1.3 enterprise browser edge and a separate mTLS-required machine webhook listener.
- Added Engineering-Admin security posture, redacted/hash-chained audit export and confirmed audit-retention purge.
- Added CycloneDX-style offline SBOM generator, deterministic secret scanner, dependency-lock preflight and Trivy/Grype build-host hook.
- Added enterprise threat model, PKI/deployment runbook and least-privilege service-account guidance.
- No new engineering domain, source-system ownership or automatic approval behavior.

# v6.0.4 — Performance, Scale & Load Certification
- Added CI/Pilot/Enterprise performance profiles and explicit capacity targets.
- Added 9 additive composite indexes for BOM, graph traversal, VIN genealogy, series quality and integration reconciliation paths.
- Added deterministic CI-scale synthetic benchmark with p50/p95 query timings.
- Added safe read-only HTTP load runner with p50/p95/p99, throughput and error-rate reporting.
- Added performance/capacity preflight and pilot acceptance runbooks.
- Packaging-container numbers are explicitly not production/enterprise certification.
- No domain ownership, ACL, evidence, approval or source-system write boundaries changed.

# v6.0.3 — Real Integration Pilot & Data Reconciliation
- Added Canonical Entity Mapping Registry with explicit human-confirmed aliases and source-fingerprint stale detection.
- Added read-only PLM EBOM ↔ ERP MBOM reconciliation using the existing deterministic BOM comparator.
- Added MES genealogy ↔ released configuration reconciliation at VIN/part/revision level.
- Added QMS defect linkage coverage to canonical Part/VIN/Supplier entities.
- Added source-of-truth conflict detection without automatic winner selection.
- Added integration SLO/SLA view: freshness, sync success, quarantine, mapping coverage and stale/unmatched mappings.
- Added fail-closed `READY_FOR_CONTROLLED_PILOT` gate with explicit human go-live requirement.
- Added compact v6.0.3 Data Reconciliation admin cockpit; no new global navigation item.
- Reconciliation remains read-only and never mutates source-system payloads or writes corrections back to PLM/ERP/MES/QMS.

# v6.0.2 — Integration Hardening & Data Confidence
- Added versioned integration contracts for PLM/PDM/ERP/MES/QMS/files sources.
- Added explainable data-confidence components: schema, completeness, freshness, identity and provenance.
- Added immutable `integration_ingest_events` ledger with payload SHA-256 and source revision/timestamp provenance.
- Added contract-validation quarantine/DLQ and explicit replay with revalidation.
- Added payload-digest idempotency fallback when a source has no checksum/revision/timestamp.
- Added `mes_rest`, `qms_rest` and structured JSON `record_mode`.
- Added per-object/system data-quality state and Prometheus confidence/quarantine gauges.
- Preserved source-system authority, ACL fail-closed behavior and no automatic write-back.

# v6.0.1 — Production Hardening Foundation

- Added `/health/live` and fail-closed `/health/ready`.
- Added schema-state marker and bounded PostgreSQL migration advisory lock.
- Fixed Celery worker healthcheck so it no longer uses the API HTTP probe inherited from the image.
- Added privacy-minimized request IDs and structured operational HTTP logs.
- Added Prometheus dependency/readiness metrics.
- Added checksum-verified core backup/guarded restore and DR/operations runbooks.
- Added DR preflight and hardening regression tests.
- No automotive business-domain behavior changed.

# v6.0.0 — Engineering Intelligence Operating System

- Added role-based Decision Cockpit without changing authorization scope.
- Added Unified Action Inbox across v5.0–v5.8 domain engines.
- Added human Decision Queue and deterministic command brief.
- Added auditable cross-domain Engineering Workflow Cases and five controlled workflow templates.
- Added fail-closed workflow evidence handling; mixed hidden evidence hides the workflow.
- Added Engineering OS frontend card at the top of Project Workspace; no new global navigation item.
- Retained CPU-first / air-gapped architecture and all existing engineering authority boundaries.

# v5.8.0 — Field Reliability & Product Lifecycle Intelligence

- Added field exposure, censored Weibull reliability, DFMEA feedback, validation effectiveness, TSB/field actions, VIN trace and field→Engineering Memory.
- All field clusters and campaign candidates are advisory; no automatic root-cause/recall decision.

## v5.7.0 — Series Quality & Manufacturing Intelligence
- Added series-quality observation buckets and process-capability snapshots without replacing MES/QMS/SPC authority.
- Added deterministic rate-shift/change-point signals with explicit non-causal semantics.
- Added VIN suspect-population builder from actual genealogy and supplier lot/revision/plant/variant/date filters.
- Added human-controlled containment, PFMEA↔Control Plan↔actual defect loop and control-effectiveness indicators.
- Added supplier-lot, shift/station and tooling/calibration investigation signals.
- Added field/warranty feedback, advisory COPQ and Field → Engineering Memory linkage.
- Added compact Series Intelligence workspace and deterministic CPU-only Ask Series Intelligence.
- Added additive/idempotent v5.7 schema wrapper, strict Project/Area/Document ACL fail-closed behavior and dedicated regression tests.


## v5.6.0
- Vehicle Build & Launch Intelligence for Pilot Build, pre-series and Safe Launch.
- VIN/build genealogy with part/revision/supplier/lot/serial provenance.
- Build-to-existing-defect links and recurrence clusters without duplicating QMS defects.
- Safe Launch exit criteria remain deterministic, advisory and human-approved.
- Explainable Build → Defect → 8D → ECO → later-build feedback paths with no automatic causal claim.
- Additive v5.6 schema wrapper and strict ACL fail-closed behavior.

## v5.5.0 — Configuration & Release Assurance

- Added deterministic EBOM↔MBOM reconciliation and explicit 150%→100% configuration.
- Added effectivity, Change Cut-In, AS-BUILT and part-supersession authority-shadow records.
- Added Buildability, Manufacturing Handover, Variant/Plant Matrix and Cross-System Consistency.
- Added Configuration Release Package and release-baseline v3 coverage for MBOM/effectivity/cut-in/supersession.
- Added semantic Release Drift that ignores capture timestamp but detects real configuration-authority changes.
- Added deterministic CPU-only Ask Configuration.
- Added fail-closed ACL coverage, additive/idempotent v5.5 schema wrapper and dedicated regression tests.
- Preserved PLM/PDM, ERP/manufacturing and MES authority; no automatic release, stock transaction or source-system write.

## v5.4.0 — Engineering Program Control / Launch Command Center

- Added controlled milestone dependency graph with lag/criticality and cycle prevention.
- Added deterministic target-gate forecast for Design Freeze / Release / SOP.
- Added explainable critical dependency chain and schedule-slip propagation.
- Added evidence-derived program maturity and manufacturing-area maturity.
- Added blocker forecast and Engineering Command Brief.
- Added read-only milestone slip simulation.
- Added compact v5.4 Project Workspace card with no new global navigation item.
- Added additive/idempotent v5.4 schema wrapper and dedicated regression/ACL coverage.

## v5.3.0 — Closed-Loop Engineering Intelligence
- Added Engineering Decision Records, Production Feedback, Change Effectiveness Reviews, controlled Deviations/Waivers and Engineering Risk Register.
- Added deterministic planned-vs-actual analysis, risk-based validation planning, early warnings and multi-domain Release Confidence.
- Added Defect Root-Cause Explorer with explainable investigation paths and `causal_claim=false`.
- Added Supplier Quality Closed Loop across localization, PPAP, incoming quality and 8D.
- Human-reviewed effectiveness is now reusable by Engineering Knowledge Memory as historical evidence.
- Added compact v5.3 Project Workspace card with no new global navigation item.
- Added additive/idempotent v5.3 schema wrapper and dedicated regression/security coverage.
- Kept CPU-first operation and explicit boundaries: not MES/SCADA/QMS/PLM authority; no automatic release, deviation, risk-acceptance or root-cause decision.

## v5.2.0 — Engineering Knowledge Memory
- Added ACL-safe historical case search across ECR/ECO, 8D, process defects, Design Review and validation issues.
- Added deterministic explainable similarity and recurrence detection.
- Added human-curated EngineeringLesson records with draft/validated/archived lifecycle.
- Engineering Admin validation requires explicit outcome and effectiveness.
- Added project and accessible-portfolio memory scope without permission expansion.
- Added Ask Engineering Memory and compact Project Workspace UI.
- Added additive/idempotent v5.2 schema wrapper and dedicated regression coverage.

## v5.1.0 — Engineering Change Intelligence
- Added deterministic Change Impact Simulator across Product/BOM, Design, V&V, Manufacturing, Supplier/PPAP, Cost and Release.
- Added Automatic Stale Evidence Detection with CURRENT / REVIEW_REQUIRED / STALE / MISSING / UNKNOWN states.
- Added Engineering Action Queue, Variant Impact Matrix, workshop impact and Traceability Coverage.
- Added Ask Digital Thread: deterministic graph facts + existing local RAG evidence.
- Extended immutable release snapshot to `mgc-release-baseline-v2` with process, cost, architecture and interface data.
- Extended baseline compare into Full Digital Thread Diff and advisory readiness delta.
- Kept UI compact: one collapsible card, no new global navigation item.
- No database schema migration required for v5.1.

## v5.0.0 — Engineering Digital Thread Explorer
- Unified deterministic engineering graph across product structure, documents/CAD, requirements/V&V, process, supplier/localization, cost, changes, quality, architecture/interfaces, variants and release baselines.
- Project-level overview and part-focused impact thread with depth-limited traversal.
- Explainable routes and explicit trace gaps; no LLM-inferred engineering relationships.
- ACL/evidence fail-closed behavior retained across cross-domain navigation.
- Advisory cross-domain coverage remains separate from Project/Release Readiness.
- CPU-first implementation; no GPU/LLM dependency for Explorer.
- Compact Project Workspace UI; no new primary navigation item.
- No database schema migration required for v5.0.

## v4.9.0 — Engineering Traceability / Release Baseline / BOM Compare
- Immutable Design Freeze/Release/SOP/Audit snapshots with SHA-256 fingerprints.
- Variant-aware freeze with UNKNOWN applicability kept explicit.
- Deterministic BOM A↔B comparison: added, removed, replaced-at-position, moved-position and field changes, plus cost delta when pricing is complete.
- Optional BOM supplier/cost columns retained for future comparisons.
- Baseline fail-closed authorization across every contributing source document.
- Compact Project/Part UI; no new main navigation item.

## v4.8.0 — Vehicle / System Architecture & Interface Management
- Vehicle → system → subsystem → assembly → component hierarchy.
- First-class mechanical/electrical/fluid/thermal/data/control/packaging interfaces.
- Critical-interface requirement and evidence gates.
- PASSED-without-evidence protection and stale verification detection after endpoint/interface changes.
- Part impact analysis across adjacent nodes/interfaces, requirements, ECR/ECO, supplier/localization and cost records.
- Compact Project Workspace card; no new primary navigation item.
- Engineer-only API and manufacturing-area/document ACL isolation retained.

## v4.6.0 — Cost & Engineering Economics
- Current/target/change/localization engineering cost baselines.
- Deterministic material/scrap/conversion/logistics/tooling calculations.
- Supplier quotations and validity/evidence checks.
- ECR/ECO unit and annual cost impact.
- Cost Evidence Pack and compact project/part UI.
- Economics remains advisory and separate from technical release readiness.

## v4.5.0 — Supplier & Localization Engineering
- Supplier Readiness separated from localization KPI.
- Localization item lifecycle: technical package, RFQ, nomination, tooling, capacity, PPAP and SOP.
- Reuses PPAP, Run@Rate and tooling/launch evidence already present in the project.
- Incoming quality records calculate reject/defect rates and can enforce acceptance limits.
- High/critical supplier issues without 8D become critical gaps.
- Localization Evidence Pack freezes a review/audit snapshot.
- Compact project UI card; no new main navigation item.

## v4.4.0 — Requirements & Verification Matrix

- added EngineeringRequirement and RequirementVerification digital-thread entities;
- trace OEM/regulatory/customer/internal requirements to source document, system/function, part and Special Characteristic;
- verification methods include analysis, inspection, test, review, demonstration, simulation and measurement;
- DV/PV/Run@Rate LaunchTrial and approved Design Review can act as verification evidence;
- `passed` verification requires evidence through the API;
- requirement edits invalidate older verification snapshots as stale;
- requirement gaps feed Project Readiness only after the matrix is configured;
- Project/Area/Document ACL remains authoritative in aggregate views;
- compact UI card; no new main-navigation item.

## v4.3.0 — Launch & Plant Readiness
- SOP readiness card by project/manufacturing area.
- Launch checks + Run@Rate/Pilot/DV/PV trial evidence.
- Derived supplier/PPAP, tooling/equipment, risk-closure and Safe Launch gates.
- Capacity target-vs-actual validation and launch blockers.
- Compact UI; no additional main navigation.
- 94/94 human-facing API routes guarded by engineer identity.

## v4.2.0 — Process Digital Thread
- Added automotive process hierarchy: manufacturing area → line → station → operation → equipment/tooling → process parameter.
- PFMEA and Control Plan can link to stable process operation IDs.
- Added process defects with optional 8D linkage and evidence references.
- Added process readiness gate with work-instruction, Core Tools, reaction-plan, calibration/maintenance and defect gaps.
- Added area-specific operation hints for welding, paint, assembly, stamping, logistics, quality and other automotive functions.
- Added one collapsible process card; no new global navigation pages.
- Explicitly remains advisory engineering software, not MES/SCADA; no machine-control commands.
- Hardened aggregate “All zones” workspace so area ACL cannot be bypassed through project summaries.

## v4.1.0 — Automotive Quality & Industrialization
- APQP, Special Characteristics, PFMEA, Control Plan, PPAP and 8D inside Project Workspace;
- Special Characteristic → PFMEA → Control Plan gap detection;
- quality gate integrated into advisory project readiness;
- area/document ACL-aware Core Tools data;
- compact quality card; no new global navigation pages;
- 8D completion gate and ECR/ECO linkage support;
- 80 backend tests and 81 engineer-protected human API routes.

# Changelog

## v4.0.0 — Engineering Project Workspace

- project workspaces with root assembly, milestones and project ACLs;
- explainable advisory release-readiness score across documentation, quality, changes, Design Review and milestones;
- explicit blocker list with drill-down to documents and ECR/ECO;
- assembly tree reconstructed from BOM;
- project timeline and project-level counts;
- human release approval remains mandatory; AI readiness is advisory only;
- additive/idempotent v3.8 → v3.9 project schema migration.

## v3.8.0 — Engineering Change Management

- Added engineer-only ECR/ECO workflow: Draft → Impact Review → Approval → ECO → Implementation → Implemented.
- Added automatic Change Impact persistence using revision delta, BOM parents, related entities, documents and open issues.
- Added author/reviewer/final-approver separation of duties; the author cannot approve their own change and final approver must differ from technical reviewer.
- High/Critical changes require an approved Design Review before ECO release.
- Added deterministic impact fingerprint. Final approval re-runs impact analysis and returns the ECR to impact review if documents, BOM scope, relationships or issues changed.
- Added append-only SHA-256 ChangeEvent history with separate head/count anchor.
- ECR/ECO milestones are mirrored into affected drawing/document activity history.
- Part 360 now shows ECR/ECO records for the selected part.
- Added simple UI section “Изменения” with a guided next-action workflow.
- Additive/idempotent database migration supports upgrades from existing v3.4–v3.7 pilot databases.
- Backend regression: 62 tests passed in the packaging environment.

## v3.7.0 — One-command Docker build + Engineering Compute Manager

- `docker compose build` is a first-class supported command from the repository root.
- Fixed backend/frontend Docker build-context vs. Dockerfile `COPY` mismatch.
- Docker build installs Python, npm and Linux runtime dependencies inside images; no manual package installation on the target host.
- Backend build runs `pip check` and fails on incompatible Python dependencies.
- Added `make start` / `START.sh`: build application images and start the configured CPU/GPU production stack in one operator action.
- Added build preflight that verifies contexts, Dockerfiles and required build inputs before BuildKit runs.
- Added Engineering Compute Manager queues: interactive, heavy, default and background.
- Heavy Design Review can run asynchronously through protected `ComputeJob` records.
- Async job results are visible only to their owner or an engineering administrator.
- Celery worker prefetch is limited to one job; background integration work receives lower priority.
- UI releases the global busy state immediately after a Design Review is queued and polls the result in the background.

## v3.6.0 — Engineer-Only Access + Drawing Activity Timeline + Design Review Agent

- Production entry is now corporate OIDC/SSO only; base gateway/API/model-server are not host-published.
- Added edge engineering-group gate plus independent backend OIDC group authorization.
- Shared API-key human access is disabled in production by default; explicit API-key pilot remains non-production only.
- Added separate `engineering-ai-users` and `engineering-ai-admins` roles and hid IT controls from normal engineers.
- Added `DocumentActivity` timeline recording document opens, questions, analysis, Drawing↔3D linking, visual inspection, similarity, native CAD conversion, issue status and Design Review actions.
- Added manual engineering notes: work done, review, decision, question and other.
- Added append-only application semantics plus SHA-256 hash-chain integrity verification for document history.
- Upgraded Design Review into one-click deterministic report with risk score, evidence checklist, findings and recommended actions.
- Added additive/idempotent v3.4→v3.6 DB migration for `DesignReview.report_json`.
- Added API authorization regression preflight: all 49 human-facing API routes require `get_identity`; health and HMAC webhook are explicit exceptions.
- Retained and integrated v3.4 KOMPAS-3D/T-FLEX native CAD support and container hardening.
- Final backend verification: 53 tests pass.


### Retained from v3.3

- Added deterministic drawing-dimension to STEP B-Rep candidate linking.
- Added addressable OCCT face inventory with exact cylinder radius/diameter, center, axis and bounding box.
- Fixed cylindrical/circular parameter extraction to use OCCT BRep adaptors instead of unsupported high-level radius calls.
- Added explicit `linked_unique`, `linked_multiple` and `unmatched` states; repeated equal features are never silently guessed.
- Added `/geometry-links` and `/link-geometry` document APIs and geometry links in Engineering Analysis.
- Added validation rules for missing CAD pair, unmatched dimensions and ambiguous repeated features.
- Redesigned the default UI around five user tasks: Главная, Спросить ИИ, Детали, Документы, Проверки.
- Moved platform/infrastructure details to a separate IT section; raw metadata is collapsed under expert details.
- Added responsive mobile/tablet navigation.
- Added `docs/DRAWING_CAD_LINKING.md` and `docs/USER_GUIDE.md`.
- Backend verification: 42 tests pass. Frontend TSX syntax/type shape was checked with local declaration stubs because npm packages are intentionally not vendored in the source ZIP.

## v3.2.0 — Engineering Vision / CAD Intelligence

- Added coordinate-aware vector PDF parsing before OCR, including engineering entity bounding boxes and title-block facts.
- Added conservative structured extraction for dimensions, tolerances, threads, surface finish, thickness, datums, standards and selected GD&T symbols.
- Added local VLM verification/consensus: AI observations never silently replace deterministic facts.
- Expanded STEP/STP OCCT analysis with B-Rep topology, surface/edge families, cylindrical feature candidates, normalized shape descriptors and AP242/PMI semantic signal inspection.
- Added deterministic DXF 2D vector parsing.
- Upgraded geometry similarity to a mostly scale-normalized explainable fingerprint with per-factor match scores.
- Added engineering drawing validation issues for ambiguous thickness and facts without coordinate evidence.
- Added Engineering Analysis API endpoints and Knowledge Base UI actions for Engineering parse / Vision verify.
- Added `docs/ENGINEERING_VISION.md`.
- Backend verification: 37 tests pass before packaging; final manifest records the release verification state.

## v3.1 Local / Air-Gapped

Main objective: convert Pilot v3 into a demonstrably local neural-network deployment.

### Added

- local vLLM `model-server` inside the default Compose stack;
- unified local text + drawing-vision endpoint;
- strict local embedding path `/models/embeddings`;
- strict local reranker path `/models/reranker`;
- local Docling artifacts path `/models/docling`;
- `AIR_GAPPED_MODE=true` default;
- public inference-host guard in backend code;
- `VLM_BASE_URL` separated from `LLM_BASE_URL` for future split deployments;
- `/api/v1/local-ai/health`;
- Operations UI card showing local AI readiness;
- Hugging Face/Transformers offline environment flags;
- `pull_policy: never` in air-gap Compose;
- internal Docker network for API/data/model services;
- model preparation and SHA-256 manifest tooling;
- Docker image export/import tooling for isolated networks;
- automated air-gap acceptance script;
- local AI IT acceptance checklist.

### Security changes

- air-gap mode rejects public inference endpoints unless explicitly approved;
- model-server is not published to the host;
- embeddings/reranker cannot use repository IDs in air-gap mode;
- runtime model downloads are disabled;
- Docling model artifacts are prefetched instead of downloaded during processing.

### Validation

- 30/30 backend tests pass, including new public inference-host blocking tests;
- Python compileall passes;
- Compose YAML parses successfully;
- shell scripts pass `bash -n`.

Full GPU/container end-to-end acceptance requires approved model weights and Docker/NVIDIA runtime on the target IT server; use `scripts/airgap_acceptance.sh` there.

## v3.1.1
- Added explicit Docker build overlay (`docker-compose.build.yml`).
- Added `make build`, `make build-no-cache`, `make up`, `make rebuild`, `make bundle` and status/log targets.
- Added `scripts/docker_build.sh` and `scripts/docker_rebuild_run.sh`.
- Air-gap bundle preparation now invokes the same canonical application-image build path.
- Documented connected build workstation vs. offline target server workflow.
- Bumped local application image tags to `3.1.1-local`.

## v4.0.0
- automotive manufacturing-area taxonomy and ProjectArea ACL/owner model;
- area-aware Project Workspace, documents, parts, issues, changes and RAG retrieval;
- zone-specific milestones and document classification history;
- compact global/project area selectors without expanding the main navigation;
- advisory automotive focus checklists for welding/body, paint, assembly, components, logistics, quality and related engineering zones;
- additive/idempotent v3.9 → v4.0 migration.

## v4.8.0
- Vehicle Variant & Configuration Management for automotive derivatives.
- Explicit included/excluded applicability; missing mapping is UNKNOWN and never treated as included.
- Variant impact for parts and ECR/ECO with direct and interface-derived relationships.
- Product attributes: market, model year, body style, engine, transmission, trim and supplier strategy.
- Project/readiness integration and fail-closed evidence/area ACL behavior.
- Compact Project Workspace and Part/ECR variant-impact UI.

## v6.3.15 — Operational Resilience & Self-Diagnostics
- Process-local circuit breakers for Redis/Qdrant/local AI/VLM/native CAD gateway.
- Graceful brownout: PostgreSQL/evidence Core remains usable while optional enrichment degrades.
- Qdrant lexical fallback, evidence-only RAG, deterministic drawing fallback.
- Resilience Operations API, Prometheus metrics and privacy-safe support-bundle diagnostics.
- Application 6.3.15; database schema remains 6.3.13.

## v6.3.18 — Blue/Green Cutover & Automated Rollback Safety
- Added isolated stable/candidate API/frontend deployment slots without changing default Compose topology.
- Added gateway upstream switching after consecutive candidate readiness acceptance.
- Added optional post-switch corporate synthetic/SLO probe and consecutive-failure rollback trigger.
- Added fail-closed rollback compatibility fencing for schema and patch-version skew.
- Added cutover safety Operations diagnostics and privacy-safe support-bundle evidence.
- Added explicit human-triggered finalization that reuses worker drain, singleton scheduler and task-envelope safety.
- Application 6.3.18; database schema remains 6.3.13.
