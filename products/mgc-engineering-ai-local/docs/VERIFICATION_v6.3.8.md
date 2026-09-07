# MGC Engineering AI Local v6.3.8 — Verification

## Executed backend regression
- v6.2.0–v6.3.8 cumulative technical regression: **83/83 PASS**.
- security/corporate/integration/change regression: **54/54 PASS**.
- Unique completed tests across those two groups: **137/137 PASS**.
- v6.3.8 lifecycle tests are included above: **8/8 PASS**.
- Current backend inventory: **399 collected tests**. A single full-suite 399/399 result is **not claimed** in this packaging environment; full clean process completion remains a corporate build-host gate.

## Static / production gates
- Data Lifecycle: **33/33 PASS**.
- Bounded Context ownership: **21/21 PASS**.
- Legacy API compatibility: **5/5 PASS**, 181/181 preserved.
- Architecture Simplification: **27/27 PASS**.
- Dependency Profiles: **18/18 PASS**.
- Ports & Adapters: **25/25 PASS**.
- Projection Reliability: **26/26 PASS**.
- Domain Integrity: **25/25 PASS**.
- Revision & Conflict: **28/28 PASS**.
- Approval & Release Governance: **28/28 PASS**.
- Enterprise Identity Policy: **38/38 PASS**.
- Release Handover Safety: **46/46 PASS**.
- Docker static security: **38/38 PASS**.
- Compose/runtime security: **100/100 PASS**.
- Enterprise Security: **23/23 PASS**.
- API authorization preflight: **299 guarded human-facing routes**, 4 explicit system exceptions.
- UX acceptance: **9/9 PASS**.
- Observability/reliability: **16/16 PASS**.
- Corporate Deployment: **13/13 PASS**.
- Operations Game Day: **15/15 PASS**.
- DR foundation: **PASS**.
- Build preflight / plain `docker compose build`: **PASS**.
- Python compileall: **PASS**.
- shell `bash -n`: **PASS**.
- Compose YAML parse: **PASS**.

## Lifecycle invariants verified
- authoritative purge default false;
- quota defaults unlimited;
- legal hold blocks purge creation/execution;
- maker cannot authorize/execute own purge;
- service account cannot be purge checker/executor;
- purge request bound to entity snapshot hash;
- released package cannot be normal purge target;
- projection purge preserves Document + PostgreSQL chunks + local evidence;
- SearchPort and GraphProjectionPort carry deletion contracts for rebuildable projections;
- lifecycle events are append-only at DB level;
- interactive upload and connector ingestion enforce configured quotas;
- lifecycle posture is surfaced in Operations/Support Bundle/Prometheus;
- no machine control or automatic PLM/MES write is introduced.

## Supply-chain limitation
Dependency lock remains **WARN** by design:
- `frontend/package-lock.json` absent;
- Core/AI/Advanced Python requirements contain declared version ranges.

Enterprise build must resolve approved npm/Python artifacts through corporate mirrors/wheelhouse and execute SCA/CVE/container-image scans.

## Packaging limitation
Frontend TypeScript transpile was not re-executed in this environment because `frontend/node_modules/typescript` is not installed. v6.3.8 does not modify frontend source. Production frontend `npm ci`/build remains a build-host gate.

## Required target-host acceptance
- full 399-test backend run with clean process termination;
- actual PostgreSQL v6.3.7 → v6.3.8 migration rehearsal and rollback/restore evidence;
- actual Docker BuildKit build for selected profile;
- SCA/CVE/image scan;
- corporate OIDC/PKI negative tests;
- quota behavior with representative evidence volumes;
- legal hold and purge UAT with Legal/Data Owner/InfoSec;
- Qdrant/Neo4j projection purge + rebuild game day;
- backup/restore after lifecycle operations.
