# Verification — MGC Engineering AI Local v6.2.0

## Scope

Architecture Simplification Release. Проверка подтверждает, что упрощение runtime composition, bounded-context model, Object 360 и shared platform contracts не ломают существующие engineering/lifecycle/security функции. Она не заменяет реальный corporate target-host acceptance.

## Executed locally

| Gate | Result |
|---|---:|
| Pre-hardening full backend baseline | 324/324 PASS |
| Post-hardening full backend rerun | NOT COMPLETED in packaging runtime (timed execution limit after 44%) |
| Dedicated v6.2.0 architecture tests | 11/11 PASS |
| Post-hardening changed-surface regression | 31/31 PASS |
| Architecture Simplification preflight | 25/25 PASS |
| Human-facing API authorization | 236/236 guarded |
| Explicit API exceptions | 4 existing health/machine exceptions |
| Docker static security | 38/38 PASS |
| Compose/runtime security | 100/100 PASS |
| Enterprise Security | 23/23 PASS |
| Corporate Deployment preflight | 13/13 PASS |
| Observability preflight | 16/16 PASS |
| Game Day preflight | 15/15 PASS |
| UX acceptance | 9/9 PASS |
| Pilot acceptance harness | PASS |
| DR preflight | PASS |
| Core authoritative-only backup manifest | PASS |
| AI backup manifest with optional Qdrant snapshot | PASS |
| Performance preflight (CI policy) | PASS |
| CPU capacity preflight | PASS |
| Build source/context preflight | PASS |
| Compose YAML parse | 13/13 PASS |
| Python compileall | PASS |
| TypeScript/TSX transpile syntax | PASS |
| Shell bash -n | PASS |
| Deterministic source secret scan | 0 findings |
| Declared-component SBOM | 37 components |
| BUILD_MANIFEST | 512/512 SHA-256 PASS |
| ZIP integrity | PASS (validated after packaging) |
| Cache artifacts in ZIP | 0 |

## Architecture invariants verified

- exactly six bounded contexts are declared;
- `Core ⊂ AI ⊂ Advanced` profile composition is monotonic;
- PostgreSQL cannot be disabled from Core;
- Qdrant is required only by semantic/AI composition, not Core readiness;
- Neo4j is an Advanced optional projection;
- profile/capability composition is not authorization;
- Object 360 uses fail-closed evidence visibility;
- unified Action/Decision contract preserves human decision requirement;
- connector envelope preserves external source authority;
- base Compose has no hard dependency on Qdrant/model-server;
- Core search degrades to deterministic metadata/lexical retrieval;
- PostgreSQL + evidence storage are the authoritative DR set;
- Qdrant snapshot is optional/rebuildable and Core backup succeeds without it.
- unknown deployment profiles fail closed instead of silently widening to Advanced;
- feature overrides cannot widen Core/AI with capabilities from a higher profile;
- legacy Supplier/Field/Cost/Program/Neo4j/Native-CAD/VLM routes are capability-gated declaratively;
- pre-auth capability denials return a generic 404 without exposing deployment posture;
- Object 360 object types are runtime-profile aware and Supplier is absent outside Advanced;
- VIN Object 360 does not load Field Claim evidence when `supplier_field` is inactive.

## Regression scope note

The original v6.2.0 package completed a 324/324 backend regression before this hardening pass. After the profile-integrity/Object-360/capability-gate changes, the packaging runtime was able to complete the dedicated architecture suite (11/11), the changed-surface regression suite (31/31), and all listed static/security/preflight gates. A monolithic full-suite rerun exceeded the available execution window after reaching 44%; therefore this document does **not** claim a new post-hardening 324/324 result. The approved CI/build host must run the complete backend suite before promotion.

## Dependency lock status

The packaging environment reports:

- frontend `package-lock.json` absent;
- backend requirements contain 25 declared version ranges.

This is intentionally **not** marked PASS. Enterprise CI must resolve/pin dependencies against the approved npm mirror and Python wheelhouse, then run CVE scanning on resolved artifacts/images.

## Not executed in this environment

The following remain mandatory on the approved corporate build/target host:

- real `docker compose build` for Core/AI/Advanced profiles;
- production frontend `npm ci` from approved lockfile/mirror;
- resolved backend wheelhouse build/scan;
- Dockle image-layer scan;
- Trivy/Grype CVE scan;
- real AD/OIDC negative tests;
- real PKI/TLS/mTLS negative tests;
- runtime proof of DB least privilege;
- actual backup→restore drill on target storage;
- target-host Pilot/Enterprise performance/load tests;
- actual PLM/PDM/ERP/MES/QMS connectivity/reconciliation;
- Operations Game Days and controlled UAT.

## Deployment authority

v6.2.0 preserves all v6.1.0 governance boundaries. Runtime profile selection only composes capabilities. It never widens project/area/document ACL and never authorizes production deployment. Human corporate change approval, security acceptance, UAT and Operations acceptance remain mandatory.
