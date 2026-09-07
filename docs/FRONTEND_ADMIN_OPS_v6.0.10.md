# Frontend Admin Operations — v6.0.10

## Purpose

v6.0.10 separates high-risk administrative operations from the historical `static/app.js` without changing backend contracts or rebuilding the full Admin / Analytics screen in one release.

The new `static/frontend/admin_ops.js` module owns the operational behavior for Pilot Governance and IT administration.

## Pilot Governance

The module now owns the complete pilot-governance UI block and its actions:

- governance summary and quotas;
- groups and waves;
- rollout status and start/end dates;
- group membership add/remove;
- per-group feature flags;
- learning-track assignments;
- assignment removal;
- pilot CSV export links.

All mutations continue to use the existing `/api/admin/pilot/...` endpoints through the shared CSRF-aware `api-client`.

## IT Admin

The existing IT dashboard renderer remains staged as the presentation source because it contains a large observability/recovery view that is already stable and independent from the mutation handlers.

The modular `admin-ops` module now owns the active IT control bindings:

- maintenance cleanup preview (`dry_run=true`);
- maintenance cleanup execution (`dry_run=false`);
- operational alert acknowledgement.

This removes active write behavior from the legacy IT handlers while avoiding a risky observability-markup rewrite.

## Authorization

`admin_ops.js` performs its own role check and allows only `admin`.

This preserves the existing separation:

- `admin` — full Admin / Analytics, Pilot Governance and IT operations;
- `editor` — content governance only;
- `manager` — department team view only.

## Compatibility strategy

The module captures the historical helpers as fallbacks and then installs modular adapters for:

- `pilotGovernanceHTML`;
- `bindPilotGovernance`;
- `itDashboardHTML`;
- `bindITDashboard`.

`admin_ops.js` loads after `content_governance.js` and before `manager_admin.js`, so the existing Admin renderer resolves the modular helpers when it builds and binds the page.

## Verification

The v6.0.10 contract test checks:

- script ordering;
- Admin-only access;
- pilot group/member/feature/assignment endpoints;
- maintenance cleanup dry-run and execution;
- alert acknowledgement;
- adapter installation;
- staged legacy fallbacks;
- JavaScript syntax.

`ci-v610.yml` runs the v6.0.9 and v6.0.10 frontend shards plus parity guards.

## Deferred work

A later release can extract the remaining IT dashboard presentation/observability markup and aggregate admin analytics renderer once the operational bindings have proven stable behind the new boundary.
