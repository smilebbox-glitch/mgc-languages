# MGC Engineering AI Local v6.3.12 — Verification

## Release boundary

- Application: **6.3.12**
- Database schema: **6.3.11**
- DB migration: **none**
- Scope: supply-chain, provenance and reproducible/offline build hardening; automotive-domain behavior unchanged.

## Executed tests

Final backend regression was executed from the unpacked release ZIP using independently terminating test-file groups, avoiding the known monolithic packaging-runtime shutdown issue:

- full collected inventory: **434 tests in 85 test files**;
- completed backend regression: **434/434 PASS**;
- completed test files: **85/85**;
- assertion failures: **0**;
- per-file/group test timeout after the final compatibility fix: **0**;
- v6.3.12-specific supply-chain tests: **13/13 PASS**;
- legacy workload compatibility tests (`test_compute_manager` + v6.3.11 workload): **9/9 PASS** after restoring transition queue aliases.

The full run exposed and then verified a real compatibility issue: v6.3.11 had moved internal Celery routing from legacy `heavy/background/default` queues to resource-class queues, while older producers could still publish to the historical queue names. v6.3.12 now keeps new resource-class routing but workers also consume the legacy aliases during the migration window.

## Static / architecture gates

- Supply Chain v6.3.12 structural/fail-closed preflight: **27/27 PASS**.
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
- Bounded Context ownership: **21/21 PASS**, **245 routes**.
- Legacy API contract: **181/181 method/path contracts preserved**.

## Security / build gates

- Docker static security: **38/38 PASS**.
- Compose/runtime security: **104/104 PASS**.
- Enterprise Security: **23/23 PASS**.
- API authorization: **307 guarded human-facing routes**, 4 explicit system exceptions.
- Observability: **16/16 PASS**.
- Corporate Deployment: **13/13 PASS**.
- Game Day: **15/15 PASS**.
- UX: **9/9 PASS**.
- Build preflight: **PASS**; plain `docker compose build` remains supported for development/internal builds.
- Python `compileall`: **PASS**.
- Shell `bash -n` on release shell scripts: **PASS**.
- Compose YAML parse: **14/14 PASS**.
- Deterministic source secret scan: **0 committed secret candidates**.
- Production frontend `npm ci`/Vite build: **not executed** in the source packaging environment because the approved `package-lock.json`/offline npm cache are intentionally absent; this remains part of the strict corporate build-host gate.

The strict production path additionally requires a source/dependency CVE scan and a **built-image** CVE scan. These are not claimed as completed in the packaging environment because an approved Trivy/Grype-equivalent scanner and approved corporate dependency/image artifacts are not available here.

## Supply-chain status

Source release status is intentionally **CONDITIONAL**. Missing corporate artifacts are reported, never fabricated:

- `frontend/package-lock.json` and populated offline npm cache;
- exact hash-pinned Core/AI/Advanced Python locks;
- corresponding wheelhouses and SHA-256 manifests;
- approved immutable container/base image digests;
- offline backend OS `.deb` bundle + `OS_PACKAGE_MANIFEST.json`, generated against the approved immutable Python base image;
- approved HIGH/CRITICAL source/dependency and built-image CVE scanner evidence.

Strict mode enforces:

- Python install from local wheelhouse only (`--no-index --require-hashes`);
- frontend install from local npm cache only (`npm ci --offline`);
- runtime OS packages from a verified local `.deb` bundle only;
- OS bundle base-image match to the approved `PYTHON_BASE_IMAGE`;
- `build.network: none` for strict application builds;
- immutable `repo@sha256:<digest>` image inputs;
- BUILD_INPUTS provenance covering build-control scripts, dependency evidence and immutable image references;
- OCI version/provenance labels on built application images;
- source/dependency CVE scan before build and built-image CVE scan after build;
- post-build attestation evidence with `production_authorized=false`.

`python scripts/supply_chain_preflight.py` returns **CONDITIONAL** for this source package. `python scripts/supply_chain_preflight.py --strict` correctly **fails closed (exit code 2)** because the approved corporate artifacts are absent.

## Mandatory corporate build-host gate

1. Resolve all approved base/runtime images to immutable digests and write `.env.reproducible`.
2. Generate all three Python lock/wheelhouse profiles from the approved Python mirror.
3. Generate `package-lock.json` + offline npm cache from the approved npm registry.
4. Generate and verify the OS `.deb` bundle from the approved pinned Python base + approved Debian mirror/network.
5. Regenerate and verify `supply-chain/BUILD_INPUTS.json` using the approved immutable image environment.
6. Run the approved source/dependency HIGH/CRITICAL CVE gate.
7. Run `make reproducible-build`; strict Compose must use `build.network: none`, local dependency bundles and `--pull=false`.
8. Run the approved **built-image** HIGH/CRITICAL CVE gate against the actual app/frontend/gateway/webhook images.
9. Generate and verify `BUILD_ATTESTATION.json`; retain CVE reports, SBOM, lock/wheelhouse/OS manifests and final image IDs/digests as release evidence.
10. Re-run the full **434-test** backend suite and production frontend build on the approved corporate build host with clean process completion.
11. Repeat Docker/Dockle, OIDC/PKI, backup/restore, target-host load/UAT and corporate change approval on target infrastructure.

No result in this document authorizes Production GO.

## Packaging integrity

- CycloneDX source SBOM: **37 declared components**.
- Final source-package manifest: **741/741 payload files SHA-256 verified**; `BUILD_MANIFEST.json` is intentionally outside its own hash list.
- Cache/test/runtime artifacts in release tree: **0**.
- ZIP central-directory/CRC integrity: **PASS**.
- Independent ZIP → BUILD_MANIFEST content/hash verification: **741/741 PASS**.
