# Frontend Content Governance — v6.0.9

## Purpose

Separate terminology/content-governance behavior from the historical `static/app.js` without rewriting unrelated Admin / Analytics domains in the same release.

## Canonical module

`static/frontend/content_governance.js`

The module owns the terminology workflow and adaptive question-quality content signal. It uses the shared frontend `api-client`, `app-state`, error boundary and existing toast/navigation facades.

## Role model

- **Editor / Language Expert**: `manager_admin.js` routes the `admin` view directly to `content-governance.renderEditor()`.
- **Admin**: keeps the full Admin / Analytics page. The historical renderer still assembles pilot/IT/analytics sections, but its content helpers are replaced by the v6.0.9 module adapters.
- **Other users**: remain blocked by the existing manager/admin access guard.

Approve/reject buttons are rendered only when `role === 'admin'` and the term is in `review` status.

## Extracted behavior

- taxonomy (`levels`, `shops`, `topics`)
- governed term list
- question-quality signal
- manual term publication
- XLSX/CSV import using `FormData`
- submit for review
- Admin approve/reject
- revision/review history lookup
- source metadata and document reference fields

## Preserved API contract

No endpoint contract changes were introduced. The module continues using the existing `/api/admin/...` routes for taxonomy, terms, import, review actions and revision history.

## Staged compatibility

The historical `adminContentHTML`, `bindAdminContent`, `adminTermCard` and `questionQualityHTML` declarations remain in `static/app.js`. On module load, v6.0.9 stores these functions as fallbacks and installs equivalent modular adapters on the global bindings. This lets the existing full Admin renderer consume the new content-governance implementation without a one-shot rewrite.

## Intentionally deferred

The following remain separate for a later admin-domain extraction:

- pilot governance/groups/features/assignments
- IT dashboard
- cleanup/maintenance
- alert acknowledgement
- learning-error telemetry
- aggregate admin analytics/users

## Verification

`tests/v609_frontend_content_governance_test.py` guards script order, role boundaries, endpoints, FormData import, review workflow, adapter installation and JavaScript syntax. The shard is integrated into `scripts/run_release_tests.py`, `scripts/static_preflight.py` and `.github/workflows/ci-v609.yml`.
