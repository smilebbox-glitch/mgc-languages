# MGC Languages v5.8.5 — Terminology & Admin Router Extraction

## Summary

v5.8.5 moves corporate terminology HTTP ownership out of the historical monolith while preserving the already extracted terminology and governance service cores.

## Extracted route ownership

A new `mgc.routers.terminology_admin` APIRouter owns 13 active routes:

- `GET /api/language/{language}/topics`
- `GET /api/language/{language}/terms`
- `GET /api/admin/terms`
- `POST /api/admin/terms`
- `PATCH /api/admin/terms/{term_id}`
- `DELETE /api/admin/terms/{term_id}`
- `GET /api/admin/terms/{term_id}/revisions`
- `POST /api/admin/terms/{term_id}/submit-review`
- `POST /api/admin/terms/{term_id}/approve`
- `POST /api/admin/terms/{term_id}/reject`
- `POST /api/admin/terms/{term_id}/rollback/{revision_no}`
- `POST /api/admin/terms/import`
- `GET /api/admin/taxonomy`

The public terminology endpoints still require an authenticated user. Corporate terminology administration preserves the existing admin/editor/manager role matrix.

## Runtime binding

`mgc_core.terminology_admin_router_bridge` replaces the thirteen legacy APIRoutes in-place and fails closed if:

- the exact method/path contract drifts;
- extracted `current_user` / `require_roles` are not active;
- the v5.7.7 terminology service is not active;
- the v5.7.6 governance/audit service is not active;
- route names or response classes change;
- routes move behind the root StaticFiles mount;
- endpoint ownership is not `mgc.routers.terminology_admin`.

## Compatibility preserved

No intentional change to:

- API paths or HTTP methods;
- request payload validation;
- CSRF behavior;
- role-based authorization;
- term approval workflow;
- audit events and tamper-evident audit chain;
- revision history and rollback semantics;
- CSV/XLSX import limits and validation;
- public visibility of published custom terms;
- database schema or Alembic head `c57d0a31f570`;
- runtime `APP_VERSION` fallback;
- UI or language content;
- Putonghua learning standard.

## Test coverage

New `v585` release shard validates:

- dependency-light router import without `app.py` / `mgc.legacy_app`;
- exact thirteen-route contract;
- active ASGI ownership by the new router;
- extracted auth/terminology/governance binding order;
- normal-user public terminology access and admin `403`;
- taxonomy access;
- create → submit review → approve lifecycle;
- public visibility after approval;
- revision/review history;
- update → reject → rollback lifecycle;
- CSV import;
- deletion;
- OpenAPI path preservation.

The architecture guard now counts 41 router-owned routes.

## Scope intentionally left for later

General administration endpoints for users, pilot groups, feature flags, assignments, SLO/operations and audit dashboards remain in `mgc/legacy_app.py`. They are a separate administrative domain and will be extracted independently rather than coupled to terminology administration.
