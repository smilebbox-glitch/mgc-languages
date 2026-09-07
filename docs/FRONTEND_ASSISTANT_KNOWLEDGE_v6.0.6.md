# Frontend Assistant & Knowledge — v6.0.6

## Purpose

Move the active AI assistant and practical knowledge-base views out of the historical frontend dispatcher while preserving existing language-learning behavior and backend contracts.

## Owned views

- `assistant`
- `knowledge`

## Assistant behavior

`assistant_knowledge.js` renders the language-aware automotive prompt examples, submits questions to `/api/assistant` through the modular API client, renders the returned answer/evidence safely, and preserves term/example pronunciation controls. The `ai_assistant` pilot feature gate remains authoritative.

## Knowledge behavior

The module loads `/api/knowledge?language=...`, caches items in shared app state, preserves topic filtering and detailed practical instructions, and keeps the target phrase, pronunciation, translation and audio actions. The detail view still hands the selected topic directly to `roleplay` for immediate practice.

## Compatibility

The module loads before `navigation.js` and captures owned `data-view` clicks before historical bubble handlers. Historical `renderAssistant`, `askAssistant`, `renderKnowledge` and `termCard` remain in `static/app.js` as staged fallback definitions.

No backend route, database schema, language content, Putonghua standard, XP/SRS logic, game flow or notification behavior is changed by this extraction.

## Verification

`tests/v606_frontend_assistant_knowledge_test.py` verifies script order, view ownership, AI/knowledge API contracts, feature gating, state ownership, audio controls, roleplay handoff and legacy fallback presence. The `v606` release shard and `ci-v606.yml` make these checks part of the release path.
