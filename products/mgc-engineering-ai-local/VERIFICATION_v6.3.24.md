# Verification — MGC Engineering AI Local v6.3.24

## Release contract

- Application: `6.3.24`
- Engineering DB schema: `6.3.13`
- DB migration: none
- Theme: Acceptance Evidence Registry & Release Provenance Ledger

## Backend regression

Final post-integration inventory: **573 tests / 97 test files**.

Eight non-overlapping pytest groups were executed from repository root with `PYTHONPATH=backend` and a packaging-only `pytest_sessionfinish` hook to avoid the known third-party process-shutdown hang. Results:

- 70/70 PASS
- 78/78 PASS
- 51/51 PASS
- 13/13 PASS
- 80/80 PASS
- 92/92 PASS
- 146/146 PASS
- 45/45 PASS

Total: **573/573 PASS**. Failures/errors/skips: **0/0/0**.

## v6.3.24 provenance checks

- Acceptance Evidence Registry preflight: **33/33 PASS**
- specialized provenance tests included in full regression
- concurrent append serialization tested
- content-object tamper detection tested
- event rename/sequence tamper detection tested
- symlink refusal tested
- private-key rejection tested
- key rotation/revocation tested
- historical pre-revocation acceptance verification tested
- cross-version metrics comparison tested
- pipeline/baseline optional auto-registration contracts tested

## Existing hardening gates

- Architecture Simplification: 27/27 PASS
- Dependency Profiles: 18/18 PASS
- Ports & Adapters: 25/25 PASS
- Projection Reliability: 26/26 PASS
- Domain Integrity: 25/25 PASS
- Revision & Conflict: 28/28 PASS
- Approval/Release Governance: 28/28 PASS
- Enterprise Identity: 38/38 PASS
- Release Handover: 46/46 PASS
- Data Lifecycle: 33/33 PASS
- Performance & Scale: 18/18 PASS
- Read Models & Cache: 22/22 PASS
- Workload Isolation: 29/29 PASS
- Job Recovery: 35/35 PASS
- Data Consistency / DR: 45/45 PASS
- Operational Resilience: 23/23 PASS
- Rolling Upgrade: 37/37 PASS
- Blue/Green: 40/40 PASS
- Application HA: 41/41 PASS
- DB/Evidence HA: 45/45 PASS
- Multi-host Topology: 30/30 PASS
- Production Certification: 22/22 PASS
- Production Load Certification: 24/24 PASS
- Automated Release Acceptance: 26/26 PASS
- Bounded Context ownership: 21/21 PASS
- Current bounded-context routes: 247
- Legacy API: 181/181 contracts preserved

## Security / operations / build

- API authorization: 317 guarded human-facing routes + 5 explicit system exceptions
- Docker static security: 38/38 PASS
- Compose/runtime security: 119/119 PASS
- Enterprise Security: 23/23 PASS
- Observability: 16/16 PASS
- Corporate Deployment: 13/13 PASS
- Game Day: 15/15 PASS
- UX: 9/9 PASS
- deterministic secret scan: 0 committed secret candidates
- Python compileall: PASS
- shell syntax: 28/28 PASS
- Compose YAML parse: 19/19 PASS
- build preflight: PASS; plain `docker compose build` supported

## Supply chain

- SBOM: 37 declared components
- BUILD_INPUTS: 95 file inputs + 14 image refs
- 80 file inputs present/hashed
- 7 expected corporate lock/wheelhouse artifacts absent
- status: **CONDITIONAL**
- `production_authorized=false`

Missing/target-owned evidence includes frontend package-lock/offline npm cache, core/ai/advanced hashed Python locks and wheelhouse manifests, immutable image digests, offline OS bundle/install receipt and corporate CVE/SCA/image approval.

## Not claimed as executed

This source/package verification does **not** claim:

- WORM/immutable-storage enforcement against privileged administrators;
- HSM/KMS/private-key custody or corporate key ceremony;
- target-host 15/30/100-user load certification;
- live host/DB/evidence failover drill;
- measured production RTO/RPO;
- Docker Engine/BuildKit runtime acceptance in this packaging environment;
- corporate CVE/SCA/image approval;
- human Production GO.

## Package integrity

Final clean-tree payload: **941 files**. Final ZIP members: **942** including `BUILD_MANIFEST.json`. Independent ZIP→manifest verification: **941/941 PASS**; missing 0, extra 0, size mismatch 0, SHA-256 mismatch 0; `unzip -t` PASS.
