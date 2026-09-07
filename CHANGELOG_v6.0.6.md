# v6.0.6 — Frontend Assistant & Knowledge

- Added `static/frontend/assistant_knowledge.js` as the canonical active owner for `assistant` and `knowledge` views.
- The AI assistant now uses the modular CSRF-aware API client for `/api/assistant` while preserving automotive example prompts, evidence term cards and audio actions.
- The practical knowledge base now uses modular app state and `/api/knowledge`, preserving topic filters, detail instructions, avoid guidance, target phrases and audio playback.
- Preserved the `ai_assistant` pilot feature gate and existing disabled-feature semantics.
- Preserved the knowledge-to-roleplay handoff so a user can open a related practice scenario directly from an instruction.
- Navigation now delegates `assistant` and `knowledge` to `assistant-knowledge`; capture-phase interception prevents duplicate legacy rendering.
- Historical `renderAssistant`, `askAssistant`, `renderKnowledge` and `termCard` remain staged fallback definitions in `static/app.js`.
- Added v6.0.6 release shard, static preflight coverage and dedicated GitHub Actions contract checks.
- No backend API, ORM, Alembic, content, Putonghua standard, XP/SRS or runtime APP_VERSION changes.
