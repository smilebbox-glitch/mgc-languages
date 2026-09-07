# Frontend Chinese Reference — v6.0.12

## Purpose

v6.0.12 removes the active `chinese-basics` path from the historical frontend monolith and gives it a dedicated module. The module is intentionally a reference/foundations surface, not a second Chinese curriculum.

## Canonical owner

`static/frontend/chinese_reference.js`

Owned view:

- `chinese-basics`

Navigation is capture-phase owned, so the legacy `[data-view]` listener does not render the same view a second time.

## Availability contract

The module preserves both conditions used by the existing product:

1. The active language must be `chinese`.
2. Pilot feature `chinese_reference` must not be explicitly disabled.

If a non-Chinese session reaches the route, navigation returns to Home. If the pilot feature is disabled, the same pilot-gate error semantics are retained.

## Data contract

The module uses the existing endpoint only:

`GET /api/chinese/foundations`

The returned document is cached in shared frontend state as `chineseFoundations`, matching the historical state field.

No backend endpoint, OpenAPI contract, schema or migration is introduced by this release.

## Learning-standard rule

The main Chinese learning standard remains:

**Путунхуа (普通话)**

The reference surface repeats this explicitly because the same page also explains regional varieties. The product contract is:

- course lessons: Putonghua;
- quizzes: Putonghua;
- pronunciation/audio in the main track: Putonghua;
- XP activities: Putonghua unless a specific reference activity says otherwise;
- final exam: Putonghua;
- dialect/regional examples: reference only.

The existing `data/chinese_foundations.json` remains unchanged and continues to carry `learning_standard`, the 10-group reference classification, and comparison examples.

## Audio policy for regional examples

The comparison section deliberately renders audio only for each `standard` Putonghua example.

Regional variants display their original text, romanization system, approximate Russian reading and explanatory note, but the frontend does **not** synthesize them with the standard Mandarin TTS voice. This avoids teaching a false regional pronunciation.

## Tone Lab

Tone Lab is now owned by the module.

Behavior preserved:

- uses tones 1–4;
- creates a five-round deck;
- one answer per round;
- correct/wrong feedback;
- final score display;
- repeat action;
- practice kind `tone_lab`;
- topic `Pinyin · тоны`;
- XP goes through the existing practice result semantics.

The module calls the existing compatibility helper `submitPractice()` rather than duplicating XP/profile update logic.

## Presentation areas

The module renders the existing foundations data as:

- learning-standard banner;
- four introductory facts;
- Pinyin explanation;
- five tones;
- Tone Lab;
- initials;
- finals;
- starter automotive/workplace vocabulary;
- context/tone ambiguity examples;
- tone-change notes;
- short learning path;
- Putonghua explanation;
- workplace request to switch to Putonghua;
- 10 large dialect-group reference cards;
- accent vs dialect explanation;
- visual regional comparisons;
- reference FAQ and safety note.

## Staged rollback compatibility

The following historical declarations remain in `static/app.js`:

- `toneLabStart`
- `renderToneLabRound`
- `renderChineseBasics`

They are no longer the active `chinese-basics` path after the new module is registered, but they remain available for staged rollback until the frontend monolith cleanup phase.

## Verification

Release-specific checks:

- `tests/v612_frontend_chinese_reference_test.py`
- release shard `v612`
- `.github/workflows/ci-v612.yml`
- `scripts/static_preflight.py`

The contract test verifies module ownership, script order, navigation delegation, feature gating, foundations endpoint use, Tone Lab practice semantics, Putonghua standard data and the absence of regional audio flags in comparison variants.
