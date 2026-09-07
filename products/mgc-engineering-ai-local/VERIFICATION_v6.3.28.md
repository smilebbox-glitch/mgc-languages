# Verification — MGC Engineering AI Local v6.3.28

## Release identity

- Application: **6.3.28**
- Database schema: **6.3.13**
- New DB migration: **none**
- Release theme: **Integration Runtime Assurance**
- `production_authorized=false`

## Backend regression

Final product-code regression before release engineering:

- **630/630 PASS**
- **101/101 test files**
- failures: 0
- errors: 0
- skipped: 0

Group results: `158 + 86 + 162 + 224 = 630`.

## v6.3.28 integration assurance

- v6.3.27 Real Integration Certification regression + v6.3.28 focused tests: **25/25 PASS**
- Real Integration Certification preflight: **49/49 PASS**
- Integration Runtime Assurance preflight: **27/27 PASS**
- Reference contract suite: **5/5 PASS** — PLM/PDM/ERP/MES/QMS
- bounded cache staleness: PASS
- recovery-sync backward compatibility: PASS
- successful `IntegrationRun.status="ok"` reliability accounting: PASS

## Full operational verification

`python scripts/mgcctl.py verify --scope full --json`:

- **21/21 PASS**
- Docker static security: PASS
- Compose security: PASS
- API access: PASS
- Enterprise security: PASS
- deterministic secret scan: PASS
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

Rolling/Blue-Green adjacent compatibility is **6.3.27 ↔ 6.3.28** with schema **6.3.13**. Two-patch rollback remains fail-closed.

## Runtime behavior verified

- source failed + fresh cache → `DEGRADED_READ_ONLY` cached read;
- source failed + stale cache → `BLOCKED` cached read;
- healthy source + stale cache → `DEGRADED_READ_ONLY` until refresh;
- recovery sync is opt-in and limited to recoverable health/cache reasons;
- quality/certification degradation remains fail-closed;
- source-system writeback remains forbidden.

## Environment boundary

Docker CLI is unavailable in the packaging environment, so this verification does not claim a live corporate multi-container deployment or real vendor gateway certification. Target-host TLS/auth/network, resolved lock/wheelhouse, immutable image digest and CVE/SCA evidence remain deployment gates.

## Supply-chain posture

The source package remains **CONDITIONAL** until approved frontend/Python lock and wheelhouse artifacts plus target-host image/OS/CVE evidence are supplied. `production_authorized=false` remains mandatory.

## Package integrity

Final package verification:

- controlled payload files: **996**
- ZIP members including `BUILD_MANIFEST.json`: **997**
- missing: **0**
- extra: **0**
- size mismatch: **0**
- SHA-256 mismatch: **0**
- cache/test artifacts: **0**
- symlinks: **0**
- `unzip -t`: **PASS**

`BUILD_MANIFEST.json` is generated from the exact frozen payload and independently rechecked against the final archive.

## Additional static checks

- Python `compileall`: **PASS**
- shell syntax: **28/28 PASS**
- Compose YAML parse: **19/19 PASS**
- Legacy API baseline: **181/181 preserved**
- Current bounded-context routes: **247**

## Supply-chain verification result

- BUILD_INPUTS: **124/124 provenance entries verified**
- SBOM: **37 declared components**
- frontend direct dependency specs: exact pins
- source-package status: **CONDITIONAL**
- missing build-host artifacts: frontend `package-lock.json`/offline npm cache; Python core/ai/advanced hashed locks and wheelhouse manifests; immutable container digests; offline OS package manifest/install receipt
- `production_authorized=false`
