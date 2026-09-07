# Verification — MGC Engineering AI Local v6.0.3

Verification выполнен на финальном v6.0.3 source tree до release packaging.

## Functional / regression

- Полный backend regression: **261/261 PASS** (`72 + 49 + 73 + 67`).
- Dedicated v6.0.3 reconciliation + migration scenarios: **13/13 PASS**.
- v6.0.1–v6.0.3 hardening/reconciliation compatibility set: **PASS**.
- EBOM ↔ MBOM deterministic source reconciliation: PASS.
- Confirmed alias mapping applied only to reconciliation copy: PASS.
- Stale mapping detected by source fingerprint and not used to make a report green: PASS.
- Multi-key mapping for one BOM source row (parent/child/supplier): PASS.
- MES genealogy ↔ released configuration revision check: PASS.
- QMS Part/VIN/Supplier linkage coverage: PASS.
- Explicit source-of-truth conflict detection: PASS.
- Time-decaying source freshness contributes to pilot gate: PASS.
- Controlled-pilot gate fails closed on missing roles, stale mapping, LOW/UNKNOWN required source quality, quarantine, authority conflict, EBOM/MBOM mismatch or unresolved MES/release state: PASS.
- v6.0.3 additive/idempotent schema marker/migration: PASS.

## Security / access

- Human-facing API authorization preflight: **197/197 guarded**.
- Preflight reports **4 explicit public/non-human exceptions** limited to health/auth-bootstrap/integration-machine boundaries.
- Dockerfile/Dockle-style static preflight: **32/32 PASS**.
- Compose/access/runtime security preflight: **84/84 PASS**.
- Mapping/reconciliation admin endpoints require authenticated Engineering Admin context: PASS by route implementation/preflight.
- Reconciliation is read-only and never mutates external source payloads: PASS by dedicated regression.

## Build / syntax / operations

- Python `compileall`: **PASS**.
- Docker Compose YAML parse: **12/12 PASS**.
- TypeScript/TSX syntax transpile using locally available TypeScript compiler: **PASS**.
- Shell `bash -n`: **PASS**.
- CPU capacity preflight: **PASS**.
- `docker compose build` source/context preflight: **PASS**.
- DR foundation preflight: **PASS**.
- Final BUILD_MANIFEST integrity: **395/395 SHA-256 PASS**.
- Release ZIP integrity (`unzip -t`): **PASS**.

### Frontend limitation in packaging environment

A full dependency-aware `npm ci` / Vite production build was **not executed** because `frontend/node_modules` is not installed in this packaging environment. The locally available TypeScript compiler was used for TSX syntax/transpile validation. The real frontend dependency install/build remains part of the Docker build-host gate.

## Runtime / integration limitations

The following were **not executed** in this packaging environment:

- real Docker image build and runtime container acceptance;
- Dockle image-layer scan;
- live Teamcenter/Windchill/SAP/MES/QMS synchronization;
- reconciliation against a real corporate golden dataset;
- corporate OIDC/AD, network segmentation and SIEM validation;
- full backup→restore drill on production-like infrastructure.

Run on the approved corporate build/integration host:

```bash
docker compose build
make dockle
make acceptance
```

Then perform the controlled pilot described in:

- `docs/INTEGRATION_HARDENING_PILOT_ACCEPTANCE.md`;
- `docs/INTEGRATION_PILOT_RECONCILIATION.md`;
- `docs/REAL_INTEGRATION_CHECKLIST.md`.

## Pilot governance

`READY_FOR_CONTROLLED_PILOT` is a deterministic readiness signal, not production authorization. PLM/PDM/ERP/MES/QMS remain authoritative. MGC does not resolve source-of-truth conflicts automatically, does not write reconciliation corrections back to source systems and requires human go-live approval.
