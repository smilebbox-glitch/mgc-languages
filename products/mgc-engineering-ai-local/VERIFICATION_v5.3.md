# Verification — MGC Engineering AI Local v5.3.0

Verification performed against the final v5.3 source tree before release packaging.

## Functional regression

- Backend regression: **166/166 PASS**.
- Dedicated v5.3 closed-loop tests: **7/7 PASS**.
- Engineering Knowledge Memory + v5.3 integration regression: **PASS**.
- v5.3 additive/idempotent schema wrapper: **PASS**.
- Engineering Decision / Production Feedback / Effectiveness linkage: **PASS**.
- Planned-vs-actual deterministic calculations: **PASS**.
- Deviation expiry handling: **PASS**.
- Initial/residual P×S×D risk scoring: **PASS**.
- Root-Cause Explorer returns explainable candidates with `causal_claim=false`: **PASS**.
- Mixed visible/hidden root-cause evidence fail-closed: **PASS**.
- Supplier Quality Closed Loop aggregation: **PASS**.
- Risk-Based Validation Planner human-approval boundary: **PASS**.

## Security / authorization

- Human-facing API authorization preflight: **152/152 guarded**.
- Explicit exceptions remain only `/health` and the HMAC-signed machine webhook.
- Dockerfile/Dockle-style static preflight: **32/32 PASS**.
- Compose/access/runtime security preflight: **82/82 PASS**.
- Project / Manufacturing Area / Document ACL remains authoritative for v5.3 cross-domain data.
- Mixed visible/hidden evidence is not partially disclosed through root-cause or closed-loop views.

## Build / syntax

- `docker compose build` source/context preflight: **PASS**.
- Plain `docker compose build` structurally supported: **PASS**.
- CPU capacity preflight: **PASS**.
- Python compileall: **PASS**.
- Shell syntax: **PASS**.
- TypeScript/TSX transpile syntax: **PASS**.
- Docker Compose YAML parse: **12/12 PASS**.

## Environment limitation

A real Docker image build, runtime-container acceptance and Dockle image-layer scan were **not executed in this packaging environment** because Docker CLI/daemon and Dockle are unavailable. They are intentionally not reported as passes.

Run on the approved corporate build host:

```bash
docker compose build
make dockle
make acceptance
```

## Governance boundary

v5.3 is an engineering intelligence/evidence layer. It does not replace PLM/PDM, ERP, QMS, MES or SCADA. It does not automatically approve engineering release, deviation/waiver, residual-risk acceptance, final effectiveness or root cause.
