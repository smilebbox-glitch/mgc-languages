# MGC Languages v5.9.1 — Notifications Router Extraction

## Goal

Move notification settings and learning-nudge HTTP ownership out of the historical FastAPI monolith without changing notification timing, user preferences, feature flags or read-state behavior.

## Extracted routes

`mgc.routers.notifications` owns four authenticated routes:

- `GET /api/notifications/settings`
- `PUT /api/notifications/settings`
- `GET /api/notifications/pending`
- `POST /api/notifications/{nudge_id}/read`

## Runtime contract

`mgc_core.notifications_router_bridge` verifies fail-closed:

- exact four-route contract;
- extracted Auth Core `current_user` dependency;
- extracted Learning Service `get_profile` dependency used by nudge scheduling;
- exact `NotificationSettingsPayload` schema;
- route-name and response-class parity;
- root StaticFiles ordering;
- endpoint ownership by `mgc.routers.notifications`.

Historical handlers remain in `mgc/legacy_app.py` as migration fallback. Production `asgi:app` replaces the active APIRoutes with the extracted router.

## Behavior preserved

- modes: `off`, `minimal`, `normal`, `active`;
- HH:MM notification windows;
- browser notification preference;
- feature-flag behavior for `learning_nudges`;
- existing gentle-return/review-due scheduling logic;
- maximum three nudges without activity;
- pending list limit and ordering;
- per-user nudge ownership;
- read-state persistence;
- auth and CSRF semantics.

## Verification

New `v591` shard covers:

- dependency-light exact route contract;
- strict settings schema validation;
- anonymous `401`;
- settings GET/PUT persistence;
- invalid settings `422`;
- pending-nudge visibility;
- read mutation and missing-nudge `404`;
- database persistence;
- OpenAPI path preservation.

## Compatibility

No DB schema/Alembic change, no API URL change, no runtime `APP_VERSION` bump, no frontend/content change. Putonghua (普通话) remains the primary Chinese-learning standard.

This is a stacked refactor over v5.9.0 and must not be merged into `main` until the preceding stacked chain and full CI/Docker are green.
