# MGC Languages v5.8.8 — User & Manager Router Extraction

## Goal

Move user administration and manager-team HTTP ownership out of the historical FastAPI monolith while preserving the extracted authentication, user-service and governance semantics.

## Extracted active routes

`mgc.routers.users_manager` now owns:

- `GET /api/admin/users`
- `GET /api/admin/users/{user_id}/learning-stats`
- `PATCH /api/admin/users/{user_id}/role`
- `PATCH /api/admin/users/{user_id}/department`
- `GET /api/manager/team`
- `GET /api/manager/team/{user_id}/learning-stats`

The historical endpoint implementations remain in `mgc/legacy_app.py` as migration fallback. Production `asgi:app` replaces the six active `APIRoute` objects in-place.

## Runtime binding

`mgc_core.user_manager_router_bridge` fails closed unless:

- `current_user` and `require_roles` come from `mgc.auth_core`;
- `user_view`, `user_admin_stats` and manager department policy come from `mgc.services.users`;
- `audit_event` comes from the extracted governance core;
- `UserRolePayload` and `UserDepartmentPayload` schemas match the legacy models exactly;
- all six route names and response classes are preserved;
- all six routes remain before the root `StaticFiles` mount.

## RBAC preserved

- user listing/statistics and role/department mutation: `admin` only;
- manager team/statistics: `manager` or `admin`;
- manager department boundary remains unchanged;
- an admin still cannot demote their own admin role through this panel.

## Verification

New `v588` release shard covers:

- dependency-light exact six-route contract;
- payload validation contract;
- live route ownership and mount ordering;
- normal-user `403` on admin routes;
- admin role/department mutation;
- self-demotion protection;
- manager same-department visibility;
- cross-department manager `403`;
- extracted User Service identity;
- extracted Governance/Audit identity and persisted audit events;
- OpenAPI path preservation.

Docker CI additionally asserts all v5.8.8 binding-report fields.

## Compatibility

No intentional changes to:

- URL paths or HTTP methods;
- response formats;
- role names or authorization policy;
- manager department policy;
- audit event types;
- database schema or Alembic head `c57d0a31f570`;
- runtime `APP_VERSION` fallback;
- UI or language content;
- Chinese learning standard: Путунхуа (普通话).

## Stacked-PR note

This increment is intentionally stacked on v5.8.7 while GitHub-hosted Actions are not provisioning runner steps. Do not merge it to `main` until the v5.8.5 → v5.8.6 → v5.8.7 chain has been revalidated and merged in order, and v5.8.8 itself has passed full CI/Docker.
