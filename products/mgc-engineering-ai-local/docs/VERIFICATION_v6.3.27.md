# Verification — MGC Engineering AI Local v6.3.27

## Release identity

- Application: **6.3.27**
- Database schema: **6.3.13**
- New DB migration: **none**
- Release theme: **Real Integration Certification**
- `production_authorized=false`

## Backend regression

Final product-code regression before release engineering:

- **620/620 PASS**
- **100/100 test files**
- failures: 0
- errors: 0
- skipped: 0

Group results: `77 + 87 + 40 + 42 + 77 + 99 + 125 + 73 = 620`.

## v6.3.27 integration certification

- Real Integration Certification preflight: **49/49 PASS**
- Reference contract suite: **5/5 PASS** — PLM/PDM/ERP/MES/QMS
- Focused integration + rolling/blue-green/mgcctl regression: **50/50 PASS**
- Existing integration hardening/reconciliation focused regression: **50/50 PASS**
- Local live HTTP simulator certification: **PASS**, 2/2 records valid, deterministic replay/idempotency/fingerprint checkpoint verified

The simulator result validates the certification mechanism only. It is not a production Teamcenter/SAP/MES/QMS certification.

## API and architecture

- Bounded contexts: **21/21 PASS**
- Bounded-context routes: **247**
- Legacy API contracts: **181/181 preserved**
- API authorization: **319 guarded human-facing routes + 5 explicit system exceptions**
- Architecture Simplification: **27/27**
- Dependency Profiles: **18/18**
- Ports & Adapters: **25/25**
- Projection Reliability: **26/26**
- Domain Integrity: **25/25**
- Revision & Conflict: **28/28**
- Approval/Release Governance: **28/28**
- Enterprise Identity: **38/38**
- Release Handover: **46/46**
- Data Lifecycle: **33/33**
- Performance/Scale: **18/18**
- Read Models/Cache: **22/22**
- Workload Isolation: **29/29**
- Job Recovery: **35/35**
- DR Consistency: **45/45**
- Operational Resilience: **23/23**

## Deployment / certification / provenance

- Operations Consolidation: **31/31**
- Rolling Upgrade: **37/37**
- Blue/Green: **40/40**
- Application HA: **41/41**
- DB/Evidence HA: **45/45**
- Multi-host: **30/30**
- Production Certification: **22/22**
- Production Load Certification: **24/24**
- Automated Release Acceptance: **26/26**
- Acceptance Evidence Registry: **33/33**
- External Trust/Retention: **32/32**

Rolling/Blue-Green adjacent compatibility is **6.3.26 ↔ 6.3.27** with schema **6.3.13**. Two-patch rollback remains fail-closed.

## Security / build

- Docker static security: **38/38 PASS**
- Compose/runtime security: **119/119 PASS**
- Enterprise Security: **23/23 PASS**
- Observability: **16/16 PASS**
- Corporate Deployment: **13/13 PASS**
- Game Day: **15/15 PASS**
- UX: **9/9 PASS**
- Python compileall: **PASS**
- shell syntax: **29/29 PASS**
- Compose YAML: **19/19 PASS**
- deterministic secret scan: **0 findings**
- plain `docker compose build`: supported by build preflight

Docker CLI is unavailable in the packaging environment (`docker: command not found`), so no claim is made for live corporate multi-container integration certification here.

## Supply chain

- BUILD_INPUTS: **120 file inputs**
- present/hashed: **113**
- missing corporate lock/wheelhouse artifacts: **7**
- immutable image refs: **14**
- build-input provenance verification: **120/120 PASS**
- Supply Chain compatibility: **27/27 PASS**
- SBOM: **37 components**
- status: **CONDITIONAL**
- `production_authorized=false`

The missing source package artifacts are the approved frontend lock and profile-specific Python lock/wheelhouse manifests. Immutable corporate image digests, offline OS-package receipts and CVE/SCA approvals must also be produced on the target build environment.

## Package integrity

First independent package pass on the frozen clean tree:

- controlled payload files: **986**
- ZIP members including `BUILD_MANIFEST.json`: **987**
- missing: **0**
- extra: **0**
- size mismatch: **0**
- SHA-256 mismatch: **0**
- cache/test artifacts: **0**
- symlinks: **0**
- `unzip -t`: **PASS**

The final archive is rebuilt after this verification text and BUILD_INPUTS are refreshed, then checked again with the same independent verifier.
