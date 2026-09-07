# v6.0.11 — Admin Analytics & IT Dashboard

- Added `static/frontend/admin_analytics.js` as the canonical Admin / Analytics orchestration layer.
- Moved the active Admin data load to the modular API client across analytics, users, pilot telemetry, IT dashboard, learning-error telemetry, governance and content datasets.
- Moved KPI/telemetry rendering, learning-error telemetry, IT observability/recovery presentation and Admin user detail into the module.
- Composed Pilot Governance from `admin-ops` and terminology/question-quality from `content-governance`.
- `manager_admin.js` no longer calls legacy `renderAdmin()` for the Admin role.
- Preserved Editor-only Content Governance and Manager department-scoped behavior.
- Historical Admin functions remain in `static/app.js` as staged fallback definitions only.
- Added v6.0.11 regression shard, static preflight and dedicated GitHub Actions gate.
- Backend API/OpenAPI, database schema/Alembic, language content, XP/SRS, notifications and runtime application version are unchanged.
