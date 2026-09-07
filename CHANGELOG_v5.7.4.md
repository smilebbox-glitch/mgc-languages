# MGC Languages v5.7.4 — Security Boundary

## Added

- `mgc.security`: dependency-light security primitives and policy helpers.
- `mgc_core.security_bridge`: fail-closed adapter that binds extracted primitives into the legacy FastAPI module for the ASGI runtime.
- Dedicated `v574` regression shard covering password compatibility, session digests, CSRF policy, role policy, response headers and live auth flows.
- Docker CI assertion that the security binding is active before runtime smoke testing.

## Preserved contracts

- Existing PBKDF2-SHA256 password format with 260,000 iterations and 16-byte random salts.
- Existing session-token SHA-256 digest format.
- Existing CSRF exemption allowlist and state-changing request behavior.
- Existing local registration/login/logout behavior, cookie names and session semantics.
- Existing OIDC role priority: admin, editor, manager, user.
- Existing manager department access rule.
- Existing response security headers.
- Existing API paths, database schema, migrations and UI.

## Architecture impact

Production Docker/uvicorn traffic already enters through `asgi:app`. v5.7.4 uses that stable boundary to bind extracted security primitives after the legacy module is imported but before requests are served. FastAPI route objects remain unchanged. This is an incremental migration step toward moving model-coupled authentication/session dependencies out of `app.py` in a later slice.

## Risk control

The bridge refuses to start if the legacy CSRF exemption allowlist differs from the extracted policy. This makes policy drift fail closed in CI/deployment rather than silently widening access.
