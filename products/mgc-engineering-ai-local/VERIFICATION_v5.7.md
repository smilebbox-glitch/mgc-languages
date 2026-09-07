# Verification — MGC Engineering AI Local v5.7.0

Verification performed against the final v5.7 source tree before release packaging.

## Functional / regression

- Full backend regression: **209/209 PASS** (executed as three complete non-overlapping groups: 98 + 81 + 30).
- Dedicated v5.7 scenarios: **12/12 PASS** (11 Series Intelligence service scenarios + v5.7 migration test).
- Series Health from actual imported quality observations: PASS.
- Process capability Cpk degradation and bands: PASS.
- Explainable non-causal quality change-point signal: PASS.
- VIN suspect-population filtering by actual supplier lot genealogy: PASS.
- Human-controlled containment progress: PASS.
- PFMEA ↔ Control Plan ↔ actual defect review signal: PASS.
- Supplier-lot outlier signal: PASS.
- Expired-calibration / post-expiry sample signal: PASS.
- Field feedback + advisory COPQ: PASS.
- Mixed hidden-evidence fail-closed: PASS.
- Deterministic Ask Series Intelligence keeps `causal_claim=false`: PASS.
- Field/warranty cases remain compatible with Engineering Knowledge Memory regression: PASS.
- v5.7 additive/idempotent schema wrapper: PASS.

## Security / access

- Human-facing API authorization preflight: **179/179 guarded**.
- Explicit non-human exceptions remain `/health` and the HMAC-signed integration webhook.
- Dockerfile/Dockle-style static preflight: **32/32 PASS**.
- Compose/access/runtime security preflight: **82/82 PASS**.

## Build / syntax

- Python `compileall`: PASS.
- TypeScript/TSX transpile syntax: PASS.
- Shell `bash -n`: PASS.
- Docker Compose YAML parse: **12/12 PASS**.
- CPU capacity preflight: PASS.
- `docker compose build` source/context preflight: PASS.
- BUILD_MANIFEST integrity: **339/339 files match SHA-256**.
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

Series Intelligence is advisory. MES/QMS/SPC/ERP/Warranty remain authoritative. Change-point, supplier-lot, station and shift relationships are investigation signals, not causal proof. Root cause, containment release, PFMEA updates, process approval and supplier/operator accountability remain human-controlled corporate decisions.
