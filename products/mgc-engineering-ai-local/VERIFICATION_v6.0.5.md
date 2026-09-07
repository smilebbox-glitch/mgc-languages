# Verification — MGC Engineering AI Local v6.0.5

Verification выполнен на финальном v6.0.5 source tree перед release packaging.

## Functional / regression

- Полный backend regression: **274/274 PASS**.
- Dedicated v6.0.5 Security Hardening: **7/7 PASS**.
- v6.0.5 schema marker / idempotency: PASS.
- Production trusted-header lockout + proxy-secret gate: PASS.
- Security posture policy: PASS.
- Audit export redaction + SHA-256 chain: PASS.
- Audit retention explicit-confirmation gate: PASS.
- TLS/mTLS + split migration/runtime DB topology assertions: PASS.

## Authorization / container / deployment security

- Human-facing API authorization preflight: **201/201 guarded**; 4 deliberate non-human/public exceptions remain health endpoints and HMAC-signed integration webhook.
- Docker/Dockle-style static preflight: **38/38 PASS**.
- Compose/access/runtime security preflight: **98/98 PASS**.
- Enterprise security preflight: **22/22 PASS**.
- Source secret scan: **0 findings**.
- Enterprise deployment template contains no floating `:latest` image references: PASS.

## Supply-chain evidence

- Offline declared-component CycloneDX-style SBOM generated: **37 components**.
- CVE scanner hook: PRESENT and fail-closed when `MGC_REQUIRE_CVE_SCANNER=true`.
- Actual Trivy/Grype CVE scan in this environment: **NOT EXECUTED** — scanner binaries unavailable.
- Frontend approved `package-lock.json`: **NOT GENERATED** in offline packaging environment; corporate npm mirror gate required.
- Backend exact resolved wheelhouse/lock: **NOT GENERATED** from declared ranges in this environment; corporate Python mirror/wheelhouse gate required.
- `scripts/dependency_lock_preflight.py` correctly reports these two build-host requirements as warnings locally and can fail closed with `MGC_REQUIRE_LOCKFILES=true`.

## Build / syntax / operations

- Python compileall: PASS.
- TypeScript/TSX syntax parser: **3/3 PASS**.
- Shell `bash -n`: PASS.
- Docker Compose YAML parse: **13/13 PASS**.
- CPU capacity preflight: PASS.
- `docker compose build` source/context preflight: PASS.
- DR preflight: PASS.
- Performance/capacity preflight: PASS.

## Runtime limitations / required corporate gates

Not executed in this packaging environment:

- real Docker image build;
- resolved frontend `npm ci` production build;
- Syft/resolved image SBOM if required by corporate policy;
- Trivy/Grype image/filesystem CVE scan;
- Dockle image-layer scan;
- penetration test / SAST under corporate tooling;
- real TLS certificate-chain and mTLS client negative tests;
- real corporate OIDC/AD login/group-removal/token-expiry/audience-negative tests;
- PostgreSQL runtime-role negative DDL test;
- runtime container acceptance.

On the approved corporate build/runtime host these are release gates, not optional checks.

## Governance

v6.0.5 does not claim formal security certification, zero vulnerabilities or cryptographic non-repudiation of database audit rows. Human security approval remains mandatory. MGC continues to be an Engineering Intelligence & Evidence Layer and does not weaken existing ACL/source-system/human approval boundaries.
