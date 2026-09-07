# Supply Chain & Reproducible/Offline Builds — v6.3.12

## Goal

Make every production build input explicit, immutable and independently verifiable while keeping ordinary developer builds convenient. v6.3.12 targets **reproducible inputs and offline application builds**; it does not claim byte-identical OCI output across arbitrary Docker/BuildKit versions.

## Two build postures

### Developer / internal build

`docker compose build` remains supported. It may resolve bounded dependency ranges and use package networks. It is not a production supply-chain certification.

### Strict corporate build

Enable `MGC_REQUIRE_REPRODUCIBLE_BUILD=true` and run `make reproducible-build`.

Before the Docker build starts, strict mode requires:

1. approved npm `package-lock.json`;
2. populated offline npm cache;
3. exact SHA-256 Python locks for Core/AI/Advanced;
4. verified profile wheelhouses;
5. approved immutable container/base images (`repo@sha256:...`);
6. verified offline OS `.deb` bundle tied to the exact approved Python base image;
7. current BUILD_INPUTS manifest + checksum;
8. approved vulnerability scanner.

Missing evidence fails closed. The source release intentionally remains `CONDITIONAL` until the corporate build host supplies these artifacts.

## Python dependency profiles

Human-maintained intent stays in:

- `backend/requirements-core.txt`
- `backend/requirements-ai.txt`
- `backend/requirements-advanced.txt`

Corporate preparation produces:

- `backend/locks/requirements-<profile>.lock.txt`
- `backend/wheelhouse/<profile>/WHEELHOUSE_MANIFEST.json`
- exact wheel files with recorded SHA-256.

Strict install uses only:

```text
pip --no-index --require-hashes
```

This preserves the Core/AI/Advanced boundary from v6.2.2.

## Frontend

Direct dependency specs in `package.json` are exact. Transitive production resolution must come from the approved npm registry. `prepare_frontend_lock.sh` creates `package-lock.json`, populates a dedicated cache and proves that `npm ci --offline` succeeds before the cache is accepted.

## Offline OS dependencies

A pinned Python base image alone is insufficient for a real offline build if the Dockerfile later executes `apt-get` against a network mirror. v6.3.12 therefore separates OS-package preparation from the application build.

On an approved host:

```bash
PYTHON_BASE_IMAGE=<approved repo@sha256:digest> ./scripts/prepare_os_package_bundle.sh
```

The preparation step downloads the required `.deb` packages and writes `backend/os-packages/runtime/OS_PACKAGE_MANIFEST.json`. The manifest records the exact approved Python base image and SHA-256 of every `.deb`.

During strict application build:

- the bundle is verified before installation;
- manifest `base_image` must equal the approved `PYTHON_BASE_IMAGE`;
- unmanifested or hash-mismatched `.deb` files fail the build;
- local `dpkg -i` is used;
- `apt-get update/install` is never used in the strict application-build path.

## Network isolation

`docker-compose.reproducible.yml` sets `build.network: none` for application builds. Once corporate preparation is complete, the strict application build must not contact PyPI, npm or Debian mirrors. Approved base images must already exist locally and the wrapper uses `--pull=false`.

A production air-gap export with `MGC_REQUIRE_REPRODUCIBLE_BUILD=true` is forced through the same strict path; the legacy build wrapper refuses to silently fall back to range resolution.

## Immutable images

Tags are not immutable. `.env.reproducible` must contain approved `repo@sha256:<64 hex>` references for build bases and runtime infrastructure images. Placeholders in `.env.reproducible.example` intentionally fail validation.

## BUILD_INPUTS provenance

`generate_build_inputs.py --env .env.reproducible` records and hashes:

- dependency declarations;
- generated lock/wheelhouse/OS-bundle manifests and bundle files when present;
- Dockerfiles and build-control/reproducible/air-gap scripts;
- Compose build overlays;
- immutable base/runtime image references.

The SHA-256 of `BUILD_INPUTS.json` is carried in OCI provenance labels together with release version. Changing a strict build wrapper therefore changes the provenance hash even when dependency declarations are unchanged.

## Vulnerability gates

An SBOM is evidence, not vulnerability acceptance. Strict mode therefore separates two gates:

1. **source/dependency scan before build** — scans source/dependency/container configuration with the approved Trivy/Grype-equivalent policy;
2. **built-image scan after build** — scans the exact resulting backend/frontend/gateway/webhook images, covering resolved transitive dependencies and base OS packages.

HIGH/CRITICAL policy is corporate-configurable, but strict mode requires actual scanner evidence rather than accepting a missing scanner as PASS.

## Build attestation

After the real corporate build, `generate_build_attestation.py` binds:

- BUILD_INPUTS SHA-256;
- CycloneDX SBOM SHA-256;
- npm/Python lock and wheelhouse evidence;
- offline OS package manifest;
- immutable base-image references;
- source/dependency and built-image CVE report hashes;
- built application image IDs.

`verify_build_attestation.py --strict` validates that evidence. The attestation cannot authorize deployment and always records `production_authorized=false`.

## Non-goals

v6.3.12 does not:

- invent dependency versions, hashes or image digests;
- claim bit-for-bit OCI reproducibility across arbitrary builders;
- accept vulnerabilities merely because an SBOM exists;
- store registry credentials/tokens in provenance evidence;
- automatically authorize production deployment.
