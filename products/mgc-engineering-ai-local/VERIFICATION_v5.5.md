# Verification — MGC Engineering AI Local v5.5.0

Verification performed against the final v5.5 source tree before release packaging.

## Functional / regression

- Backend regression: **189/189 PASS**.
- Dedicated v5.5 Configuration & Release Assurance: **12/12 PASS** (service/regression + additive migration coverage).
- EBOM ↔ MBOM aligned / revision mismatch classification: PASS.
- Explicit 150% → 100% applicability; UNKNOWN is never silently included: PASS.
- Effectivity / AS-BUILT revision mismatch and approved-deviation handling: PASS.
- Change Cut-In old-stock / logistics / PPAP gates: PASS.
- Mixed hidden-evidence fail-closed: PASS.
- Release Package SHA-256 fingerprint / human approval boundary: PASS.
- Release Drift ignores volatile capture timestamp: PASS.
- Release Baseline v3 detects MBOM change after freeze: PASS.
- Variant / Plant Matrix and read-only Cross-System Consistency: PASS.
- Deterministic CPU-only Ask Configuration: PASS.
- Additive/idempotent v5.5 schema wrapper: PASS.

## Security / access

- Human-facing API authorization preflight: **165/165 guarded**.
- Explicit non-human exceptions remain `/health` and HMAC-signed integration webhook.
- Dockerfile/Dockle-style static preflight: **32/32 PASS**.
- Compose/access/runtime security preflight: **82/82 PASS**.
- Project / Manufacturing Area / Document ACL remains fail-closed for v5.5 authority-shadow records.

## Build / syntax

- Python `compileall`: PASS.
- TypeScript/TSX `transpileModule` syntax: PASS.
- Shell `bash -n`: PASS.
- Docker Compose YAML parse: **12/12 PASS**.
- CPU capacity preflight: PASS.
- `docker compose build` source/context preflight: PASS.
- BUILD_MANIFEST integrity: **324/324 files match SHA-256**.
- Release ZIP integrity (`unzip -t`): PASS.

## Runtime limitation

A real Docker image build, runtime container acceptance and Dockle image-layer scan were **not executed in this packaging environment** because Docker CLI/daemon and Dockle are unavailable here.

Run on the approved corporate build host:

```bash
docker compose build
make dockle
make acceptance
```

## Governance

Configuration & Release Assurance is advisory. PLM/PDM remains authoritative for EBOM/released product definition, ERP/manufacturing planning for MBOM/material planning, and MES or approved import for AS-BUILT. v5.5 does not automatically approve manufacturing handover/release, write back to source systems, execute stock disposition or control MES/SCADA/PLC equipment.
