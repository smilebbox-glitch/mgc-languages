# Dockle / container security — v4.0.0

## What is hardened in this release

MGC-owned runtime images (`api/worker`, `frontend`, `gateway`, `webhook-edge`, integration
simulator) are built to run as non-root and include `HEALTHCHECK`. Runtime
containers use `no-new-privileges`, drop Linux capabilities where practical,
and use a read-only root filesystem with tmpfs for temporary paths. The API is
multi-stage: compilers/build-essential exist only in the builder stage.

Dockerfiles use `COPY`, not `ADD`; apt cache is removed in the same layer; no
credentials are embedded in image `ENV`; setuid/setgid bits are removed from
MGC-owned runtime images.

## Run real Dockle after building

```bash
make build
./scripts/dockle_scan.sh
```

The scan fails the command on **FATAL** Dockle findings and stores JSON reports
under `security-reports/dockle/`.

To additionally inspect imported third-party images:

```bash
./scripts/dockle_scan.sh --all
```

For an air-gapped environment, stage the approved Dockle binary/image in the
same supply-chain process as the other deployment images. Never mount the
Docker socket into the MGC application containers; it is mounted only into the
short-lived Dockle scanner when the Docker-based scanner fallback is used.


## Verification performed while packaging v3.8

The release contains `security-reports/STATIC_SECURITY_VERIFICATION.txt`. In the packaging environment:

- Dockerfile Dockle/CIS-aligned source checks: **32/32 PASS**;
- Compose hardening/network checks: **82/82 PASS**;
- air-gap Compose contains no `:latest` references;
- the air-gap bundle script refuses placeholder/`latest` image references before export.

A real Dockle **image** scan could not be executed in the packaging runtime because there is no Docker daemon/CLI or Dockle binary there. This is intentionally reported as **NOT RUN**, not as a pass. Run `make build && make dockle` on the connected Docker build workstation; promotion should stop on Dockle FATAL findings.

The source ZIP does not vendor npm packages. A frontend dependency install/build was attempted during packaging but the environment could not resolve `registry.npmjs.org`; TSX syntax/transpilation was therefore checked locally, while the canonical full frontend build remains part of `make build` on the connected build workstation.

## Important limitation

Dockle is an image/configuration linter, not a complete vulnerability scanner.
Use the corporate SCA/container scanner (e.g. Trivy or equivalent) in addition
to Dockle. Pin every third-party image to an approved version/digest in the
release manifest before production promotion.

- Human-facing API authorization preflight: **59/59 guarded routes PASS**; health and HMAC webhook are explicit exceptions.
