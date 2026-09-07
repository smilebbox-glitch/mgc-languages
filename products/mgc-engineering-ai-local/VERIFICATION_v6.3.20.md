# MGC Engineering AI Local v6.3.20 — Verification

## Release boundary

- Application: **6.3.20**
- Database schema: **6.3.13**
- DB migration: **none**
- Scope: multi-host application placement, external load-balancer health/safety and topology certification hardening; automotive business-domain behavior unchanged.

## Backend regression

The complete backend inventory was collected from the release tree with `PYTHONPATH=backend`. Because third-party lifetime hooks can retain the packaging Python process after pytest assertions finish, non-overlapping verification groups used a packaging-only `pytest_sessionfinish` hook located outside the release tree. Each accepted group emitted explicit collected/passed/failed/error/skipped counts; the hook does not modify product behavior.

- collected: **515 tests**
- test files: **93/93**
- total: **515/515 PASS**
- failures: **0**
- errors: **0**
- skipped: **0**
- v6.3.20 Multi-host Topology tests: **14/14 PASS**
- accepted group results: **129 + 129 + 36 + 93 + 60 + 68 = 515 PASS**

Two additive current-release test fixtures were corrected during verification: v6.3.17 blue/green and v6.3.16 rolling-upgrade tests still referenced the previous adjacent-patch transition window. The product compatibility policy was not widened: current transition is **6.3.19 ↔ 6.3.20** at schema **6.3.13**, while a two-patch rollback remains rejected.

## v6.3.20 multi-host topology gate

- Multi-host Production Topology static preflight: **30/30 PASS**.
- Runtime heartbeat carries stable node id, failure domain and node-role placement metadata.
- Compatible active stable API replicas are evaluated by independent failure domain.
- Required interactive/CPU/IO worker roles are evaluated by failure-domain spread.
- Candidate/draining runtimes do not count toward stable placement redundancy.
- Duplicate node identity observed in different failure domains is `UNSAFE`.
- Missing placement labels or under-replication is `DEGRADED`, not an individual API readiness cascade.
- Redis component registry remains ephemeral diagnostic evidence and never engineering truth.
- `GET /api/v1/health/lb` exposes only contract/status/eligibility/version/schema and uses local readiness as traffic eligibility.
- External HAProxy reference uses active health checks, `retries 0`, and no request redispatch/retry-on policy.
- Per-node Compose overlay requires explicit node/failure-domain/bind-IP plus shared PostgreSQL/Redis and v6.3.19 DB/evidence fencing.
- 15/30/100 topology reference inventories pass their placement policies; results explicitly set `performance_certified=false` and `production_authorized=false`.
- Deployment guard fails closed unless the current topology snapshot is `HEALTHY` with complete labels and no domain gaps/conflicts.
- Host-loss drill harness requires explicit confirmation plus operator-supplied approved fault injection/recovery commands.

## Architecture / governance gates

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
- Read Models & Cache: **22/22 PASS**.
- Workload Isolation: **29/29 PASS**.
- Job Execution Recovery: **35/35 PASS**.
- Data Consistency & DR: **45/45 PASS**.
- Operational Resilience: **23/23 PASS**.
- Rolling Upgrade: **37/37 PASS**.
- Blue/Green Cutover: **40/40 PASS**.
- Application-tier High Availability: **41/41 PASS**.
- Database & Evidence Storage HA: **45/45 PASS**.
- Bounded Context Ownership: **21/21 PASS**, **247 routes**.
- Legacy API contract: **5/5 preflight PASS; 181/181 legacy method/path contracts preserved**.
- Supply Chain v6.3.12 compatibility: **27/27 PASS**.

## Security / operations / build gates

- API authorization: **315 guarded human-facing routes**, **5 explicit system exceptions** (`/health`, `/health/live`, `/health/ready`, `/health/lb`, signed machine webhook).
- Docker static security: **38/38 PASS**.
- Compose/runtime security: **119/119 PASS**.
- Enterprise Security: **23/23 PASS**.
- Observability: **16/16 PASS**.
- Corporate Deployment: **13/13 PASS**.
- Game Day: **15/15 PASS**.
- UX acceptance: **9/9 PASS**.
- Build preflight: **PASS**; plain `docker compose build` remains supported.
- Python `compileall`: **PASS**.
- Compose YAML parse: **19/19 PASS**.
- shell `bash -n`: **28/28 PASS** including root `BUILD.sh`.
- deterministic source secret scan: **0 committed secret candidates**.
- SBOM: **37 components**.
- BUILD_INPUTS provenance inventory: **75 file inputs** (including multi-host overlay, external-LB reference, topology inventories and deployment/drill controls).

## Supply-chain status

Supply-chain status remains **CONDITIONAL**, not PASS and not Production GO. The packaging environment does not provide the approved corporate npm lock/cache, Python hashed locks/wheelhouses, immutable container image digests, offline OS package bundle, or approved source/image vulnerability scanner evidence. Those artifacts are not fabricated.

## Target-host gates not executed here

The packaging environment has no Docker CLI/daemon and no external load-balancer/host-management control plane. Therefore this release does **not** claim execution of:

- real physical/VM host loss with external LB failover;
- external LB cluster-node failure itself;
- rack/zone anti-affinity enforcement by an orchestrator;
- PostgreSQL quorum/promotion/ST​ONITH;
- evidence-storage replication/failover;
- combined DB/evidence + app-host failover chain;
- measured RPO/RTO;
- 15/30/100-engineer latency/throughput/capacity certification;
- production blue/green/rolling upgrade across multiple hosts.

These remain mandatory corporate target-host acceptance gates.

## Production authority boundary

`production_authorized=false` remains explicit. Passing source/regression/static placement gates proves the implementation and fail-closed contracts, not production authorization or measured hardware capacity.

## Final package integrity

- clean manifest-controlled payload files: **870**;
- `BUILD_MANIFEST.json` is included in the ZIP but intentionally does not hash itself;
- expected ZIP file count: **871**;
- cache/test artifacts targeted for release: **0**.

Final ZIP-to-manifest verification: **870/870 payload files PASS**; ZIP members: **871** including `BUILD_MANIFEST.json`; missing: **0**; extra: **0**; size mismatch: **0**; SHA-256 mismatch: **0**; cache/test artifacts: **0**; `unzip -t`: **PASS**. The archive SHA-256 is distributed separately in `mgc-engineering-ai-local-v6.3.20.zip.sha256`.
