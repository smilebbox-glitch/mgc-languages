# Verification — MGC Engineering AI Local v6.2.1

## Release scope

v6.2.1 physically decomposes the legacy HTTP route monolith into the six v6.2 bounded contexts while preserving the public API contract. It is a source/composition patch only: application version is 6.2.1 and database schema remains 6.2.0.

## Verification executed in this packaging environment

| Check | Result |
|---|---:|
| Context router decomposition preflight | 21/21 PASS |
| v6.2.0 → v6.2.1 legacy API contract equivalence | 4/4 PASS |
| Architecture simplification preflight | 27/27 PASS |
| v6.2.0 + v6.2.1 affected pytest suite | 15/15 PASS |
| Human-facing API authorization | 236 guarded routes; 4 explicit exceptions |
| Enterprise Security | 23/23 PASS |
| Docker static security | 38/38 PASS |
| Compose/runtime security | 100/100 PASS |
| Corporate Deployment | 13/13 PASS |
| UX acceptance | 9/9 PASS |
| Observability/Reliability | 16/16 PASS |
| Game Day | 15/15 PASS |
| Build preflight | PASS |
| `docker compose build` command support | PASS |
| Deterministic source secret scan | 0 findings |
| CycloneDX declared-component SBOM | generated for 6.2.1 |

## Route decomposition proof

The original v6.2.0 archive was used to create `docs/API_CONTRACT_v6.2.0.json`. The v6.2.1 preflight verifies:

- original route count = 181;
- current decomposed route count = 181;
- exact HTTP method + path set is unchanged;
- handler identity is unchanged;
- normalized AST hash for each handler signature/body/decorator is unchanged.

This proves the source extraction did not silently alter handler implementation semantics at the Python AST level.

## Ownership distribution

- Engineering Core: 53;
- Configuration & Change: 39;
- Manufacturing & Quality: 39;
- Supplier & Field: 22;
- Intelligence & Search: 20;
- Platform & Operations: 8.

`backend/app/api/routes.py` is now a 19-line compatibility facade. Shared ACL/visibility helpers live in route-free `backend/app/api/context_shared.py`.

## Profile-aware context composition

`context_registry.py` mounts contexts according to the active runtime capability envelope. This is composition only, not authorization.

- Core does not mount Supplier & Field when no supplier/field capability is active.
- Core still mounts Intelligence & Search because `lexical_search` is a Core capability.
- Advanced mounts all six bounded contexts.

Identity, Project/Area/Document ACL and CapabilityGate remain independent enforcement layers.

## Schema compatibility

No database migration is introduced by v6.2.1.

- `APP_VERSION = 6.2.1`;
- `SCHEMA_VERSION = 6.2.0`;
- existing v6.2.0 schema bootstrap/migration remains authoritative.

## Dependency-lock status

The packaging environment still reports the known enterprise supply-chain gaps inherited from v6.2.0:

- `frontend/package-lock.json` is absent;
- backend requirements contain 25 declared version ranges.

This is not a production PASS. Corporate CI must resolve/pin dependencies using the approved npm mirror and Python wheelhouse, then generate resolved SBOM/CVE evidence from the actual images.

## Full-suite statement

A complete post-refactor backend suite was not claimed in this packaging environment. The environment does not have every production Python dependency installed (for example `qdrant_client`), while those dependencies are declared for the Docker build. The affected architecture suites completed 15/15 and all listed static/security gates passed. The approved build host must run the complete backend suite before promotion.

## Required target-host gates

Mandatory before controlled pilot/production promotion:

- real Core/AI/Advanced `docker compose build`;
- production frontend `npm ci` using approved lockfile/mirror;
- resolved Python wheelhouse + CVE scan;
- Dockle/Trivy/Grype image checks;
- AD/OIDC negative tests;
- PKI/TLS/mTLS negative tests;
- database least-privilege proof;
- backup→restore drill;
- target-host performance/load certification;
- PLM/PDM/ERP/MES/QMS reconciliation;
- controlled UAT and Operations acceptance.

## Deployment authority

v6.2.1 does not authorize deployment. Human corporate change approval, InfoSec/Data Owner acceptance, UAT and Operations acceptance remain mandatory.
