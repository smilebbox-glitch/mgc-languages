# MGC Languages v5.8.7 — Users & Manager Router Extraction

## Summary

v5.8.7 moves user administration and manager-team HTTP ownership out of the historical FastAPI monolith and behind `mgc.routers.users_manager`.

The change is intentionally architectural. Existing user statistics, manager department policy, terminology lookup, audit behavior, authentication, database schema, UI and learning content remain unchanged.

## Extracted routes

The dedicated router now owns six active endpoints:

- `GET /api/admin/users`
- `GET /api/admin/users/{user_id}/learning-stats`
- `PATCH /api/admin/users/{user_id}/role`
- `PATCH /api/admin/users/{user_id}/department`
- `GET /api/manager/team`
- `GET /api/manager/team/{user_id}/learning-stats`

## Runtime binding

`mgc_core.users_manager_router_bridge` replaces the six historical APIRoutes in-place after the extracted auth, governance and service bindings have been installed.

The bridge fails closed if any of these contracts drift:

- exact path/method ownership;
- route names or response classes;
- `UserRolePayload` / `UserDepartmentPayload` schemas;
- root StaticFiles ordering;
- router endpoint module ownership;
- `mgc.auth_core` role dependency;
- `mgc.services.users` user serialization/statistics and manager policy;
- `mgc.services.terminology` terminology lookup;
- `mgc.governance_core` audit function.

## RBAC preserved

- Admin user listing, user learning stats, role mutation and department mutation remain Admin-only.
- Manager team views remain available to `manager` and `admin`.
- Managers remain restricted to employees in their own department.
- Admin continues to bypass the department boundary for management/support purposes.

## CI / release gates

A new `v587` regression shard covers:

- dependency-light exact six-route contract;
- payload validation;
- live ASGI route ownership;
- ordinary-user denial for admin/manager routes;
- manager denial for admin routes;
- manager own-department visibility;
- cross-department manager denial;
- admin cross-department visibility;
- OpenAPI path preservation.

Docker runtime binding assertions were moved from the oversized inline workflow expression into `scripts/verify_runtime_bindings.py`. The new script preserves all previous checks and adds v5.8.7 assertions.

## Compatibility

No change to:

- public API paths or methods;
- role names or department semantics;
- session/cookie/CSRF behavior;
- XP, SRS, games or terminology content;
- database schema;
- Alembic head `c57d0a31f570`;
- runtime `APP_VERSION` fallback;
- UI/front-end assets;
- Chinese learning standard: `Путунхуа (普通话)`.

## Stacking note

This increment is stacked on v5.8.6 while GitHub-hosted runners are unavailable. It must not be merged to `main` until v5.8.5 and v5.8.6 are merged in order and v5.8.7 is retargeted/revalidated against the resulting `main`.
