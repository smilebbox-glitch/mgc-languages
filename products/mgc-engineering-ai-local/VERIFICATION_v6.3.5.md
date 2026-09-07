# MGC Engineering AI Local v6.3.5 — Verification

## Verified in packaging environment
- v6.3.5 governance tests: **7/7 PASS**.
- Expanded affected/cumulative regression: **86/86 PASS**.
- Approval & Release Governance preflight: **28/28 PASS**.
- Architecture simplification: **27/27 PASS**.
- Context ownership: **21/21 PASS**.
- API contract: **5/5 PASS**; 181/181 legacy routes preserved.
- Ports & Adapters: **25/25 PASS**.
- Dependency profiles: **18/18 PASS**.
- Projection reliability: **26/26 PASS**.
- Domain integrity: **25/25 PASS**.
- Revision/conflict: **28/28 PASS**.
- Docker security: **38/38 PASS**.
- Compose/runtime security: **100/100 PASS**.
- Enterprise Security: **23/23 PASS**.
- API authorization: **271 guarded human-facing routes**, 4 explicit system exceptions.
- UX acceptance: **9/9 PASS**.
- Observability: **16/16 PASS**.
- Corporate Deployment: **13/13 PASS**.
- Operations Game Day: **15/15 PASS**.
- Secret scan: **0 committed secret candidates**.
- Build preflight: **PASS**; plain `docker compose build` supported.
- Frontend TSX transpile/syntax: **PASS**.
- Python compileall: **PASS**.
- Build Manifest: **613/613 files verified by SHA-256**.
- ZIP integrity: **PASS**.
- Cache artifacts in package: **0**.

## Backend inventory note
`pytest --collect-only` sees **376 tests in 78 files**. A monolithic full run in this packaging runtime again did not terminate within the execution window after progressing through assertions, consistent with the previously observed test-runtime shutdown/thread issue. Therefore this document does **not** claim 376/376. The release is grounded on the 86-test cumulative changed-surface regression plus all static production/security gates above.

## Supply-chain boundary
Dependency locking remains WARN: the project still requires a reviewed `package-lock.json` and resolved/pinned Python wheelhouse on the approved corporate build host. Run SCA/CVE/image scans on those resolved artifacts.

## Mandatory corporate-host gates
- real `docker compose build` for selected profile;
- PostgreSQL v6.3.4 → v6.3.5 migration rehearsal and backup/restore;
- OIDC/AD and PKI/TLS negative tests;
- full resolved dependency/CVE scan;
- real multi-user UAT of maker-checker/SoD and Release Package handover;
- validation of corporate legal/e-sign requirements if qualified signatures are required.

## Governance boundary
Approval records are tamper-evident engineering evidence, not a qualified electronic signature. Release Package never authorizes automatic PLM/PDM/MES or equipment write-back.
