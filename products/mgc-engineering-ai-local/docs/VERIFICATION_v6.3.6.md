# MGC Engineering AI Local v6.3.6 — Verification

## Release scope
Enterprise Identity & Policy Enforcement on top of v6.3.5 Approval & Release Governance, v6.3.4 Revision/Conflict Management, v6.3.3 Domain Integrity, v6.3.2 Transactional Outbox, v6.3.1 Ports & Adapters and v6.3.0 Manufacturing Work Instructions / BOM Translation / Layouts.

## Executed automated checks
- v6.2.x–v6.3.6 cumulative + security/integration/change regression: **98/98 PASS**.
- v6.3.6 Enterprise Identity tests: **7/7 PASS** (included above).
- Architecture Simplification: **27/27 PASS**.
- Bounded Context Ownership: **21/21 PASS**.
- Legacy API contract: **5/5 PASS**; all **181/181** v6.2.0 method/path contracts preserved.
- Dependency Profiles: **18/18 PASS**.
- Ports & Adapters: **25/25 PASS**.
- Projection Reliability: **26/26 PASS**.
- Domain Integrity: **25/25 PASS**.
- Revision & Conflict Management: **28/28 PASS**.
- Approval & Release Governance: **28/28 PASS**.
- Enterprise Identity & Policy Enforcement: **38/38 PASS**.
- Docker static security: **38/38 PASS**.
- Compose/runtime security: **100/100 PASS**.
- Enterprise Security: **23/23 PASS**.
- API authorization: **277 human-facing routes guarded**, **4 explicit system exceptions**.
- UX acceptance: **9/9 PASS**.
- Observability: **16/16 PASS**.
- Corporate Deployment: **13/13 PASS**.
- Game Day static gate: **15/15 PASS**.
- deterministic secret scan: **0 committed secret candidates**.
- Python `compileall`: **PASS**.
- shell `bash -n`: **PASS**.
- Docker Compose YAML parse: **PASS**.
- plain `docker compose build` preflight: **PASS**.
- frontend TypeScript transpile: **PASS**.
- SBOM generated: **37 components**.

## Full backend inventory
The repository contains **383 collected backend tests in 79 test files**. A monolithic full run was attempted in the packaging runtime; it reached approximately **18%** with no assertion failure before the execution limit terminated the process. Because the process did not complete, **383/383 is not claimed** for this packaging environment.

The corporate build-host acceptance gate must run the entire 383-test inventory in an environment where worker/background runtimes can terminate cleanly.

## Identity/security invariants verified
- OIDC bearer tokens and raw claims are not stored in approval evidence.
- Approval evidence stores a sanitized identity/assurance snapshot.
- Service accounts cannot perform human approval, policy/delegation administration or Final Release.
- Identity-policy deny groups override allow groups.
- Production privileged actions can require OIDC, bounded `auth_time` age and accepted `acr` values.
- Delegation is limited to approval decisions, requires an explicit validity window/scope/reason and cannot delegate Engineering Admin authority.
- Delegation is usable only when both the approval stage and resolved identity policy permit it.
- Final Release remains Engineering Admin + maker-checker controlled.
- Release Manifest is canonical/hashable and performs no PLM/PDM/MES/PLC write-back.
- Qualified electronic signature is not claimed; bundled e-sign adapter is disabled.
- Optional PostgreSQL RLS is limited to identity-policy/delegation tables; existing Project/Area/Document ACL is unchanged.

## Supply-chain lock status
**WARN, intentionally not PASS.**
- `frontend/package-lock.json` is absent.
- backend Core/AI/Advanced requirement profiles contain declared version ranges.
- enterprise image build must resolve/pin packages through the approved npm mirror and Python wheelhouse, then execute SCA/CVE/image scans.

## Required corporate target-host gates
- full **383-test** backend run;
- real `docker compose build` for Core/AI/Advanced;
- reviewed PostgreSQL 6.3.5 → 6.3.6 migration rehearsal and backup/restore;
- actual corporate OIDC issuer/JWKS/claims/group mapping tests;
- negative OIDC tests: stale auth-time, wrong ACR, wrong audience/issuer, service-account privilege attempt;
- policy/delegation UAT for each participating manufacturing area;
- optional RLS test only after DBA/security approval of the PostgreSQL role model;
- PKI/e-sign adapter remains disabled unless separately approved/certified;
- CVE/SCA/container image scan;
- controlled UAT and Operations acceptance.

## Deployment authority
No readiness, policy or approval status produced by MGC constitutes automatic Production GO. Human corporate change approval, InfoSec/IAM/DBA acceptance, UAT and Operations acceptance remain mandatory.
