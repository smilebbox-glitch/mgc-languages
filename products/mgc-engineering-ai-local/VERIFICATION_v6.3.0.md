# MGC Engineering AI Local v6.3.0 — Verification

## Executed in packaging environment

- affected backend pytest: **26/26 PASS**;
- context ownership/decomposition: **21/21 PASS**;
- legacy API contract + additive v6.3 surface: **5/5 PASS**;
- architecture simplification/runtime composition: **27/27 PASS**;
- dependency profile/lazy optional dependencies: **18/18 PASS**;
- frontend TSX syntax transpile: **PASS**;
- Docker static security: **38/38 PASS**;
- Compose/access/runtime security: **PASS**;
- enterprise security: **23/23 PASS**;
- corporate deployment: **13/13 PASS**;
- observability/reliability: **16/16 PASS**;
- operations game day: **15/15 PASS**;
- UX acceptance: **9/9 PASS**;
- build preflight: **PASS**;
- API authorization: **248 human-facing routes guarded; 4 explicit exceptions**.

## v6.3 invariants verified

- workspace is strictly manufacturing-area scoped;
- source-document visibility is fail-closed;
- foreign source and Russian translation are distinct records/views;
- engineering tokens are checked for preservation in translation;
- foreign WI translation review is required for complete/approvable state;
- Core optional-dependency isolation remains intact;
- all 181 v6.2.0 method/path contracts remain present; v6.3 adds 12 APIs.

## Required on corporate build/target host

A real `docker compose build`, complete dependency resolution/lock, CVE/image scan, full backend test suite, OIDC/TLS negative tests, DB migration rehearsal, backup→restore, representative document parsing, approved local-model translation quality/UAT and station/layout engineering UAT remain mandatory. Packaging checks do not authorize production deployment.
