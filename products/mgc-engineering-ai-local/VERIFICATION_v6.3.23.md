# MGC Engineering AI Local v6.3.23 — Verification

## Release contract

- Application: **6.3.23**
- Database schema: **6.3.13**
- New DB migration: **none**
- Theme: Automated Release Acceptance Pipeline

## Backend regression

Final inventory: **558 tests / 96 test files**.

Non-overlapping repository-root runs completed with explicit pytest summaries:

- 87/87 PASS
- 48/48 PASS
- 17/17 PASS
- 39/39 PASS
- 71/71 PASS
- 56/56 PASS
- 76/76 PASS
- 92/92 PASS
- 72/72 PASS

Total: **558/558 PASS**, failures **0**, errors **0**, skipped **0**.

## v6.3.23 release-acceptance gate

Automated Release Acceptance Pipeline preflight: **26/26 PASS**.

Focused acceptance/load/production-certification/rolling/blue-green regression: **62/62 PASS**.

Cryptographic E2E used ephemeral RSA keys and completed this flow:

1. canonical load evidence;
2. detached load signature;
3. first signed release acceptance (`technical_decision=GO`, release decision `CONDITIONAL` because no approved baseline);
4. explicit human-approved signed bootstrap baseline;
5. second signed acceptance using verified baseline;
6. relative regression checks PASS;
7. technical release decision `GO`;
8. `production_authorized=false` remained unchanged.

Ephemeral private keys and generated E2E evidence are not release artifacts.

## Architecture / reliability gates

- Architecture Simplification: 27/27 PASS
- Dependency Profiles: 18/18 PASS
- Ports & Adapters: 25/25 PASS
- Projection Reliability: 26/26 PASS
- Domain Integrity: 25/25 PASS
- Revision & Conflict: 28/28 PASS
- Approval & Release Governance: 28/28 PASS
- Enterprise Identity: 38/38 PASS
- Release Handover: 46/46 PASS
- Data Lifecycle: 33/33 PASS
- Performance & Scale: 18/18 PASS
- Read Models & Cache: 22/22 PASS
- Workload Isolation: 29/29 PASS
- Job Execution Recovery: 35/35 PASS
- Data Consistency / DR: 45/45 PASS
- Operational Resilience: 23/23 PASS
- Rolling Upgrade: 37/37 PASS
- Blue/Green Cutover: 40/40 PASS
- Application HA: 41/41 PASS
- Database/Evidence HA: 45/45 PASS
- Multi-host Topology: 30/30 PASS
- Production Certification & SLO: 22/22 PASS
- Production Load Certification: 24/24 PASS
- Automated Release Acceptance: 26/26 PASS
- Bounded Contexts: 21/21 PASS, **247** bounded-context routes
- Legacy API contract: **181/181** method/path contracts preserved

## Security / operations / build

- Docker static security: 38/38 PASS
- Compose/runtime security: 119/119 PASS
- Enterprise Security: 23/23 PASS
- API authorization: **316** human-facing routes guarded; **5** explicit system exceptions
- Observability: 16/16 PASS
- Corporate Deployment: 13/13 PASS
- Game Day: 15/15 PASS
- UX: 9/9 PASS
- Build preflight: PASS; plain `docker compose build` remains supported
- Python compileall: PASS
- Shell syntax: **28/28 PASS**
- Compose YAML: **19/19 PASS**
- deterministic secret scan: **0** committed secret candidates

## Supply-chain evidence

- SBOM: **37** declared components
- BUILD_INPUTS: **87** tracked file inputs + **14** immutable-image references
- Present/hashed file inputs: **80**
- Missing corporate artifacts: **7**
  - frontend/package-lock.json
  - backend/locks/requirements-core.lock.txt
  - backend/wheelhouse/core/WHEELHOUSE_MANIFEST.json
  - backend/locks/requirements-ai.lock.txt
  - backend/wheelhouse/ai/WHEELHOUSE_MANIFEST.json
  - backend/locks/requirements-advanced.lock.txt
  - backend/wheelhouse/advanced/WHEELHOUSE_MANIFEST.json
- Current supply-chain status: **CONDITIONAL**
- `production_authorized`: **false**

No dependency hashes, immutable image digests, package locks, wheelhouse manifests or CVE evidence were fabricated.

## Release-acceptance semantics

A technical release `GO` now requires both the absolute v6.3.21/v6.3.22 SLO/capacity gates and the relative v6.3.23 regression gate against a trusted approved baseline. Missing baseline is `CONDITIONAL`; an invalid/tampered/unapproved baseline or a material performance regression is fail-closed `NO_GO`.

Approved baseline promotion remains a separate explicit human action. Same-release baseline is rejected except the explicitly confirmed sequence-1 bootstrap path for initial adoption.

Release-acceptance evidence is canonical-hashed and may be detached-signed. Acceptance chain entries include sequence + parent acceptance digest. Chain verification rejects broken parent, sequence, digest or signature.

## Not claimed in this environment

The following are not claimed as completed here:

- live 15/30/100-engineer target-host load certification;
- real corporate performance baseline approval;
- real multi-host/external-LB host loss under concurrent load;
- real PostgreSQL primary/standby promotion under load;
- evidence-storage replication failover under load;
- measured production RTO/RPO;
- corporate CVE/image acceptance;
- human Production GO.

## Final package integrity

Clean release-tree payload: **926 files**. Independent ZIP-to-manifest verification confirmed **926/926 payload files PASS**; ZIP members: **927** including `BUILD_MANIFEST.json`; missing: **0**; extra: **0**; size mismatch: **0**; SHA-256 mismatch: **0**; cache/test/private-key artifacts: **0**; `unzip -t`: **PASS**. The distributed `.sha256` file is authoritative for the final archive digest.
