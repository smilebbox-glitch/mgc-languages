# v6.0.16 — Physical Frontend Shell Cleanup

- Physically reduced `static/app.js` from the historical ~128 KB feature monolith to a ~19 KB shared compatibility shell.
- Removed all feature renderer implementations from `static/app.js`.
- Preserved only shared state/session, language loading, DOM helpers, service status, pronunciation/audio, practice XP and modular navigation handoff primitives.
- Kept the `legacy-app` bridge at exactly 18 shared entries; no feature renderer adapters remain.
- Advanced v6.0.3–v6.0.15 frontend contracts to require physical absence of superseded UI code.
- Added `v616_frontend_physical_shell_cleanup_test.py`, release shard, static preflight integration and dedicated CI.
- Backend APIs, OpenAPI, ORM/Alembic, Putonghua content, XP/SRS rules and runtime application version are unchanged.
- Next release target: pilot-readiness gate and deployment rehearsal.
