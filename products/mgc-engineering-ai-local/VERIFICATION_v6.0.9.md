# Verification — MGC Engineering AI Local v6.0.9

Verification performed against the final v6.0.9 source tree before release packaging.

## Functional / regression

- Backend regression: **308/308 PASS**.
- Dedicated v6.0.9 Production Operations Acceptance scenarios: **10/10 PASS**.
- v6.0.9 schema marker and operations game-day tables: PASS.
- Rehearsal cannot return production GO: PASS.
- Controlled GO requires all mandatory runtime gates: PASS.
- RPO breach => NO_GO: PASS.
- Open CRITICAL production incident => NO_GO: PASS.
- Open HIGH production incident => CONDITIONAL_GO: PASS.
- Exercise VERIFIED status requires recovery/verification timestamps plus evidence: PASS.
- Finalization requires `FINALIZE_OPERATIONS_ACCEPTANCE`: PASS.
- Finalized GO remains advisory (`deployment_authorized=false`): PASS.
- Application fault-injection boundary (`application_never_injects_faults=true`): PASS.

## Operations / reliability preflights

- Game-day framework preflight: **15/15 PASS**.
- Observability/reliability preflight: **16/16 PASS**.
- UX acceptance preflight: **9/9 PASS**.
- DR foundation preflight: PASS.
- Performance/capacity preflight (CI profile): PASS.
- Controlled-pilot harness preflight: PASS.
- CPU capacity preflight: PASS.
- `docker compose build` source/context preflight: PASS.

## Security / access

- Human-facing API authorization preflight: **227/227 guarded**, with 4 explicit non-human/public exceptions defined by the existing security policy.
- Dockerfile/Dockle-style static preflight: **38/38 PASS**.
- Compose/access/runtime security preflight: **100/100 PASS**.
- Enterprise security preflight: **23/23 PASS**.
- Deterministic source secret scan: **0 committed secret candidates**.
- Offline declared-component SBOM: **37 components** (`security-reports/SBOM_v6.0.9.cdx.json`).

## Build / syntax

- Python compileall: PASS.
- TypeScript/TSX transpile syntax: PASS.
- Shell `bash -n`: PASS.
- Docker Compose YAML parse: **13/13 PASS**.
- BUILD_MANIFEST integrity: **474/474 files match SHA-256**.
- Release ZIP integrity (`unzip -t`): PASS.
- Test caches / `.pyc` in release: **0**.

## Important runtime limitation

The packaging environment does **not** provide an approved corporate runtime, Docker daemon/image scanner, AD/OIDC/PKI infrastructure, or authority to inject destructive failures. Therefore the following are mandatory target-host / corporate acceptance gates and are **not claimed as executed here**:

- real `docker compose build` and runtime acceptance;
- Dockle image-layer scan;
- Trivy/Grype resolved-image CVE scan;
- approved frontend lockfile / `npm ci` and resolved backend wheelhouse verification;
- live AD/OIDC negative tests;
- live PKI/mTLS negative tests;
- real PostgreSQL/Redis/Qdrant outage drills;
- real Celery worker crash/restart drill;
- real PLM/ERP/MES/QMS integration-outage drill;
- real expired-certificate and OIDC-failure game days;
- real queue-overload drill on the approved capacity-test host;
- real isolated backup→restore drill with measured RTO/RPO;
- live monitoring/alert-routing verification;
- Pilot/Enterprise target-host performance profile.

These drills must be performed on an approved non-production or controlled-pilot environment following `docs/GAME_DAY_RUNBOOK.md`. MGC records the evidence but does not execute destructive fault injection.

## Governance

Operations Acceptance is advisory evidence for the corporate Go-Live board. `GO` is not a deployment command. Every evaluation keeps `human_go_live_required=true` and `deployment_authorized=false`.
