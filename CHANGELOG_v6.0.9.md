# MGC Languages v6.0.9 — Admin Content Governance

- Added `static/frontend/content_governance.js` as the canonical terminology/content-governance module.
- Preserved admin/editor role boundaries; approve/reject remains Admin-only.
- Extracted taxonomy, terms and question-quality loading to the modular API client/shared state.
- Extracted manual term publishing and XLSX/CSV import with CSRF-aware `FormData` handling.
- Extracted submit-review, approve, reject and revision-history actions.
- Editor `admin` view now renders directly through the content-governance module.
- Full Admin / Analytics keeps its existing layout while its terminology helpers/actions are supplied by modular adapters.
- Pilot governance, IT dashboard, maintenance, analytics and telemetry are intentionally unchanged.
- Added v6.0.9 release shard, static preflight and dedicated CI workflow.
- Backend API/OpenAPI, ORM/Alembic, Putonghua content, XP rules and runtime APP_VERSION are unchanged.
