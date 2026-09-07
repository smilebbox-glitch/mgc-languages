# v6.0.2 — Frontend Error Boundary & Diagnostics

- Added an in-memory global JS error/unhandled-rejection boundary before `app.js`.
- Added bounded 20-event local diagnostics with secret/query scrubbing.
- Frontend enters `degraded` state instead of silently failing.
- No diagnostics are persisted or uploaded automatically.
- Added v602 Node runtime privacy regression and focused CI gate.
- API, ORM, Alembic, session semantics, learning content and Putonghua scope are unchanged.
