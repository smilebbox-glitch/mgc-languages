# v5.9.9 — Frontend Modularization: Shell Boundary

- Added `static/frontend/runtime.js` with a fail-closed frontend module registry and diagnostics.
- Added `static/frontend/boot.js` to expose the historical bundle through a stable `legacy-app` adapter.
- Registered department-aware authentication as the first independent frontend module.
- Fixed deterministic browser asset ordering: runtime → legacy app → auth module → boot bridge.
- Added explicit DOM/runtime contract checks and `mgc:frontend-ready` event.
- Added `v599` release shard and focused frontend CI gate.
- Kept `static/app.js` unchanged in this increment; no UI/API/schema/content behavior change.
- Alembic head and runtime APP_VERSION remain unchanged.
