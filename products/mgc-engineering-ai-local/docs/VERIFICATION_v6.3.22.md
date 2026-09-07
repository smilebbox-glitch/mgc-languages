# MGC Engineering AI Local v6.3.22 — Verification

## Release contract

- Application: **6.3.22**
- Database schema: **6.3.13**
- New DB migration: **none**
- Theme: Production Load Certification Harness

## Backend regression

Final inventory: **542 tests / 95 test files**.

Eight non-overlapping repository-root groups completed with explicit pytest summaries:

- 87/87 PASS
- 48/48 PASS
- 57/57 PASS
- 71/71 PASS
- 55/55 PASS
- 69/69 PASS
- 89/89 PASS
- 66/66 PASS

Total: **542/542 PASS**, failures **0**, errors **0**, skipped **0**.

## v6.3.22 load-certification gate

Production Load Certification preflight: **24/24 PASS**.

Focused v6.3.21↔v6.3.22 compatibility regression: **47/47 PASS**.

Cryptographic E2E verification generated an ephemeral RSA key pair, signed canonical load evidence, verified it with the public key and allowed the signed measurements to contribute to a technical `GO`. The private key and generated test evidence are not release artifacts.

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
- Shell syntax: **29/29 PASS**
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

## Load-certification semantics

The default load plan is read-mostly and contains Object 360, BOM, Work Instructions, Digital Thread and RAG audited-read traffic. RAG POST operations require explicit opt-in. The harness records p50/p95/p99, request rate, error budget, DB-pool saturation and queue/workload safety measurements.

Generated load evidence is canonical-hashed. A detached OpenSSL signature must be verified with a supplied public key before that load evidence can participate in technical `GO`. Missing or unsigned load evidence remains `CONDITIONAL`; invalid/tampered evidence and mandatory SLO/saturation failures are fail-closed.

Technical `GO` still means `production_authorized=false` and requires an explicit human-approved change window.

## Not claimed in this environment

The following are not claimed as completed here:

- live 15/30/100-engineer target-host load certification;
- real corporate p50/p95/p99/throughput;
- real multi-host/external-LB host loss under concurrent load;
- real PostgreSQL primary/standby promotion under load;
- evidence-storage replication failover under load;
- measured production RTO/RPO;
- corporate CVE/image acceptance;
- human Production GO.

## Final package integrity

Clean release-tree payload: **906 files**. Final independent ZIP-to-manifest verification confirmed **906/906 payload files PASS**; ZIP members: **907** including `BUILD_MANIFEST.json`; missing: **0**; extra: **0**; size mismatch: **0**; SHA-256 mismatch: **0**; cache/test artifacts: **0**; `unzip -t`: **PASS**. The distributed `.sha256` file is authoritative for the final archive digest.
