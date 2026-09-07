# Verification — MGC Engineering AI Local v6.3.29

## Release identity

- Application: **6.3.29**
- Database schema: **6.3.13**
- New DB migration: **none**
- Release theme: **Target-Host Deployment Assurance**
- `production_authorized=false`

## Backend regression

Final product-code regression before release engineering:

- **636/636 PASS**
- **102/102 test files**
- failures: 0
- errors: 0

Group results: `148 + 64 + 162 + 262 = 636`.

## Target-host assurance

- Target-Host Assurance preflight: **15/15 PASS**
- reference two-node profile-30 certification: **PASS**
- canonical SHA-256 guard: **PASS**
- missing topology node: fail-closed **PASS**
- duplicate/extra evidence: fail-closed **PASS**
- old Docker baseline: fail-closed **PASS**
- unsynchronized clock: fail-closed **PASS**
- deployment without PASS report: blocked by real rollout path
- emergency rollback remains independent from host-assurance gate

## Full operational verification

`./mgcctl verify --scope full --json`:

- **22/22 PASS**
- Docker static security: PASS
- Compose security: PASS
- API access: PASS
- Enterprise security: PASS
- secret scan: PASS
- Architecture Simplification: PASS
- Bounded contexts: PASS — **247 routes**
- Ports & Adapters: PASS
- Domain Integrity: PASS
- Rolling Upgrade: PASS
- Blue/Green: PASS
- Application HA: PASS
- DB/Evidence HA: PASS
- Multi-host: PASS
- Production Certification: PASS
- Production Load Certification: PASS
- Automated Release Acceptance: PASS
- Acceptance Evidence Registry: PASS
- External Trust/Retention: PASS
- Real Integration Certification: PASS
- Integration Runtime Assurance: PASS
- Target-Host Deployment Assurance: PASS

Rolling/Blue-Green adjacent compatibility is **6.3.28 ↔ 6.3.29** with schema **6.3.13**. Two-patch rollback remains fail-closed.

## Trust boundary

A host-assurance `PASS` certifies only the baseline host envelope. It does **not** certify production load, vendor integrations, CVE/SCA state or business authorization. `performance_certified=false`, `production_authorized=false` and human approval remain mandatory.

## Environment boundary

Docker CLI is unavailable in the packaging environment. Live target-host probe evidence must therefore be generated on the company's actual application nodes before deployment.

## Static / supply-chain verification

- Python `compileall`: **PASS**
- shell syntax: **30/30 PASS**
- Compose YAML parse: **19/19 PASS**
- Legacy API baseline: **181/181 preserved**
- Current bounded-context routes: **247**
- BUILD_INPUTS provenance entries: **134/134 validated**
- source-package build-input files present: **127/134**; **7** corporate lock/wheelhouse artifacts intentionally absent
- SBOM: **37 declared components**
- source-package supply-chain status: **CONDITIONAL**
- `production_authorized=false`

The `CONDITIONAL` status is caused by missing target-build artifacts: approved frontend lock/offline npm cache, profile-specific hashed Python locks/wheelhouse manifests, immutable image digests, offline OS-package receipt and corporate CVE/SCA approvals.

## Package integrity

- controlled payload files: **1013**
- ZIP members including `BUILD_MANIFEST.json`: **1014**
- independent first-pass missing: **0**
- independent first-pass extra: **0**
- size mismatch: **0**
- SHA-256 mismatch: **0**
- cache/test artifacts: **0**
- symlinks: **0**
- ZIP CRC/test: **PASS**

The final package is regenerated after this verification document and BUILD_INPUTS are frozen, then independently rechecked against the embedded manifest.
