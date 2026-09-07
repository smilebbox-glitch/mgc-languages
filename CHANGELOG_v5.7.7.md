# MGC Languages v5.7.7 — Service Layer

## Goal

Continue decomposing the legacy `app.py` by moving reusable business logic into explicit service modules while preserving every public API route, ORM schema, security contract and UI behavior.

## New service boundary

`mgc.services.users` owns the production implementations for:

- stable public user serialization (`user_view`);
- Admin user learning/gamification summary aggregation (`user_admin_stats`);
- manager-to-target department access policy (`_manager_target_allowed`).

`mgc.services.terminology` owns the production implementations for:

- custom-term API projection (`custom_term_view`);
- combined built-in + published corporate terminology queries (`terms_for` / `term_by_id`);
- immutable term snapshots;
- sequential terminology revision recording;
- Admin terminology response projection.

Both modules are dependency-injected and do not import `app.py`.

## Runtime binding strategy

`mgc_core.service_bridge` validates the existing ORM/helper contract and rebinds the legacy module globals to the extracted service functions. Existing FastAPI endpoint objects are not replaced: their normal Python global lookups resolve the service implementations at request time.

The modular runtime order is now:

1. security primitives;
2. RLS/audit governance;
3. user/terminology services;
4. auth/session dependency rebinding;
5. route-contract validation.

The service layer intentionally binds before auth so `mgc.auth_core.create_login_session` captures the extracted `user_view` implementation.

## Compatibility preserved

v5.7.7 does not change:

- API paths, HTTP methods or route objects;
- JSON field names for user/admin/terminology responses;
- role/department access semantics;
- built-in language dictionaries or Putonghua learning standard;
- custom-term publication filtering;
- term revision numbering/snapshot format;
- RLS, audit-chain, auth/session or CSRF behavior;
- Alembic schema/head;
- frontend assets.

No database migration is required.

## Regression gates

The `v577` shard contains:

- a dependency-light service-core test using isolated SQLAlchemy models and no `app.py` import;
- a live ASGI integration test proving service binding, auth capture ordering, Admin user stats, published terminology lookup, update/revision history and manager department policy.

Docker CI additionally asserts `SERVICE_BINDING_REPORT.ok` and the critical user/terminology bindings before runtime smoke.

## Next extraction

The next low-risk step is to extract learning/gamification orchestration (`get_profile`, XP award/spend, SRS scheduling and practice result workflows) behind a learning service boundary, then reduce the remaining legacy helper surface progressively.
