# MGC Engineering AI Local v6.3.19 — Verification

## Release boundary

- Application: **6.3.19**
- Database schema: **6.3.13**
- DB migration: **none**
- Scope: PostgreSQL/evidence-storage authority fencing and failover verification; automotive business-domain behavior unchanged.

## Backend regression

The complete backend inventory was collected and executed from the release tree with `PYTHONPATH=backend`. Because third-party process-lifetime cleanup hooks can retain the packaging Python process after pytest has finished, the suite was executed in non-overlapping verification groups with a packaging-only `pytest_sessionfinish` hook outside the release tree. Each completed group emitted explicit collected/passed/failed/error/skipped counts; the hook does not modify product behavior.

- collected: **501 tests**
- test files: **92/92**
- total: **501/501 PASS**
- failures: **0**
- errors: **0**
- skipped: **0**
- v6.3.19 Database & Evidence Storage HA tests: **16/16 PASS**

## v6.3.19 authoritative HA gate

- Database & Evidence Storage HA static preflight: **45/45 PASS**.
- PostgreSQL role probe checks `pg_is_in_recovery()` and `transaction_read_only` on the actual write connection.
- Optional PostgreSQL `system_identifier` pinning fails closed on mismatch or unavailable identity when configured.
- `mgc_schema_state` must be present and exactly equal runtime schema **6.3.13** before authoritative writes are considered safe.
- Evidence marker requires expected cluster id, valid monotonic generation and `state=active`.
- Evidence generation can be bound to the PostgreSQL cluster identity.
- Marker path traversal and symlinked marker/path components fail closed; marker updates use atomic replace plus file/directory `fsync`.
- Mutating HTTP traffic is fenced before route side effects.
- SQLAlchemy sessions are fenced on `before_flush`, bulk ORM UPDATE/DELETE and final `before_commit`, covering API, Celery and maintenance write paths.
- `.mgc-ha` operational fencing metadata is excluded from evidence fingerprints and authoritative backup archives.
- Evidence promotion is explicit, stale-generation protected and requires a full consistency-bound recovery point.
- Promotion evidence always retains `production_authorized=false`.
- MGC does not promote PostgreSQL, implement STONITH/quorum or claim storage replication.

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
- Bounded Context Ownership: **21/21 PASS**, **247 routes**.
- Legacy API contract: **181/181 method/path contracts preserved**.
- Supply Chain v6.3.12 compatibility: **27/27 PASS**.

## Security / operations / build gates

- API authorization: **314 guarded human-facing routes**, 4 explicit system exceptions.
- Docker static security: **38/38 PASS**.
- Compose/runtime security: **108/108 PASS**.
- Enterprise Security: **23/23 PASS**.
- Observability: **16/16 PASS**.
- Corporate Deployment: **13/13 PASS**.
- Game Day: **15/15 PASS**.
- UX acceptance: **9/9 PASS**.
- Build preflight: **PASS**; plain `docker compose build` remains supported.
- Python `compileall`: **PASS**.
- Compose YAML parse: **18/18 PASS**.
- shell `bash -n`: **28/28 PASS**.
- deterministic source secret scan: **0 committed secret candidates**.
- SBOM: **37 components**.
- BUILD_INPUTS provenance inventory: **66 file inputs verified** (including v6.3.19 authoritative-HA overlay/control scripts).

## Supply-chain status

Supply-chain status remains **CONDITIONAL**, not PASS and not Production GO. The packaging environment does not provide the approved corporate npm lock/cache, Python hashed locks/wheelhouses, immutable container image digests, offline OS package bundle, or approved source/image vulnerability scanner evidence. Those artifacts are not fabricated.

## Target-host HA gates not executed here

The packaging environment has no Docker CLI/daemon and no external PostgreSQL HA manager or replicated/shared production storage. Therefore this release does **not** claim that the following were executed:

- real primary failure + STONITH/fencing;
- PostgreSQL replica promotion through the corporate HA manager;
- application reconnect through a writer VIP/DNS;
- evidence-storage replication/failover at storage-controller level;
- target-local evidence generation promotion after external failover;
- simultaneous old-primary isolation proof;
- multi-host/zone load-balancer failover;
- measured RPO/RTO or zero-RPO certification;
- live backup/restore/PITR plus HA failover chain on target infrastructure.

These remain mandatory corporate target-host acceptance gates.

## Production authority boundary

`production_authorized=false` remains explicit. Passing source/regression/static gates proves the release implementation and fail-closed contracts, not production authorization. PostgreSQL/evidence HA requires external quorum/fencing/replication infrastructure and a controlled human change decision.

## Final package integrity

- clean manifest-controlled payload files: **848**;
- `BUILD_MANIFEST.json` is included in the ZIP but intentionally does not hash itself;
- expected ZIP file count: **849**;
- cache/test artifacts targeted for release: **0**.

Final ZIP-to-manifest verification: **848/848 payload files PASS**; ZIP members: **849** including `BUILD_MANIFEST.json`; missing: **0**; extra: **0**; size mismatch: **0**; SHA-256 mismatch: **0**; cache/test artifacts: **0**; `unzip -t`: **PASS**. The archive SHA-256 is distributed separately in `mgc-engineering-ai-local-v6.3.19.zip.sha256`.
