# MGC Engineering AI Local v6.3.2 — Verification

## Executed in packaging environment

- Backend collected inventory: **356 tests**.
- Backend regression: **356/356 PASS**, executed in deterministic shards across all 75 test files.
- v6.3.2 projection reliability tests: **8/8 PASS**.
- Transaction/projection reliability preflight: **26/26 PASS**.
- Ports & Adapters preflight: **25/25 PASS**.
- Architecture simplification preflight: **27/27 PASS**.
- Dependency profile preflight: **18/18 PASS**.
- Bounded-context router preflight: **21/21 PASS**.
- Legacy API compatibility: **5/5 PASS**, all 181 v6.2.0 legacy method/path contracts preserved.
- Docker static security: **38/38 PASS**.
- Compose/runtime static security: **100/100 PASS**.
- Human-facing API authorization preflight: **253 guarded routes**; 4 explicit non-human/public exceptions.
- Enterprise Security: **23/23 PASS**.
- Corporate Deployment: **13/13 PASS**.
- Observability/reliability: **16/16 PASS**.
- Operations Game Day: **15/15 PASS**.
- UX acceptance: **9/9 PASS**.
- DR foundation preflight: **PASS**.
- Python `compileall`: **PASS**.
- Build preflight: **PASS**; plain `docker compose build` remains supported.
- Secret scan: **0 committed secret candidates**.
- Build manifest: **582/582 PASS**.

## Reliability invariants verified

- engineering state and projection requests share one PostgreSQL transaction;
- rollback removes authoritative chunks and outbox work together;
- duplicate logical enqueue converges to one unique idempotency key;
- delivery receipt prevents duplicate logical processing after a recorded success;
- Qdrant replacement uses deterministic point IDs;
- Neo4j projection is convergent/retry-safe for MGC-owned edges;
- worker leases recover abandoned processing rows;
- retry is bounded and eventually enters DLQ;
- Engineering Admin can replay DLQ explicitly;
- older outbox events cannot overwrite a newer authoritative source version;
- legacy v6.3.1-and-older text evidence can be backfilled before rebuild;
- projection backlog/DLQ/lag is observable;
- optional projection failure does not block deterministic Core readiness;
- projection workers never create engineering approval decisions.

## Dependency lock status

The packaging environment intentionally reports warnings:

- `frontend/package-lock.json` is absent;
- Core has 21 declared Python version ranges;
- AI has 23 declared Python version ranges;
- Advanced has 25 declared Python version ranges.

This is not marked PASS. Enterprise CI must resolve/pin against approved npm/Python mirrors or wheelhouse and scan the resolved artifacts/images.

## Not executed in this environment

The following remain mandatory on the approved corporate build/target host:

- real Docker Engine/BuildKit image build for Core/AI/Advanced;
- resolved npm `npm ci` from approved lockfile/mirror;
- resolved Python wheelhouse build;
- Dockle or equivalent image-layer hardening scan;
- Trivy/Grype or approved CVE scan;
- real PostgreSQL v6.3.0 → v6.3.2 migration rehearsal and rollback plan;
- real Redis/Celery multi-worker `SKIP LOCKED` contention test;
- Qdrant outage/recovery + full rebuild with representative engineering corpus;
- Neo4j outage/recovery + graph rebuild;
- MinIO outage/recovery + evidence mirror replay;
- real AD/OIDC and PKI/TLS/mTLS negative tests;
- backup→restore on target storage;
- target-host performance/load certification;
- PLM/PDM/ERP/MES/QMS reconciliation;
- controlled Operations Game Day and UAT.

## Deployment authority

No automated test, readiness endpoint, rebuild status or projection health result authorizes Production GO. Human corporate change approval, Information Security acceptance, Data Owner acceptance, UAT and Operations acceptance remain mandatory.
