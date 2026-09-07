# MGC Engineering AI Local v6.3.18 — Verification

## Release boundary

- Application: **6.3.18**
- Database schema: **6.3.13**
- DB migration: **none**
- Scope: application-tier API/worker/scheduler/frontend redundancy, passive gateway failover, HA topology diagnostics and target-host failover drill tooling.
- Explicit non-claim: this release does **not** certify PostgreSQL/storage/external-load-balancer or physical-host/zone HA.

## Backend regression

Full collected inventory: **485 tests in 91 test files**.

The packaging runtime can retain process-lifetime cleanup hooks after assertions complete. The final authoritative run therefore executed all 91 test files from the repository root in four non-overlapping groups with `PYTHONPATH=backend` and an external pytest verification hook that records the completed session result without modifying release sources:

- **142/142 PASS**;
- **70/70 PASS**;
- **130/130 PASS**;
- **143/143 PASS**.

Total: **485/485 PASS**, failures **0**, errors **0**, test files covered **91/91**.

Focused HA/rolling/blue-green/support regression: **40/40 PASS** before full-suite execution.

## Static / architecture gates

- High Availability & Failover Coordination: **41/41 PASS**
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
- Human-facing API authorization: **313 guarded routes**, 4 explicit system exceptions
- Observability: **16/16 PASS**
- Corporate Deployment: **13/13 PASS**
- Game Day: **15/15 PASS**
- UX acceptance: **9/9 PASS**
- Python `compileall`: **PASS**
- Shell `bash -n`: **PASS**
- Compose YAML parse: **17/17 PASS**
- deterministic source secret scan: **0 committed secret candidates**
- declared-component CycloneDX SBOM: **37 components**
- BUILD_INPUTS provenance: **61/61 controlled inputs verified**

## HA invariants verified in source/backend tests

- HA mode is opt-in; base Compose remains single-instance by default;
- two compatible active stable APIs satisfy API redundancy policy;
- candidate and draining APIs do not count toward stable redundancy;
- under-replication is `DEGRADED` and does not intentionally cascade the surviving API to not-ready;
- registry outage produces `UNKNOWN`, never a false HA-ready result;
- Redis component telemetry is not authoritative;
- exactly one active Beat leader is required in HA mode;
- more than one active Beat leader is `UNSAFE` split-brain risk;
- existing PostgreSQL advisory leader lock and lock-session loss termination remain in force;
- duplicate worker roles are provided for interactive/CPU/IO and optional CAD/AI capacity;
- Celery late acknowledgements/reject-on-worker-lost remain enabled;
- gateway supports bounded passive failover across two API/frontend upstreams;
- gateway does not enable `non_idempotent` retry;
- HA overlay publishes no additional host ports;
- HA replica services inherit hardened base service definitions;
- Operations endpoint and support-bundle addition remain admin/identity protected;
- Production authorization remains external/human controlled.

## Supply-chain status

`python scripts/supply_chain_preflight.py` reports **CONDITIONAL** because the packaging environment intentionally lacks approved corporate dependency locks/wheelhouses, offline OS bundle, immutable image digests and approved vulnerability scanner evidence. Existing strict-mode behavior remains fail-closed.

## Packaging integrity

- clean release payload controlled by `BUILD_MANIFEST.json`: **831 files**;
- pre-ZIP manifest verification: **831/831 PASS**;
- final ZIP contains **832 files** including `BUILD_MANIFEST.json`;
- ZIP → manifest missing files: **0**;
- unexpected payload files: **0**;
- size mismatches: **0**;
- SHA-256 payload mismatches: **0**;
- `__pycache__`, `.pytest_cache`, `*.pyc` artifacts in final ZIP: **0**;
- `unzip -t`: **PASS**.

## Not executed / mandatory target-host gates

Docker CLI/daemon is absent in this packaging environment. Therefore this verification does **not** claim completion of:

- live dual-API container execution;
- live Nginx upstream balancing/failover under real Docker networking;
- forced primary API loss and traffic continuity measurement;
- worker process loss and real Celery task redelivery timing;
- Beat leader loss followed by live standby takeover;
- network partition/split-brain fault injection;
- PostgreSQL HA/failover;
- physical shared-evidence-storage HA;
- external load-balancer/entrypoint HA;
- multi-host/multi-zone failover;
- RTO/RPO/SLO certification;
- corporate OIDC/PKI acceptance under failover;
- real BuildKit image build and CVE/SCA/image scanning.

These remain mandatory corporate target-host/infrastructure acceptance gates. `production_authorized=false` remains an external human decision.
