# MGC Engineering AI Local v6.3.15 — Verification

## Release boundary

- Application: **6.3.15**
- Database schema: **6.3.13**
- DB migration: **none**
- Scope: operational resilience, graceful optional-dependency degradation and self-diagnostics; engineering authority unchanged

## Executed backend regression

The final source tree was exercised in independently terminating pytest groups to avoid the known monolithic packaging-runtime shutdown coupling.

- collected inventory: **453 tests in 88 test files**;
- completed backend regression: **453/453 PASS**;
- completed test files: **88/88**;
- failures: **0**;
- new v6.3.15 Operational Resilience unit tests: **6/6 PASS**.

The run exposed two compatibility assertions and both were resolved and rerun:

1. a legacy readiness test used a partial Settings stub with no v6.3.15 policy field; v6.3.15 now preserves fail-closed behavior for such legacy/partial configuration objects while the real Settings explicitly selects brownout semantics;
2. the v6.0.8 support-bundle test required an exact four-file archive; it was updated for the additive privacy-safe `resilience.json` diagnostic artifact.

## Static / architecture gates

- Operational Resilience & Self-Diagnostics: **23/23 PASS**
- Data Consistency & DR: **45/45 PASS**
- Architecture Simplification: **27/27 PASS**
- Dependency Profiles: **18/18 PASS**
- Ports & Adapters: **25/25 PASS**
- Projection Reliability: **26/26 PASS**
- Domain Integrity: **25/25 PASS**
- Revision & Conflict: **28/28 PASS**
- Approval & Release Governance: **28/28 PASS**
- Enterprise Identity: **38/38 PASS**
- Release Handover Safety: **46/46 PASS**
- Data Lifecycle: **33/33 PASS**
- Performance & Scale: **18/18 PASS**
- Read Models & Cache: **22/22 PASS**
- Workload Isolation: **29/29 PASS**
- Execution Recovery & Job Lease Safety: **35/35 PASS**
- Supply-chain structural/fail-closed compatibility: **27/27 PASS**
- Bounded Context ownership: **21/21 PASS**, **247 routes**
- Legacy API contract: **181/181 method/path contracts preserved**

## Security / build gates

- Docker static security: **38/38 PASS**
- Compose/runtime security: **108/108 PASS**
- Enterprise Security: **23/23 PASS**
- API authorization: **310 guarded human-facing routes**, 4 explicit system exceptions
- Observability: **16/16 PASS**
- Corporate Deployment: **13/13 PASS**
- Game Day: **15/15 PASS**
- UX: **9/9 PASS**
- Build preflight: **PASS**; plain `docker compose build` remains supported
- Python `compileall`: **PASS**
- shell `bash -n`: **PASS**
- Compose YAML parse: **15/15 PASS**
- deterministic source secret scan: **0 committed secret candidates**

## Resilience invariants verified at source/unit/static level

- circuit-breaker state is explicitly non-authoritative and process-local;
- PostgreSQL/evidence storage remain the engineering sources of truth;
- Qdrant open/failure state falls back to PostgreSQL lexical discovery;
- Qdrant indexing failure cannot make authoritative document ingestion fail solely because the projection is unavailable;
- LLM open/failure state allows evidence-only RAG output instead of fabricated synthesis;
- VLM open/failure state preserves deterministic drawing analysis;
- native CAD gateway failure is isolated from BOM/WI/document/Digital Thread access;
- Redis/Celery publish is breaker-protected while managed job state remains PostgreSQL-ledgered;
- open optional circuits drive BROWNOUT diagnostics rather than engineering decision automation;
- half-open probing is bounded to one in-flight probe per process;
- support bundle exposes sanitized resilience state without raw engineering content or secrets;
- strict optional-dependency readiness remains explicitly configurable for corporate policy.

## Supply-chain status

The source package remains **CONDITIONAL**, not production-authorized. Approved npm lock/cache, exact hashed Python locks/wheelhouses, immutable image digests, offline OS bundle/install receipt and approved CVE scanner evidence must be supplied by the corporate build environment.

## Not claimed as executed here

- real Docker Engine/BuildKit image build and container runtime acceptance;
- production `npm ci --offline` from approved cache and resolved Python wheelhouse installation;
- corporate source/dependency and built-image CVE/SCA acceptance;
- live Redis/Qdrant/model-server/CAD-gateway fault injection under 15/30/100-engineer representative load;
- multi-replica circuit-breaker behavior and orchestrator readiness policy certification;
- target PostgreSQL backup → restore/PITR rehearsal and measured production RPO/RTO;
- live corporate OIDC/PKI/mTLS negative tests;
- production PLM/PDM/ERP/MES/QMS reconciliation;
- controlled UAT / human Production GO.

## Package integrity

The final release package is rebuilt after documentation/SBOM generation. `BUILD_MANIFEST.json` is intentionally excluded from its own file-hash inventory and the final ZIP is independently rehashed against the manifest after packaging.
