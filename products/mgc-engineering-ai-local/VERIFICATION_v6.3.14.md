# MGC Engineering AI Local v6.3.14 — Verification

## Release boundary

- Application: **6.3.14**
- Database schema: **6.3.13**
- DB migration: **none**
- Scope: authoritative data consistency, disaster-recovery verification and optional PostgreSQL PITR readiness; automotive decision authority unchanged

## Executed backend regression

The final source tree was exercised using independently terminating pytest processes, avoiding monolithic packaging-runtime shutdown/order coupling.

- collected inventory: **447 tests in 87 test files**;
- completed backend regression: **447/447 PASS**;
- completed test files: **87/87**;
- failures: **0**;
- v6.3.14 Data Consistency & DR unit tests: **5/5 PASS**.

## Static / architecture gates

- Data Consistency & DR: **45/45 PASS**
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
- Execution Recovery & Job Lease Safety: **35/35 PASS**
- Supply-chain structural/fail-closed compatibility: **27/27 PASS**
- Bounded Context ownership: **21/21 PASS**, **247 routes**
- Legacy API contract: **181/181 method/path contracts preserved**

## Security / build gates

- Docker static security: **38/38 PASS**
- Compose/runtime security: **108/108 PASS**
- Enterprise Security: **23/23 PASS**
- API authorization: **309 guarded human-facing routes**, 4 explicit system exceptions
- Observability: **16/16 PASS**
- Corporate Deployment: **13/13 PASS**
- Game Day: **15/15 PASS**
- UX: **9/9 PASS**
- Build preflight: **PASS**; plain `docker compose build` remains supported
- Python `compileall`: **PASS**
- shell `bash -n`: **PASS**
- Compose YAML parse: **15/15 PASS**
- deterministic source secret scan: **0 committed secret candidates**
- CycloneDX declared-component SBOM: **37 components**

## DR invariants verified at source/unit/static level

- backup requires quiesce by default and a non-quiesced capture is explicitly non-certifiable;
- gateway and scheduler are stopped before consistency capture;
- managed compute jobs must drain to a safe boundary unless an operator deliberately chooses a weaker policy;
- every worker class (`worker`, CPU, IO, CAD, AI) is included in the quiesce set;
- authoritative consistency snapshot is produced before PostgreSQL/evidence capture;
- database logical fingerprint includes deterministic rows and PostgreSQL sequence state;
- evidence storage rejects symlinks and document paths escaping the configured root;
- controlled document existence/size/SHA-256 is checked against the evidence tree;
- Digital Thread document references and tamper-evident event chains are checked;
- restore verifies the exact database and storage fingerprints before private API/workers/gateway restart;
- mismatch is fail-closed and keeps the system in maintenance;
- optional PITR overlay requires an explicit archive target and does not expose the archive command value;
- Qdrant remains optional/rebuildable and is not promoted to engineering source of truth.

## Supply-chain status

Current `BUILD_INPUTS.json` verifies **48 controlled build inputs**. The source package remains **CONDITIONAL**, not production-authorized, because corporate immutable dependency/image artifacts are intentionally absent from the packaging environment: approved npm lock/cache, exact hashed Python locks/wheelhouses, immutable image digests, offline OS bundle/install receipt and approved CVE scanner evidence.

## Not claimed as executed here

- real Docker Engine/BuildKit image build and container runtime acceptance;
- production `npm ci --offline` from approved cache and resolved Python wheelhouse installation;
- corporate source/dependency and built-image CVE/SCA acceptance;
- real target PostgreSQL backup → restore rehearsal using representative engineering data;
- WAL archive durability/retention and point-in-time recovery to a chosen timestamp/LSN;
- measured production RPO/RTO;
- live corporate OIDC/PKI/mTLS negative tests;
- target-host 15/30/100-engineer load certification;
- production PLM/PDM/ERP/MES/QMS reconciliation;
- controlled UAT / human Production GO.

## Package integrity

The release manifest controls **773 payload files**. `BUILD_MANIFEST.json` is intentionally excluded from its own hash inventory. Test/cache bytecode and runtime databases are excluded from release packaging. The ZIP is independently rehashed against this manifest after packaging.
