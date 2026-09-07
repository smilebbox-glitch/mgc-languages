# Verification — MGC Engineering AI Local v6.0.2

Verification выполнен на финальном v6.0.2 source tree до release packaging.

## Functional / regression

- Полный backend regression: **248/248 PASS** (`98 + 83 + 67`).
- Dedicated v6.0.2 integration hardening + migration scenarios: **12/12 PASS**.
- v6.0.1 + v6.0.2 hardening compatibility: **18/18 PASS**.
- Integration contract validation: PASS.
- Transparent Data Confidence breakdown: PASS.
- Time-decaying freshness: PASS.
- Missing source timestamp with configured SLA cannot remain HIGH: PASS.
- Strong metadata idempotency: PASS.
- Payload SHA-256 fallback for weak source identity: PASS.
- Quarantine preserves immutable replayable payload: PASS.
- Explicit replay revalidates current contract: PASS.
- Record-mode JSON evidence: PASS.
- Per-source PostgreSQL advisory sync lock: PASS.
- v6.0.2 additive/idempotent schema marker/migration: PASS.

## Security / access

- Human-facing API authorization preflight: **193/193 guarded**.
- Explicit non-human/public exceptions reported by the preflight remain limited to health/public auth bootstrap and HMAC integration webhook boundaries.
- Dockerfile/Dockle-style static preflight: **32/32 PASS**.
- Compose/access/runtime security preflight: **84/84 PASS**.
- Quarantine filesystem paths are not exposed in normal client responses: PASS by dedicated tests/static review.
- Replay endpoint is identity/admin governed: PASS.

## Build / syntax / operations

- Python `compileall`: **PASS**.
- Docker Compose YAML parse: **12/12 PASS**.
- TypeScript/TSX syntax transpile using local TypeScript compiler: **PASS (2 source/config files)**.
- Shell `bash -n`: **PASS**.
- CPU capacity preflight: **PASS**.
- `docker compose build` source/context preflight: **PASS**.
- DR foundation preflight: **PASS**.

### Frontend limitation in packaging environment

A full dependency-aware `tsc -b` / Vite production build was **not executed** in this packaging environment because `frontend/node_modules` is not installed. The locally available TypeScript compiler was used for syntax/transpile validation. The real frontend dependency install/build remains part of the Docker build-host gate below.

## Runtime limitations

A real Docker image build, container runtime acceptance, Dockle image-layer scan, live PLM/ERP/MES/QMS integration test and full backup→restore drill were **not executed in this packaging environment** because Docker daemon/Dockle and corporate source systems are unavailable here.

Run on the approved corporate build/integration host:

```bash
docker compose build
make dockle
make acceptance
```

For the integration pilot additionally execute `docs/INTEGRATION_HARDENING_PILOT_ACCEPTANCE.md` against real test endpoints and verify source-side revisions/checksums/timestamps, freshness SLA, quarantine/replay and reconciliation with each authoritative system.

## Governance

Data Confidence is an explainable evidence-quality indicator and not an engineering approval score. PLM/PDM/ERP/MES/QMS remain authoritative for their owned records. Contract-invalid payload is quarantined; stale-but-valid evidence remains visible with explicit degradation.
