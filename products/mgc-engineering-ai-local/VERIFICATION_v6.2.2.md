# Verification — MGC Engineering AI Local v6.2.2

## Scope

Service Dependency Decomposition on top of v6.2.1. No DB migration; `APP_VERSION=6.2.2`, `SCHEMA_VERSION=6.2.0`.

## Executed checks in packaging environment

| Gate | Result |
|---|---:|
| v6.2.0/v6.2.1/v6.2.2 affected pytest | 22/22 PASS |
| Dependency profile preflight | 18/18 PASS |
| Architecture simplification preflight | 27/27 PASS |
| Bounded-context decomposition preflight | 21/21 PASS |
| v6.2.0 API contract equivalence | 4/4 PASS |
| Docker/Dockle static preflight | 38/38 PASS |
| Compose/access/runtime security | 100/100 PASS |
| Human-facing API authorization | 236 guarded routes; 4 explicit exceptions |
| Enterprise security | 23/23 PASS |
| Corporate deployment | 13/13 PASS |
| Observability/reliability | 16/16 PASS |
| Game Day | 15/15 PASS |
| UX acceptance | 9/9 PASS |
| Build preflight | PASS; plain `docker compose build` supported |
| Profile-aware declared SBOM | generated, 37 components |

## Dependency isolation verified

- `context_shared.py` has zero top-level `app.services.*` imports;
- context registry has zero top-level imports of the six bounded-context modules;
- `vector_store.py` has no top-level import of Qdrant/Sentence Transformers;
- Core requirements exclude `qdrant-client`, `sentence-transformers`, `neo4j`, `minio`;
- AI requirements extend Core with Qdrant/Sentence Transformers;
- Advanced requirements extend AI with Neo4j/MinIO;
- sensitive Core import test passed while imports of `qdrant_client`, `sentence_transformers`, `neo4j`, and `minio` were forcibly blocked;
- Core image + AI/Advanced runtime profile is rejected fail-closed by build/runtime compatibility validation.

## API compatibility

The v6.2.0 baseline contains 181 legacy routes. v6.2.2 retains all 181 method/path contracts and handler AST equivalence for the decomposed handler modules.

## Dependency lock status

The project still intentionally ships declared version ranges rather than an enterprise resolved lock/wheelhouse:

- Core: 21 declared ranges;
- AI: 23 declared ranges;
- Advanced: 25 declared ranges;
- frontend `package-lock.json` remains absent in this packaging baseline.

Therefore enterprise dependency-lock acceptance is **not claimed**. Approved internal mirror/wheelhouse resolution and CVE scanning remain mandatory.

## Not executed here

- real Docker Engine/BuildKit image build for Core/AI/Advanced;
- actual image-layer Dockle scan;
- Trivy/Grype resolved image CVE scan;
- real OIDC/PKI/mTLS negative tests;
- target-host backup→restore and load/performance certification;
- real PLM/PDM/ERP/MES/QMS connectivity/reconciliation;
- controlled pilot/UAT/Operations acceptance.

No Production GO is implied by these packaging checks.
