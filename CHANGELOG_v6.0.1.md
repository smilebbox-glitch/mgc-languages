# v6.0.1 — Frontend Session Lifecycle

- Added modular browser session bootstrap and logout ownership.
- Historical `DOMContentLoaded` boot listener is removed by exact function reference.
- `/api/meta`, `/api/me` and `/api/logout` now use the modular API client in the session lifecycle.
- Logout uses capture-phase interception to avoid the historical anonymous handler.
- Existing UI event bindings, local/OIDC auth configuration and navigation behavior are preserved.
- `static/app.js`, API, ORM, Alembic, learning content and Putonghua scope are unchanged.
