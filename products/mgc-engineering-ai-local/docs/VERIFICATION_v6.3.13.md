# MGC Engineering AI Local v6.3.13 — Verification

## Release boundary

- Application: **6.3.13**
- Database schema: **6.3.13**
- Migration: additive/idempotent worker-lease/fencing/recovery ledger migration over v6.3.11
- Business scope: no new automotive decision authority; execution recovery hardening only

## Executed backend regression

The final source tree was tested using independently terminating test-file processes to avoid packaging-runtime cross-test/order coupling and long monolithic-process shutdown issues.

- collected inventory: **442 tests in 86 test files**;
- completed regression: **442/442 PASS**;
- completed test files: **86/86**;
- assertion failures: **0**;
- v6.3.13 recovery tests: **8/8 PASS**;
- focused v6.3.11 workload + v6.3.12 supply-chain compatibility set: **28/28 PASS**.

The run also exposed and fixed an old test-hygiene issue: several historical migration tests implicitly depended on another test importing the ORM model registry first. Those tests now import the registry themselves and pass in isolated processes.

## Static / architecture gates

- Execution Recovery & Job Lease Safety: **35/35 PASS**
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
- Bounded Context ownership: **21/21 PASS**, **247 routes**
- Legacy API contract: **181/181 method/path contracts preserved**

## Security / build gates

- Docker static security: **38/38 PASS**
- Compose/runtime security: **104/104 PASS**
- Enterprise Security: **23/23 PASS**
- API authorization: **309 guarded human-facing routes**, 4 explicit system exceptions
- Observability: **16/16 PASS**
- Corporate Deployment: **13/13 PASS**
- Game Day: **15/15 PASS**
- UX: **9/9 PASS**
- Supply Chain controls introduced in v6.3.12: **27/27 structural/fail-closed PASS**
- Build preflight: **PASS**; plain `docker compose build` remains supported
- Python `compileall`: **PASS**
- shell `bash -n`: **PASS**
- Compose YAML parse: **14/14 PASS**
- deterministic source secret scan: **0 committed secret candidates**

## Recovery invariants verified

- dispatch fence is persisted before broker publish;
- stale/old delivery cannot write progress, success or failure after token rotation;
- duplicate delivery cannot acquire an active worker lease;
- expired replay-safe document ingestion is fenced and can be requeued;
- design review becomes `orphaned` and is not automatically replayed;
- exact Engineering Admin confirmation is required for orphan recovery;
- exhausted retry budget enters DLQ;
- every recovery decision is recorded in PostgreSQL;
- recovery metrics are exposed without making Redis/Celery authoritative;
- no SIGKILL cancellation or automatic engineering/release authorization is introduced.

## Supply-chain status

The source package remains **CONDITIONAL**, not production-certified, until a corporate build host supplies approved immutable build artifacts. v6.3.13 retains the v6.3.12 fail-closed reproducible/offline path and regenerates current BUILD_INPUTS metadata for this source tree.

The packaging environment does not contain the approved corporate npm/Python/Debian/container mirrors, production `package-lock.json`/offline npm cache, resolved Python wheelhouses, immutable image digests, or approved Trivy/Grype-equivalent scanner. Therefore the following are **not claimed as executed PASS**:

- real Docker BuildKit image build and runtime acceptance;
- production frontend `npm ci --offline` from approved lock/cache;
- resolved Python wheelhouse installation/certification;
- source/dependency CVE acceptance with corporate policy;
- built-image CVE scan;
- real PostgreSQL 6.3.11 → 6.3.13 migration rehearsal/rollback/backup→restore proof;
- live corporate OIDC/PKI/mTLS negative tests;
- target-host 15/30/100-engineer load certification;
- production PLM/PDM/ERP/MES/QMS reconciliation;
- controlled UAT / human Production GO.

## Deployment authority

This release does not self-authorize production deployment, engineering approval, release handover, or machine control. Production GO remains a corporate human/change-management decision.

## Package integrity target

The release manifest controls **755 payload files**. `BUILD_MANIFEST.json` is intentionally excluded from its own hash inventory and is included as the 756th file in the ZIP. Cache/test bytecode artifacts and runtime SQLite databases are excluded from the package.
