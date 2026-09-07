# MGC Languages v5.7.5 — Auth & Session Core

## Goal

Continue decomposition of the legacy `app.py` without changing public API, database schema, cookie semantics or the user interface.

## New boundary

`mgc.auth_core` is the model-aware authentication/session implementation. It does not import `app.py`; instead the current ORM models and DB/RLS hooks are injected explicitly while those definitions still live in the legacy module.

It owns the production implementations for:

- current authenticated-user lookup;
- expired-session rejection and cleanup;
- RLS identity hook after authentication;
- role dependencies (`user` / `manager` / `editor` / `admin` policies);
- login-session creation;
- `mgc_session` and `mgc_csrf` cookie issuance.

## FastAPI compatibility strategy

FastAPI captures `Depends(...)` callables when routes are declared. Reassigning `app.current_user` after import would therefore leave existing routes on the legacy dependency.

`mgc_core.auth_bridge` uses FastAPI's supported `application.dependency_overrides` mechanism instead:

1. discover captured legacy `current_user` dependencies;
2. discover captured `require_roles(...)` closures and their role tuples;
3. install extracted replacements for every captured dependency;
4. bind the extracted `create_login_session` to the module global used by login/register/OIDC endpoint bodies;
5. fail closed if the expected dependency graph cannot be found or an override conflicts.

This keeps route objects and OpenAPI/API paths unchanged while production `asgi:app` executes the extracted auth/session core.

## Compatibility contracts

v5.7.5 preserves:

- session cookie name: `mgc_session`;
- CSRF cookie name: `mgc_csrf`;
- configured SameSite/Secure flags;
- session TTL behavior;
- SHA-256 token digest from `mgc.security`;
- 401 messages for missing/not-found/expired sessions and missing users;
- 403 message for insufficient role permissions;
- expired-session deletion;
- RLS context binding after user resolution.

No Alembic migration is required.

## Regression gates

The `v575` shard contains:

- a dependency-light core test using isolated SQLAlchemy models and no `app.py` import;
- a live ASGI integration test proving dependency rebinding, registration, session expiry cleanup, ordinary-user Admin denial and Admin authorization.

Docker CI additionally asserts the auth binding report before runtime smoke.

## Next extraction

The next low-risk modular step is to move RLS context and audit/session maintenance helpers behind a database/security service boundary, then begin physical removal of the corresponding fallback implementations from `app.py` once the connector workflow supports a safe large-file patch path.
