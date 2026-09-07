# MGC Engineering AI Local v6.3.10 — Verification

## Executed regression

- Read-model/cache tests: **8/8 PASS**.
- Primary affected regression (Object 360, Project Workspace, Work Instructions, Digital Thread, outbox, v6.3.3–v6.3.9 hardening): **97/97 PASS**.
- Integration/security/operations/BOM/change regression: **88/88 PASS**.
- Factually completed regression total: **185/185 PASS**.
- Full backend inventory collected: **414 tests**. A clean full-suite completion remains a mandatory corporate build-host gate; this packaging environment result is not represented as 414/414.

## Static / architecture gates

- Read Models & Cache: **22/22 PASS**.
- Architecture Simplification: **27/27 PASS**.
- Dependency Profiles: **18/18 PASS**.
- Ports & Adapters: **25/25 PASS**.
- Projection Reliability: **26/26 PASS**.
- Domain Integrity: **25/25 PASS**.
- Revision & Conflict: **28/28 PASS**.
- Approval & Release Governance: **28/28 PASS**.
- Enterprise Identity: **38/38 PASS**.
- Release Handover Safety: **46/46 PASS**.
- Data Lifecycle: **33/33 PASS**.
- Performance & Scale: **18/18 PASS**.
- Bounded Context Ownership: **21/21 PASS**.
- Legacy API Contract: **5/5 PASS**, **181/181 legacy routes preserved**.
- API authorization: **303 guarded human-facing routes**, 4 explicit system exceptions.
- Observability: **16/16 PASS**.
- Corporate Deployment: **13/13 PASS**.
- Game Day: **15/15 PASS**.
- UX acceptance: **9/9 PASS**.
- Build preflight: **PASS**.

## Supply-chain status

Dependency locking remains **WARN**, not PASS:
- `frontend/package-lock.json` is absent;
- Core/AI/Advanced Python profiles still contain declared version ranges.

Approved corporate npm mirror / resolved Python wheelhouse, image-layer/SCA/CVE scans and full Docker build remain mandatory before production certification.

## Read-model invariants verified

- PostgreSQL engineering data/evidence remains authoritative;
- `engineering_read_models` is rebuildable and contains safe aggregates only;
- Redis is optional acceleration and failure does not alter correctness;
- full-payload cache is ACL-fingerprinted;
- pending outbox invalidation bypasses cache;
- worker invalidation marks read models stale and evicts Redis acceleration keys;
- read-model rebuild does not mutate engineering-domain records;
- ETag responses are private/no-cache and conditional GET is supported.

## Required corporate-host gates

Run a real PostgreSQL 6.3.9 → 6.3.10 migration rehearsal, concurrent invalidation/load tests, Redis outage tests, full 414-test suite, Docker BuildKit images, CVE/SCA/image scans, OIDC/PKI negative tests and representative 15/30/100-engineer workload certification.

## Packaging checks

- deterministic source secret scan: **0 findings**;
- Python `compileall`: **PASS**;
- shell `bash -n`: **PASS**;
- final build manifest: **688/688 PASS** before ZIP creation;
- cache/test artifacts targeted for package: **0**.
- independent ZIP → manifest verification: **688/688 PASS**;
- unexpected files in ZIP: **0**;
- cache artifacts in ZIP: **0**;
- `unzip -t`: **PASS**.
