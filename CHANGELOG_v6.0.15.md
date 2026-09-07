# v6.0.15 — Practice / Games / XP Extraction

- `practice-games` now implements `roleplay`, `games` and `xp` directly instead of delegating to `static/app.js` renderers.
- Preserved scenario progress, practice XP awards and Putonghua learning banner behavior.
- Preserved four game modes: Word Match, Listening Sprint, Phrase Builder and Find the Mistake.
- Preserved server-side game start/finish scoring and anti-farming semantics.
- Preserved XP profile, reward catalogue and reward-spend flows.
- Removed `renderPracticeRoleplay`, `renderPracticeGames` and `renderPracticeXP` from `legacy_bridge.js`.
- Added runtime retirement for superseded roleplay/game/XP globals.
- Advanced v6.0.4, v6.0.13 and v6.0.14 regression contracts to the stricter post-extraction architecture.
- Added v6.0.15 release shard, static preflight integration and dedicated CI.
- Backend APIs, database schema, Putonghua content and runtime APP_VERSION are unchanged.
