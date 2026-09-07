# Corporate Pilot Deployment Plan

## Phase 0 — isolated technical smoke test

Use synthetic/sample data only.

Acceptance:
- all services start;
- integration simulator health is green;
- PLM/BOM sync creates documents;
- repeated sync is idempotent;
- native-CAD placeholder -> STEP derivative workflow completes;
- Part 360 and retrieval use the derivative.

## Phase 1 — identity and one read-only source

Connect corporate OIDC and one read-only engineering folder containing non-sensitive pilot material.

Acceptance:
- real user/group identity appears in audit logs;
- unauthorized group cannot retrieve restricted evidence;
- historical bytes remain immutable when source file changes.

## Phase 2 — one PLM/PDM project

Expose a minimal gateway for one project/product family.

Acceptance:
- stable external IDs;
- revision mapping agreed with engineering;
- source checksum/version token available;
- delta sync and webhook tested;
- deletion/retirement semantics agreed (the RAG should not silently delete historical evidence).

## Phase 3 — BOM/ERP

Connect one assembly hierarchy.

Acceptance:
- parent/child quantities match authoritative ERP/PLM sample;
- change-impact traversal validated by engineers;
- access classification is correct.

## Phase 4 — licensed native CAD

Deploy approved CAD SDK gateway.

Acceptance:
- supported native formats defined;
- conversion accuracy verified on a controlled set;
- SDK/version provenance recorded;
- corrupted/unsupported files fail closed;
- source and derivative hashes remain distinct.

## Phase 5 — evaluation and go/no-go

Measure:
- retrieval Recall@K / MRR on a golden engineering question set;
- citation correctness;
- false-positive/false-negative validation rules;
- synchronization success/failure rate;
- p50/p95 ingest and query latency;
- CAD conversion success rate by format;
- ACL penetration tests;
- engineer time saved on agreed workflows.

Production rollout only after the pilot owners sign off on these metrics and information-security controls.
