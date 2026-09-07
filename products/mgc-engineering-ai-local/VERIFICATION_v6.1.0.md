# Verification — MGC Engineering AI Local v6.1.0

## Scope

Corporate Deployment & Pilot Launch Kit. Проверка подтверждает код/конфигурацию/acceptance harness, но не заменяет реальный корпоративный deployment acceptance.

## Executed locally

| Gate | Result |
|---|---:|
| Backend regression | 316/316 PASS |
| Dedicated v6.1.0 tests | 8/8 PASS |
| v6.0.8–v6.1.0 focused regression | 26/26 PASS |
| Human-facing API authorization | 232/232 guarded |
| Explicit API exceptions | 4 (health x3 + HMAC webhook x1) |
| Docker static security | 38/38 PASS |
| Compose/runtime security | 100/100 PASS |
| Enterprise Security | 23/23 PASS |
| Corporate Deployment preflight | 13/13 PASS |
| Observability preflight | 16/16 PASS |
| Game Day preflight | 15/15 PASS |
| UX acceptance | 9/9 PASS |
| DR preflight | PASS |
| Performance preflight (CI policy) | PASS |
| Pilot acceptance harness | PASS |
| CPU capacity preflight | PASS |
| Build source/context preflight | PASS |
| Compose YAML parse | 13/13 PASS |
| Python compileall | PASS |
| TypeScript TSX transpile syntax | PASS |
| Shell bash -n | PASS |
| Deterministic source secret scan | 0 findings |
| Declared-component SBOM | 37 components |
| BUILD_MANIFEST | 490/490 SHA-256 PASS |
| ZIP integrity | PASS (validated after packaging) |
| Cache artifacts in ZIP | 0 |

## Dependency lock status

The packaging environment reports:

- frontend `package-lock.json` absent;
- backend requirements contain 25 declared version ranges.

This is intentionally **not** marked PASS. Enterprise CI should resolve/pin dependencies against the approved npm mirror and Python wheelhouse, then run CVE scanning on resolved images/components.

## Not executed in this environment

The following remain mandatory on the approved corporate target/build host:

- real `docker compose build`;
- production frontend `npm ci` from approved lockfile/mirror;
- resolved backend wheelhouse build/scan;
- Dockle image-layer scan;
- Trivy/Grype CVE scan;
- real AD/OIDC negative tests;
- real PKI/TLS/mTLS negative tests;
- runtime proof that `mgc_runtime` cannot CREATE/ALTER/DROP;
- backup→restore drill on target storage;
- Pilot performance/load profile against real PostgreSQL/Redis/Qdrant/model topology;
- actual PLM/PDM/ERP/MES/QMS connectivity and reconciliation;
- Operations Game Days on an approved non-production/controlled target;
- real UAT with 15–30 engineers.

## Deployment authority

A v6.1.0 result of `READY_TO_LAUNCH_CONTROLLED_PILOT` means only that the evidence required to begin the controlled pilot is present. It does not authorize Production GO. Human corporate change approval and later UAT/Operations acceptance remain mandatory.
