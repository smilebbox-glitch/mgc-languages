# MGC Languages v5.7.2 — Technical hardening

This engineering increment reduces regression risk before further feature growth. It does not change the database schema and does not alter the learning UX.

## 1. API architecture contract

`scripts/api_contract_guard.py` statically inspects `app.py` and fails CI when it detects:

- duplicate FastAPI method/path registrations;
- disappearance of critical health/auth/meta endpoints;
- `/api/admin/*` routes without an explicit `require_roles(...)` dependency;
- state-changing routes outside `/api/`;
- unreviewed drift of the CSRF exemption allowlist;
- API routes declared after the root static-file mount;
- growth of the current backend/frontend monolith beyond hard safety budgets.

The current large-file limits are deliberately temporary. Soft-budget warnings are already emitted for `app.py` and `static/app.js`; new functionality should be extracted into modules rather than expanding those files indefinitely.

## 2. Language content integrity

`scripts/content_integrity_guard.py` validates both `data/english.json` and `data/chinese.json` before a build is accepted:

- top-level structure and non-empty datasets;
- required term fields;
- unique term IDs;
- supported CEFR-style levels;
- Chinese pinyin sanity;
- example coverage signals;
- duplicate semantic term/translation pairs as review warnings.

This is intentionally a structural/technical quality gate. Linguistic correctness still requires editorial review and the existing content-governance workflow.

## 3. CI isolation

A new `v572` regression shard runs the architecture and content-integrity tests independently. Static preflight also executes both guards, so malformed content or unsafe route changes fail early before Docker image creation.

The CI image tag is now version-neutral (`mgc-languages:ci`) to avoid stale release numbers in build plumbing.

## 4. Next decomposition target

After this guard is stable, the recommended refactor order is:

1. extract environment/config parsing from `app.py`;
2. extract database models/session setup;
3. extract auth/security middleware and dependencies;
4. extract learning/SRS/game routers;
5. extract admin/operations routers;
6. split `static/app.js` by feature domain while preserving the current UI.

Each extraction should keep endpoint contracts unchanged and run the full shard matrix before merge.
