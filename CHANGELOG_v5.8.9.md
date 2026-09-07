# MGC Languages v5.8.9 — Pilot Administration Router Extraction

## Goal

Move pilot rollout/governance HTTP ownership out of the historical FastAPI monolith while preserving existing pilot groups, waves, feature flags, assignments, quotas, CSV export, RBAC and audit semantics.

## Extracted active routes

`mgc.routers.pilot_admin` owns 13 admin-only routes:

- `GET /api/admin/pilot/groups`
- `POST /api/admin/pilot/groups`
- `PATCH /api/admin/pilot/groups/{group_id}/status`
- `PATCH /api/admin/pilot/groups/{group_id}`
- `POST /api/admin/pilot/groups/{group_id}/members/{user_id}`
- `DELETE /api/admin/pilot/groups/{group_id}/members/{user_id}`
- `GET /api/admin/pilot/features`
- `POST /api/admin/pilot/features`
- `PUT /api/admin/pilot/groups/{group_id}/features/{flag_key}`
- `POST /api/admin/pilot/groups/{group_id}/assignments`
- `DELETE /api/admin/pilot/groups/{group_id}/assignments/{assignment_id}`
- `GET /api/admin/pilot/export.csv`
- `GET /api/admin/pilot/governance-summary`

Historical handlers remain in `mgc/legacy_app.py` as migration fallback. Production `asgi:app` replaces the active APIRoutes in-place.

## Runtime binding

`mgc_core.pilot_admin_router_bridge` fails closed unless:

- `require_roles` comes from `mgc.auth_core`;
- `user_admin_stats` comes from the extracted User Service;
- `audit_event` comes from the extracted Governance Core;
- all six pilot payload schemas match the legacy Pydantic models exactly;
- all 13 route names/response classes are preserved;
- all routes stay before the root StaticFiles mount;
- endpoint ownership is `mgc.routers.pilot_admin`.

Binding counters:

- 13 total routes;
- 9 group-related routes;
- 2 feature-catalog routes;
- 2 assignment routes;
- 1 export route;
- 1 governance-summary route;
- 9 state-changing routes.

## Verification

New `v589` release shard covers:

- dependency-light exact 13-route contract;
- exact six-payload validation contracts;
- live ownership and mount ordering;
- non-admin `403`;
- group creation, duplicate-name and invalid-date guards;
- member add/remove;
- custom feature upsert and group override;
- track assignment create/delete;
- status/update lifecycle;
- UTF-8 CSV export and Putonghua column preservation;
- governance summary;
- persisted pilot audit event types;
- OpenAPI path preservation.

Docker CI also checks every v5.8.9 binding invariant.

## Compatibility

No intentional changes to:

- API paths/methods or response formats;
- admin-only RBAC;
- pilot group/wave rules;
- feature-flag semantics;
- track assignments;
- quotas;
- CSV headers/UTF-8 BOM;
- audit event types;
- database schema or Alembic head `c57d0a31f570`;
- runtime `APP_VERSION` fallback;
- UI/content;
- Chinese standard: Путунхуа (普通话).

## Stacked-PR note

This increment is intentionally stacked on v5.8.8 while GitHub-hosted Actions are not provisioning runner steps. Do not merge it into `main` until v5.8.5 → v5.8.8 have been revalidated and merged in order, then re-run the full v5.8.9 CI/Docker pipeline against `main`.
