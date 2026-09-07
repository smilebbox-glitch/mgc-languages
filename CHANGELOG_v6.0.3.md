# v6.0.3 — Frontend Learning Module

- Added `static/frontend/learning.js` as canonical active owner for `home`, `topics`, `quiz`, and `course30` navigation.
- Modular navigation routes owned learning views through the new module.
- Capture-phase interception prevents duplicate legacy click rendering for owned views.
- Existing legacy render functions remain staged fallback only; `static/app.js` is not rewritten in this increment.
- Putonghua banner, loading/error UI, topic selection, quiz reset and session/navigation behavior are preserved.
- No backend API, ORM, Alembic, content or runtime APP_VERSION changes.
