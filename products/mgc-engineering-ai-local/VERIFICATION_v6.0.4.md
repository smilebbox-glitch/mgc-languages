# Verification — MGC Engineering AI Local v6.0.4

Verification выполнен на финальном v6.0.4 source tree до release packaging.

## Functional / regression

- Full backend regression: **267/267 PASS**.
- Dedicated v6.0.4 performance + migration scenarios: **6/6 PASS**.
- v6.0.4 additive/idempotent performance-index migration: PASS.
- Existing v6.0.1–v6.0.3 hardening/reconciliation behavior: PASS inside full regression.

## Performance harness

- `performance_preflight.py --profile ci`: PASS.
- Critical composite index declaration gate: **9/9 present**.
- Synthetic CI dataset actually executed:
  - parts: 5,000;
  - BOM edges: 25,000;
  - VINs: 2,000;
  - genealogy rows: 20,000;
  - quality observations: 50,000.
- Recorded CI SQLite query p95:
  - BOM children: **1.673 ms**;
  - VIN genealogy: **0.135 ms**;
  - 7-day series quality aggregation: **45.850 ms**.
- HTTP load-runner harness self-test: **100/100 successful**, error rate 0%; this used a local read-only stub endpoint and validates the harness only, not MGC production API capacity.
- Pilot/Enterprise certification: **NOT EXECUTED in packaging environment**.

## Security / access

- Human-facing API authorization preflight: **197/197 guarded**.
- Explicit non-human exceptions remain documented health/root/webhook paths.
- Dockerfile/Dockle-style static preflight: **32/32 PASS**.
- Compose/access/runtime security preflight: **84/84 PASS**.

## Build / syntax / operations

- Python compileall: PASS.
- TypeScript/TSX transpile syntax: **1/1 source PASS** using installed TypeScript compiler API.
- Full frontend type/module build was not run locally because frontend React/Three packages are not installed in the packaging container; it remains part of `docker compose build` on the approved build host.
- Shell `bash -n`: PASS.
- Docker Compose YAML parse: **12/12 PASS**.
- CPU capacity preflight: PASS.
- `docker compose build` source/context preflight: PASS.
- DR preflight: PASS.
- Performance/capacity preflight: PASS.
- BUILD_MANIFEST integrity: **410/410 tracked files match SHA-256**.

## Runtime limitation

A real Docker image build, frontend npm dependency build, runtime container acceptance, Dockle image-layer scan and production-shaped PostgreSQL/Redis/Qdrant load certification were **not executed** in this packaging environment.

Run on the approved corporate build/performance host:

```bash
docker compose build
make dockle
make acceptance
make performance-preflight
```

Then execute the Pilot profile from `docs/PERFORMANCE_SCALE_CERTIFICATION.md` and `docs/PERFORMANCE_PILOT_ACCEPTANCE.md`.

## Governance

CI synthetic timings are not presented as enterprise performance. A controlled pilot is performance-ready only after the target corporate infrastructure passes the agreed live SLOs without weakening ACL, evidence, provenance or human-approval boundaries.
