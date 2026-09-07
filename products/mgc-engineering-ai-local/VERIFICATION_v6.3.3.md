# MGC Engineering AI Local v6.3.3 — Verification

## Scope

Database & Domain Integrity Hardening on top of v6.3.2 Transaction & Projection Reliability and v6.3.0 Manufacturing Work Instructions & Station Intelligence.

## Executed checks

- Complete backend inventory executed in eight shards: **362/362 PASS** across **76** test files.
- Changed-surface regression (v6.3.0 Work Instructions, v6.3.1 Ports, v6.3.2 projections, v6.3.3 integrity, Engineering Change, BOM compare, Project Workspace): **40/40 PASS**.
- Domain Integrity preflight: **25/25 PASS**.
- Architecture Simplification: **27/27 PASS**.
- Dependency Profiles: **18/18 PASS**.
- Bounded Context Router: **21/21 PASS**.
- API contract compatibility: **5/5 PASS**; **181/181** v6.2.0 legacy method/path contracts preserved; v6.3.0 additive routes retained.
- Ports & Adapters: **25/25 PASS**.
- Projection Reliability: **26/26 PASS**.
- Docker/Dockle-style static security: **38/38 PASS**.
- Compose/access/runtime security: **100/100 PASS**.
- Enterprise Security: **23/23 PASS**.
- Corporate Deployment: **13/13 PASS**.
- Observability: **16/16 PASS**.
- Game Day: **15/15 PASS**.
- UX acceptance: **9/9 PASS**.
- API authorization preflight: **253** guarded human-facing routes; **4** explicit machine/health exceptions.
- Deterministic secret scan: **0** committed candidates.
- Plain `docker compose build` build-context preflight: **PASS**.

## v6.3.3 integrity evidence

Verified behavior includes:

1. stale Work Instruction `expected_version` is rejected with an edit conflict;
2. two concurrent SQLAlchemy sessions cannot produce a silent lost update;
3. domain update and audit event roll back together when a Unit of Work fails;
4. ChangeRequest creation rolls back if its hash-chained event cannot be persisted;
5. fresh schema rejects invalid station headcount and non-positive BOM quantity;
6. migration is additive/idempotent and records schema marker `6.3.3`.

## Packaging environment limitations

Frontend production `npm ci`/Vite build was not executed because this source snapshot has no approved `package-lock.json`/installed `node_modules`. Dependency-lock preflight therefore remains a warning until the corporate npm mirror and Python wheelhouse resolve/pin the approved dependency set.

Actual Docker image build, Dockle layer scan, Trivy/Grype scan, real PostgreSQL migration rehearsal and rollback, OIDC/PKI negative tests, backup→restore and controlled UAT remain target-host gates.
