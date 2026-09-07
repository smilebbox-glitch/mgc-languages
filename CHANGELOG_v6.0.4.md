# v6.0.4 — Frontend Practice & Games Module

- Added `static/frontend/practice_games.js` as canonical active owner for `roleplay`, `games`, and `xp` views.
- Preserved pilot feature gating for `games` and `xp_economy` with the same disabled-feature error semantics.
- Modular navigation now delegates owned practice views before falling back to historical `setView`.
- Capture-phase interception prevents duplicate legacy click rendering.
- Historical `renderRoleplay`, `renderGames`, and `renderXP` remain staged fallback only; `static/app.js` is unchanged.
- No backend API, ORM, Alembic, content or runtime APP_VERSION changes.
