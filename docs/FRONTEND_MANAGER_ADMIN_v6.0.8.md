# Frontend Manager & Admin Boundary — v6.0.8

## Purpose

Reduce `static/app.js` ownership of management navigation without combining a large governance rewrite with the manager-dashboard extraction.

## Canonical ownership

`static/frontend/manager_admin.js` owns:
- `manager`
- `admin`

The module is loaded before `navigation.js`, intercepts its owned `[data-view]` actions in capture phase, and applies role checks before rendering.

## Manager view

The manager view is fully rendered by the modular frontend:
- role must be `manager`;
- `/api/manager/team` loads the department-scoped roster;
- `/api/manager/team/{id}/learning-stats` loads the selected employee learning detail;
- shared `managerTeam` state is updated via `app-state`;
- XP remains explicitly presented as motivational activity rather than professional-performance evaluation.

No cross-department scope is added by this frontend extraction; backend authorization remains authoritative.

## Admin view

The Admin / Analytics screen is structurally larger than the manager screen. It includes terminology/content governance, user analytics, pilot groups/waves/feature flags, IT telemetry, learning-error telemetry, alerts and maintenance actions.

v6.0.8 therefore moves the **route and access boundary** into `manager_admin.js` while preserving the existing `renderAdmin` implementation behind `legacy_bridge.renderAdmin`. This is deliberate staged migration rather than a partial rewrite of governance behavior.

Role parity remains:
- `admin`: full Admin / Analytics behavior;
- `editor`: content-oriented admin behavior already defined by the historical renderer;
- all other roles: denied.

## Compatibility

The historical `renderManager` and `renderAdmin` functions remain in `static/app.js` as staged fallback/compatibility definitions. The active manager view no longer requires the historical renderer, while the active admin view still delegates rendering through the bridge until a later admin-domain extraction.

Backend routes, database schema, Alembic head, Putonghua learning content, XP rules and runtime `APP_VERSION` are unchanged.

## Verification

`tests/v608_frontend_manager_admin_test.py` verifies:
- script order and one-time module load;
- owned views and capture-phase interception;
- manager/admin/editor role boundaries;
- manager team and learning-stat API contracts;
- modular manager shared-state update;
- staged `renderAdmin` bridge contract;
- navigation and boot integration;
- preservation of major admin endpoint strings and historical helpers;
- JavaScript syntax.
