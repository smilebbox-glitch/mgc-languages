# MGC Engineering AI Local v6.3.7 — Verification

## Release scope
Engineering Release Handover & Integration Safety on top of v6.3.6 Enterprise Identity & Policy Enforcement, v6.3.5 Approval & Release Governance, v6.3.4 Revision/Conflict Management, v6.3.3 Domain Integrity, v6.3.2 Transactional Outbox, v6.3.1 Ports & Adapters and v6.3.0 Manufacturing Work Instructions / BOM Translation / Layouts.

## Executed automated checks
- v6.3.0–v6.3.7 cumulative manufacturing/architecture/governance regression: **53/53 PASS**.
- Engineering Change + integration + integration-hardening + reconciliation + security regression: **46/46 PASS**.
- combined non-overlapping executed regression above: **99/99 PASS**.
- v6.3.7 handover safety tests: **8/8 PASS** (included in the 53-test cumulative group).
- Release Handover Safety preflight: **46/46 PASS**.
- Architecture Simplification: **27/27 PASS**.
- Bounded Context Ownership: **21/21 PASS**.
- Legacy API contract: **5/5 PASS**; all **181/181** v6.2.0 method/path contracts preserved.
- Dependency Profiles: **18/18 PASS**.
- Ports & Adapters: **25/25 PASS**.
- Projection Reliability: **26/26 PASS**.
- Domain Integrity: **25/25 PASS**.
- Revision & Conflict Management: **28/28 PASS**.
- Approval & Release Governance: **28/28 PASS**.
- Enterprise Identity & Policy Enforcement: **38/38 PASS**.
- Docker static security: **38/38 PASS**.
- Compose/runtime security: **100/100 PASS**.
- Enterprise Security: **23/23 PASS**.
- API authorization: **286 human-facing routes guarded**, **4 explicit system exceptions**.
- UX acceptance: **9/9 PASS**.
- Observability: **16/16 PASS**.
- Corporate Deployment: **13/13 PASS**.
- Game Day static gate: **15/15 PASS**.
- deterministic source secret scan: **0 committed secret candidates**.
- frontend TypeScript transpile: **PASS**.
- Python `compileall`: **PASS**.
- shell `bash -n`: **PASS**.
- Docker Compose YAML parse: **PASS**.
- plain `docker compose build` preflight: **PASS**.

## Full backend inventory
The repository contains **390 collected backend tests in 80 test files**. A full independent-file execution was attempted because the packaging runtime has previously retained background worker/thread state after completed assertions. The execution window terminated before every file could complete; completed processes showed no assertion failure, but the complete inventory was not verified. Therefore **390/390 is not claimed** for this packaging environment.

The corporate build-host acceptance gate must execute the complete 390-test inventory and require every test process to terminate cleanly.

## Handover safety invariants verified
- write-back is disabled by default; dry-run is default; code/host allowlists are empty by default;
- read connectors are not silently converted into outbound write connectors;
- target authority is restricted to PLM/PDM/MES domains;
- production write requires explicit global enable, code+host allowlists and HTTPS;
- targets used for write must declare idempotency support;
- maker cannot authorize or execute their own outbound job;
- service account cannot replace the human checker/executor;
- outbound payload/manifest/request SHA and idempotency key form an immutable command identity;
- DB-level trigger rejects direct mutation of immutable command fields;
- retry is bounded and reuses the same idempotency command;
- required external receipt is fail-closed;
- reconciliation requires hash/target-state proof and rejects mismatch;
- Release Manifest is revalidated before write;
- failed/reconciliation-failed or stale unreconciled delivery is visible in Operations Summary/Prometheus/Support Bundle;
- handover degradation does not make optional external integration an authority over PostgreSQL Core readiness;
- no machine-control path exists.

## Supply-chain lock status
**WARN, intentionally not PASS.**
- `frontend/package-lock.json` is absent.
- backend Core/AI/Advanced requirements contain declared version ranges.
- enterprise build must resolve/pin packages through approved npm/Python repositories and run SCA/CVE/image scans.

## Required corporate target-host gates
- full **390-test** backend run with clean process termination;
- real `docker compose build` for Core/AI/Advanced;
- PostgreSQL 6.3.6 → 6.3.7 migration rehearsal + backup/restore;
- OIDC re-auth/service-account negative tests against the real IdP;
- register only approved PLM/PDM/MES gateway targets;
- validate code and hostname allowlists;
- certify external target idempotency semantics;
- network timeout/retry/duplicate-delivery Game Day;
- receipt and reconciliation mismatch tests against the real gateway;
- validate operational alert threshold for unreconciled handover age;
- CVE/SCA/container image scans;
- InfoSec + PLM/MES owner + Operations controlled UAT before `HANDOVER_WRITE_ENABLED=true`.

## Deployment authority
No handover, reconciliation, approval or readiness status produced by MGC constitutes automatic Production GO. Enabling outbound write requires explicit corporate change approval. Machine-control integration remains outside the product boundary.

## Packaging integrity
- `BUILD_MANIFEST.json`: **648/648 PASS** against the clean release tree (size + SHA-256 for every listed file).
- release-tree cache artifacts (`__pycache__`, `.pytest_cache`, `*.pyc`, `*.pyo`): **0**.
- temporary DB/log artifacts (`*.db`, `*.sqlite*`, `*.tmp`, `*.log`): **0**.
- final ZIP must be built only from this clean manifest-consistent tree; `unzip -t` and an independent ZIP cache-artifact scan are mandatory before distribution.
