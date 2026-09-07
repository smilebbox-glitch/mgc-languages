# MGC Languages v6.0.0 — Frontend API & State Core

## Goal

Reduce coupling to the historical `static/app.js` without rewriting the whole UI in one risky change.

## Runtime order

1. `frontend/runtime.js`
2. `app.js`
3. `frontend/legacy_bridge.js`
4. `frontend/service_status.js`
5. `frontend/api_client.js`
6. `frontend/app_state.js`
7. `frontend/navigation.js`
8. `auth_department.js`
9. `frontend/boot.js`

## New canonical modules

- `legacy-app`: compatibility boundary around historical globals.
- `service-status`: status banner facade.
- `api-client`: JSON/CSRF/session-aware HTTP client.
- `app-state`: shared state facade with `mgc:state-change` events.
- `navigation`: app/auth visibility and home navigation facade.

`auth-department` is the first user-facing module migrated to the new core. It no longer falls back to direct `api`, `state`, `showApp`, `loadLanguage` or `setView` globals.

## Compatibility

- `static/app.js` is unchanged.
- UI layout and routes are unchanged.
- API/OpenAPI/ORM/Alembic are unchanged.
- Existing login + department behavior is preserved.
- XP/SRS/games/notifications/admin/content are unchanged.
- Chinese learning standard remains Putonghua (普通话).

## Next extraction slices

1. logout/session bootstrap;
2. games/practice frontend;
3. learning/course frontend;
4. notifications;
5. admin/terminology.
