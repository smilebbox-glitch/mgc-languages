# MGC Engineering AI Local v6.3.16 — Verification

## Release boundary

- Application: **6.3.16**
- Database schema: **6.3.13**
- DB migration: **none**
- Scope: rolling-upgrade safety, worker draining, scheduler single-leader coordination, task runtime fencing and version-skew diagnostics; automotive business-domain behavior unchanged

## Executed backend regression

Final source inventory: **463 tests in 89 test files**.

Because one monolithic pytest process in the packaging runtime can spend excessive time in third-party cleanup/lifetime hooks, final verification was split into independently completed source groups. A verification-only pytest `sessionfinish` hook emitted collected/failed/exitstatus and terminated after the completed test session; this helper is not included in application runtime.

Completed groups:

- 65 collected / 0 failed;
- 73 collected / 0 failed;
- 58 collected / 0 failed;
- 12 collected / 0 failed;
- 43 collected / 0 failed;
- 84 collected / 0 failed;
- 90 collected / 0 failed;
- 38 collected / 0 failed.

Aggregate: **463/463 PASS**, **89/89 test files**, failures **0**.

Dedicated v6.3.16 Rolling Upgrade tests: **10/10 PASS**.

## Static / architecture gates

- Rolling Upgrade & Deployment Safety: **37/37 PASS**
- Operational Resilience: **23/23 PASS**
- Data Consistency & DR: **45/45 PASS**
- Supply Chain v6.3.12 compatibility: **27/27 PASS**
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
- Bounded Context ownership: **21/21 PASS**, **247 routes**
- Legacy API contract: **181/181 method/path contracts preserved**

## Security / build / operations gates

- API authorization: **311 guarded human-facing routes**, 4 explicit system exceptions
- Docker static security: **38/38 PASS**
- Compose/runtime security: **108/108 PASS**
- Enterprise Security: **23/23 PASS**
- Observability: **16/16 PASS**
- Corporate Deployment: **13/13 PASS**
- Game Day: **15/15 PASS**
- UX acceptance: **9/9 PASS**
- Build preflight: **PASS**; plain `docker compose build` remains supported
- Python `compileall`: **PASS**
- shell `bash -n`: **PASS**
- Compose YAML parse: **15/15 PASS**
- deterministic source secret scan: **0 committed secret candidates**

## v6.3.16 invariants verified

- new task publications carry app/schema/profile compatibility metadata;
- worker runtime guard executes before the task body;
- schema mismatch is always incompatible;
- same major/minor and maximum patch skew of 1 is required by default;
- `6.3.15/6.3.13` is accepted by v6.3.16 transition policy;
- `6.3.14/6.3.13` is rejected because patch skew exceeds the window;
- legacy task envelopes are an explicit temporary transition policy, not an implicit permanent bypass;
- workers stop queue consumption before waiting for active jobs to drain;
- normal rollout contains no SIGKILL/`docker compose kill` path;
- Celery Beat uses a PostgreSQL advisory single-leader lock;
- loss of the lock-owning DB session terminates the scheduler fail-closed;
- component registry is explicitly ephemeral/non-authoritative;
- known incompatible component skew blocks readiness;
- component-registry/Redis outage alone does not remove Core readiness;
- rollout script upgrades workers before Beat and API;
- database schema remains 6.3.13.

## Supply-chain status

- generated declared-component CycloneDX SBOM: **37 components**;
- BUILD_INPUTS provenance: **50/50 build-control inputs verified**;
- strict production status: **CONDITIONAL**, not PASS/GO.

The packaging environment intentionally does not fabricate missing corporate `package-lock.json`/npm cache, hashed Python wheelhouses, immutable image digests, offline OS bundle or approved CVE scanner evidence. Those remain fail-closed requirements of the strict corporate build path.

## Required target-host acceptance

Before Production GO, execute at minimum:

1. real BuildKit build from approved dependencies/images;
2. source/dependency and built-image CVE/SCA scans;
3. corporate OIDC/PKI/mTLS negative tests;
4. real PostgreSQL backup/restore/PITR drill;
5. v6.3.15 → v6.3.16 rolling-upgrade rehearsal with representative active CPU/CAD/AI jobs;
6. forced worker-drain timeout test proving rollout stops without killing active work;
7. duplicate-Beat test proving only one scheduler publishes;
8. lock-session-loss test proving former Beat leader exits;
9. version-skew negative tests with intentionally incompatible worker/API versions;
10. rollback rehearsal and human change-approval evidence.

No automated check in this package authorizes production deployment.
