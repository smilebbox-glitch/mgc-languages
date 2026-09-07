# MGC Languages v6.0.1 — Frontend Session Lifecycle

## Goal

Move browser session bootstrap and logout from the historical `app.js` API path onto the modular frontend core without rewriting the large legacy bundle.

## Bootstrap

The historical bundle still defines and registers `boot`, but `legacy_bridge.js` exposes the original callback reference. `session_lifecycle.js` removes that exact `DOMContentLoaded` listener and installs the modular bootstrap.

New flow:

1. `legacy.bindStaticEvents()` keeps existing UI event wiring.
2. `api-client` loads `/api/meta`.
3. `app-state` stores metadata.
4. legacy `configureAuthUi()` preserves local/OIDC UI semantics.
5. `api-client` loads `/api/me`.
6. `navigation.enterUserSession()` restores the authenticated UI or `showAuth()` is used when no valid session exists.

## Logout

`session_lifecycle.js` installs a capture-phase handler on `#logoutButton`. It stops the historical anonymous bubble handler, sends `POST /api/logout` through the modular CSRF-aware API client, clears frontend user state and returns to the auth view.

## Compatibility

- `static/app.js` remains unchanged.
- API/cookies/CSRF/session TTL are unchanged.
- Local auth and OIDC UI configuration are unchanged.
- No ORM or Alembic changes.
- Learning, XP, SRS, games and Putonghua content are unchanged.
