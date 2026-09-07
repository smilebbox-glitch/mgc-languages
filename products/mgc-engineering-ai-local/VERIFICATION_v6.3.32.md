# Verification — MGC Engineering AI Local v6.3.32

## Release identity

- Application: **6.3.32**
- Database schema: **6.3.13**
- New DB migration: **none**
- Release theme: **Resilience Certification & Recovery Baselines**
- `production_authorized=false`

## Backend regression

Full regression completed before release packaging:

- **668/668 PASS**
- **105/105 test files**
- failures: 0
- errors: 0

Deterministic group results: `150 + 70 + 202 + 246 = 668`.

## Resilience certification & recovery baselines

- Resilience Certification preflight: **18/18 PASS**
- Resilience Drill preflight: **13/13 PASS**
- signed live drill baseline contract: PASS
- approved campaign contract: PASS
- per-scenario RTO comparison: PASS
- aggregate RTO comparison: PASS
- ratio regression detection: PASS
- absolute regression detection: PASS
- RTO ceiling enforcement: PASS
- missing mandatory scenario detection: PASS
- bootstrap/simulation cannot satisfy release GO: PASS
- invalid/tampered signature fails closed: PASS
- current evidence profile/tier must exactly match approved baseline/campaign: PASS
- baseline must be exactly the adjacent previous patch (`6.3.31`): PASS
- deploy guard recomputes certification from signed evidence + baseline + campaign: PASS
- report-only GO cannot satisfy deployment gate: PASS
- automatic threshold relaxation forbidden: PASS
- automatic production authorization forbidden: PASS
- emergency rollback remains ungated: PASS
- no DB migration: PASS

Default recovery regression policy used by the reference campaign is bounded by `max_rto_ratio=1.20`, `max_absolute_increase_seconds=5.0`, and `rto_ceiling_seconds=120.0`; production policy remains a human-approved campaign artifact rather than a runtime self-tuning value.

## Real detached-signature E2E

A temporary RSA keypair outside the package was used only for verification. The sequence below completed successfully:

1. sign v6.3.31 live baseline evidence with detached OpenSSL SHA-256 signature;
2. verify signature and promote human-approved recovery baseline;
3. create human-approved v6.3.32 drill campaign;
4. sign v6.3.32 live drill evidence;
5. certify current RTO against baseline;
6. receive `GO` for improved `api_instance_loss 10.0s → 8.0s` and `worker_cpu_loss 12.0s → 10.0s`;
7. pass `resilience_release_guard.py` with the complete signed source bundle;
8. confirm that report-only invocation is rejected fail-closed.

No private key is included in the source package or evidence.

## Full operational verification

`./mgcctl verify --scope full --json` clean-scope release target:

- **25/25 PASS**
- Docker static security
- Compose security
- API access
- Enterprise security
- secret scan
- Architecture Simplification
- Bounded contexts
- Ports & Adapters
- Domain Integrity
- Rolling Upgrade
- Blue/Green
- Application HA
- DB/Evidence HA
- Multi-host
- Production Certification
- Production Load Certification
- Automated Release Acceptance
- Acceptance Evidence Registry
- External Trust/Retention
- Real Integration Certification
- Integration Runtime Assurance
- Target-Host Deployment Assurance
- Production Observability / Incident Evidence
- Resilience Drill Orchestration
- Resilience Certification & Recovery Baselines

Rolling/Blue-Green adjacent compatibility is **6.3.31 ↔ 6.3.32** with schema **6.3.13**. Two-patch rollback remains fail-closed.

## Static verification

- Python `compileall`: **PASS**
- shell syntax: **30/30 PASS**
- Compose YAML parse: **19/19 PASS**
- Legacy API baseline: **181/181 preserved**
- Current bounded-context routes: **247**

## Supply-chain status

- BUILD_INPUTS provenance entries: **152/152 validated**
- source-package inputs present: **145/152**
- intentionally missing corporate build artifacts: **7**
- immutable image digest refs available in this build environment: **0/14**
- SBOM: **37 components**
- status: **CONDITIONAL**
- `production_authorized=false`

The seven missing artifacts are the approved frontend `package-lock.json` plus profile-specific Python hashed lock and wheelhouse manifests for `core`, `ai`, and `advanced`. Immutable corporate image digests, offline OS-package receipts and CVE/SCA approvals must be produced on the target corporate build environment.

## Package integrity

Independent clean-tree archive audit:

- controlled payload files: **1064**
- ZIP members including `BUILD_MANIFEST.json`: **1065**
- missing: **0**
- extra: **0**
- duplicate members: **0**
- size mismatch: **0**
- SHA-256 mismatch: **0**
- cache/generated artifacts: **0**
- symlinks: **0**
- ZIP CRC: **PASS**

The final package is rebuilt after this evidence update and must reproduce the same membership/hash invariants.

## Safety boundary

A resilience certification `GO` is a technical release gate, not production authorization. It does not perform fault injection itself, relax approved thresholds, claim root cause, alter engineering data, or approve a go-live. Human change/release approval remains required.
