# Verification — MGC Engineering AI Local v5.8.0

Verification performed against the final v5.8 source tree before release packaging.

## Functional / regression

- Complete backend regression: **221/221 PASS** (executed as 109 + 78 + 34 independent batches).
- Dedicated v5.8 Field Reliability scenarios: **12/12 PASS**, including migration coverage.
- Grouped right-censored Weibull: PASS.
- Explicit insufficient-data behavior: PASS.
- Field failure clustering remains investigation-only / non-causal: PASS.
- DFMEA field-occurrence review: PASS.
- Validation exposure gap detection: PASS.
- Revision-level observed field effectiveness: PASS.
- VIN genealogy -> TSB applicability: PASS.
- NTF/repeat-repair technical pattern boundary: PASS.
- Campaign candidate remains advisory/no automatic recall: PASS.
- Mixed hidden-evidence fail-closed: PASS.
- v5.8 additive/idempotent schema wrapper: PASS.

## Security / access

- Human-facing API authorization preflight: **186/186 guarded**.
- Explicit non-human exceptions remain `/health` and HMAC-signed integration webhook.
- Dockerfile/Dockle-style static preflight: **32/32 PASS**.
- Compose/access/runtime security preflight: **82/82 PASS**.

## Build / syntax

- Python compileall: PASS.
- TypeScript/TSX transpile syntax: PASS.
- Shell `bash -n`: PASS.
- Docker Compose YAML parse: **12/12 PASS**.
- CPU capacity preflight: PASS.
- `docker compose build` source/context preflight: PASS.

## Runtime limitation

A real Docker image build, runtime container acceptance and Dockle image-layer scan were **not executed in this packaging environment** because Docker CLI/daemon and Dockle are unavailable here. Required corporate build-host gate:

```bash
docker compose build
make dockle
make acceptance
```

## Governance

Field Reliability is advisory engineering intelligence. It does not replace DMS/Warranty/ERP/QMS, automatically confirm root cause, edit DFMEA/V&V, declare a safety defect, or initiate recall/service campaigns. Human engineering/quality/legal authority remains mandatory.
