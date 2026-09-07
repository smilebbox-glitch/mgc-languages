# v6.0.14 — Core Learning Extraction

- `home`, `topics`, `quiz` and `course30` now render directly inside `static/frontend/learning.js`.
- Removed active `renderLearning*` compatibility dependencies from `legacy_bridge.js`.
- Preserved Topics/Terms, Quiz, XP-help, 30-day course, daily tests and practice XP API contracts.
- Added modular language switching and Pinyin preference rerender so legacy `renderView()` is not re-entered by those controls.
- Added shared pronunciation bridge access for XP audio help while audio remains a shell-level primitive.
- Retired superseded core-learning globals at runtime after the modular learning owner loads.
- Practice renderers (`roleplay`, `games`, `xp`) remain the only feature renderer family still exposed through the legacy bridge.
- Added v6.0.14 regression shard, static preflight integration and dedicated CI.
- Backend API/OpenAPI, ORM/Alembic, Putonghua content, XP/SRS rules and runtime APP_VERSION are unchanged.
