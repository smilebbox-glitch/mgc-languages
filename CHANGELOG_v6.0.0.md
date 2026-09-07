# v6.0.0 — Frontend API & State Core

- Added modular frontend compatibility bridge around the historical bundle.
- Added canonical service-status, API client, app-state and navigation modules.
- Migrated department-aware auth to the new frontend core.
- Preserved CSRF, 401 re-authentication, DB-unavailable status and login semantics.
- Added deterministic asset order, v600 regression shard and focused CI gate.
- No API, ORM schema, Alembic, learning content or Putonghua changes.
- Runtime `APP_VERSION` remains unchanged for compatibility.
