# MGC Languages v6.0.2 — Frontend Error Boundary

## Goal

Make browser failures visible and diagnosable during the office pilot without sending user data or secrets anywhere automatically.

## Placement

`error_boundary.js` loads immediately after `frontend/runtime.js` and before the historical `app.js`, so it can capture failures from both legacy and modular frontend code.

## Behavior

- captures global `error` events;
- captures `unhandledrejection` events;
- stores at most 20 recent events in memory only;
- marks `data-mgc-frontend="degraded"`;
- shows one non-blocking service-status notice when the status module is available;
- exposes `MGCFrontend.get('error-boundary').snapshot()` for local diagnostics;
- `clear()` drops the in-memory buffer.

## Privacy

Diagnostics are not persisted and are not uploaded automatically.

The scrubber redacts:
- Authorization Bearer values;
- `mgc_session` and `mgc_csrf` values;
- password/token/secret query-style values;
- URL query strings and fragments.

No cookies, localStorage, sessionStorage, beacon, fetch or XHR are used by the error boundary.

## Compatibility

- UI flows are unchanged.
- API/ORM/Alembic are unchanged.
- `static/app.js` remains unchanged.
- authentication/session behavior from v6.0.1 is unchanged.
- learning, XP, games and Putonghua content are unchanged.
