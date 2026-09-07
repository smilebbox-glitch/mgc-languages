# MGC Engineering AI Local v6.3.17 — Verification

## Release boundary

- Application: **6.3.17**
- Database schema: **6.3.13**
- DB migration: **none**
- Scope: blue/green API/frontend candidate cutover, guarded automated traffic rollback, deployment-slot diagnostics and human-triggered finalization.

## Backend regression

Full collected inventory: **473 tests in 90 test files**.

The suite was completed in independently terminating groups because the packaging Python runtime can hold process-lifetime cleanup hooks after assertions complete. Explicit pytest summaries were obtained for every group:

- 131 passed;
- 64 passed;
- 11 passed;
- 106 passed;
- 161 passed.

Total: **473/473 PASS**, failures **0**, test files covered **90/90**.

Focused rollout/support regression after additive-contract updates: **28/28 PASS**.

## Static / architecture gates

- Blue/Green Cutover & Rollback Safety: **40/40 PASS**
- Rolling Upgrade & Deployment Safety: **37/37 PASS**
- Bounded Context ownership: **21/21 PASS**, **247 routes**
- Legacy API contract: **181/181 method/path contracts preserved**
- Architecture Simplification: **27/27 PASS**
- Dependency Profiles: **18/18 PASS**
- Ports & Adapters: **25/25 PASS**
- Projection Reliability: **26/26 PASS**
- Domain Integrity: **25/25 PASS**
- Revision & Conflict: **28/28 PASS**
- Approval & Release Governance: **28/28 PASS**
- Enterprise Identity: **38/38 PASS**
- Release Handover Safety: **46/46 PASS**
- Data Lifecycle: **33/33 PASS**
- Performance & Scale: **18/18 PASS**
- Read Models & Cache: **22/22 PASS**
- Workload Isolation: **29/29 PASS**
- Job Execution Recovery: **35/35 PASS**
- Data Consistency & DR: **45/45 PASS**
- Operational Resilience: **23/23 PASS**
- Supply-chain compatibility: **27/27 PASS**

## Security / operations / build gates

- Docker static security: **38/38 PASS**
- Compose/runtime security: **108/108 PASS**
- Enterprise Security: **23/23 PASS**
- Human-facing API authorization: **312 guarded routes**, 4 explicit system exceptions
- Observability: **16/16 PASS**
- Corporate Deployment: **13/13 PASS**
- Game Day: **15/15 PASS**
- UX acceptance: **9/9 PASS**
- Python compileall: **PASS**
- Shell `bash -n`: **PASS**
- Compose YAML parse: **16/16 PASS**
- deterministic source secret scan: **0 committed secret candidates**
- declared-component CycloneDX SBOM: **37 components**
- BUILD_INPUTS provenance: **57/57 controlled inputs verified**

## Blue/green invariants verified in source/backend tests

- base deployment still routes gateway to canonical stable API/frontend by default;
- candidate API/frontend have no published host ports in the blue/green overlay;
- stable and candidate API runtime telemetry carries explicit deployment slot;
- candidate traffic switch occurs only after consecutive candidate readiness samples;
- post-switch acceptance can include a corporate SLO/synthetic command;
- consecutive post-switch failures invoke guarded rollback;
- automatic rollback requires the same database schema and bounded patch distance;
- two-patch rollback and cross-schema rollback fail closed;
- rollback leaves failed candidate isolated for diagnostics;
- finalization is explicit/human-triggered and reuses rolling-upgrade worker/scheduler/task fencing;
- traffic routing never authorizes production automatically.

## Not executed / mandatory target-host gates

The packaging environment has **no Docker CLI/daemon** (`docker: command not found`). Therefore this verification does **not** claim:

- live simultaneous stable/candidate container execution;
- real gateway cutover under user traffic;
- forced candidate failure followed by automatic rollback;
- live SLO/error-rate rollback trigger;
- rollback/finalization timing or zero-downtime SLO;
- target PostgreSQL/Redis/Qdrant failure interaction during cutover;
- corporate OIDC/PKI acceptance during mixed revisions;
- real BuildKit image build, CVE/SCA/image scanning or immutable image-digest certification.

Those are required corporate deployment-host acceptance gates. `production_authorized=false` remains an external human change-control decision.
