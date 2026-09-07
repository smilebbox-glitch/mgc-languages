# v6.0.10 — Pilot Governance & IT Admin

- Added `static/frontend/admin_ops.js` as the modular admin-operations boundary.
- Moved Pilot Governance rendering and mutations into the modular frontend.
- Preserved pilot groups, waves, members, feature flags, assignments, quotas and CSV export behavior.
- Moved maintenance cleanup preview/run and alert acknowledgement bindings into the modular frontend.
- Preserved the established IT dashboard renderer as a staged presentation fallback while removing its active mutation handlers from legacy ownership.
- Enforced Admin-only access inside the new module.
- Added error-boundary integration for pilot and IT administrative actions.
- Added v6.0.10 release shard, static preflight coverage and dedicated GitHub Actions workflow.
- Backend APIs, database schema, Alembic head, language content, XP/SRS and runtime APP_VERSION are unchanged.
