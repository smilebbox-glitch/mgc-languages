# v6.0.8 — Frontend Manager & Admin Boundary

- Added canonical frontend ownership for `manager` and `admin` views.
- Extracted manager team dashboard rendering to `static/frontend/manager_admin.js`.
- Preserved department-scoped manager access and `/api/manager/team` APIs.
- Preserved manager learning-stat drilldown and XP-as-motivation disclaimer.
- Added explicit role guards: `manager` for team view; `admin`/`editor` for admin view.
- Routed Admin / Analytics through the new module while keeping complex governance rendering behind the staged legacy adapter.
- Preserved existing admin analytics, taxonomy, terms, pilot governance, IT dashboard, telemetry and maintenance flows.
- Added navigation, boot and script-order integration.
- Added v6.0.8 regression shard, static preflight and dedicated CI workflow.
- Backend API/OpenAPI, ORM/Alembic, Putonghua content and runtime APP_VERSION are unchanged.
