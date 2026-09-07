# Frontend Admin Analytics — v6.0.11

## Purpose

v6.0.11 removes the remaining active Admin / Analytics orchestration from the historical `static/app.js` path. The Admin role now renders through `static/frontend/admin_analytics.js`, while previously extracted domains remain independent modules.

## Composition

The active Admin surface is composed from four frontend modules:

1. `admin-analytics`
   - loads the full Admin read model
   - renders KPI/telemetry overview
   - renders IT observability/recovery presentation
   - renders aggregated learning-error telemetry
   - renders Admin user list and user learning detail
2. `admin-ops`
   - renders Pilot Governance
   - binds rollout/member/feature/assignment mutations
   - binds maintenance and alert acknowledgement actions
3. `content-governance`
   - renders terminology governance
   - renders question-quality signals
   - binds create/import/review/approve/reject/history actions
4. `manager-admin`
   - owns the `admin` route and enforces role access
   - dispatches Admin to `admin-analytics`
   - dispatches Editor to `content-governance`

## Data contract

`admin-analytics.load()` preserves the previous Admin request set:

- `/api/admin/analytics`
- `/api/admin/users`
- `/api/admin/taxonomy`
- `/api/admin/terms`
- `/api/admin/pilot-telemetry`
- `/api/admin/it-dashboard`
- `/api/admin/learning-error-telemetry`
- `/api/admin/pilot/governance-summary`
- `/api/admin/pilot/groups`
- `/api/admin/pilot/features`
- `/api/admin/learning/question-quality`

User drill-down continues to use `/api/admin/users/{id}/learning-stats`.

## IT dashboard ownership

The active IT dashboard presentation now lives in `admin_analytics.js`. It preserves:

- readiness state
- recovery state
- DB latency
- active alerts
- availability/error-rate/p95 SLO values and targets
- DB query p95 and slow-query count
- DB pool saturation
- backup age/evidence
- restore rehearsal evidence
- schema head
- TTS/circuit state
- HTTP 5xx count
- RPO/RTO targets
- alert cards and acknowledge controls
- slow-query fingerprints without SQL or parameters
- maintenance preview/run controls
- recent operational events

The mutation handlers for maintenance and alerts remain in `admin-ops`, keeping presentation and actions separated.

## Learning analytics

`learningErrorTelemetryHTML()` is now modular and continues to show aggregated accuracy, previous-period accuracy, error count, users with errors and weak topics. It remains a content-quality/learning signal rather than an HR suitability score.

## Role model

- `admin`: full Admin / Analytics surface.
- `editor`: Content Governance only.
- `manager`: department-scoped manager surface only.
- other roles: blocked from management surfaces.

## Staged fallback

Historical `renderAdmin`, `itDashboardHTML`, `learningErrorTelemetryHTML` and `openAdminUser` declarations remain in `static/app.js` for rollback compatibility. The active Admin route no longer calls legacy `renderAdmin()`.

## Verification

The v6.0.11 contract test verifies script ordering, module registration, all Admin read endpoints, IT/recovery presentation markers, user drill-down, role routing, absence of active legacy `renderAdmin()` delegation and JavaScript syntax checks.
