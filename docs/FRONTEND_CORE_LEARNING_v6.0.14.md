# Frontend Core Learning — v6.0.14

## Purpose

v6.0.14 converts the `learning` module from a navigation wrapper into the canonical implementation of the four core learning views:

- `home`
- `topics`
- `quiz`
- `course30`

The historical implementations remain physically declared in `static/app.js` only as staged rollback material. They are no longer part of the active compatibility surface and are retired at runtime after the modular owner is present.

## Home

The modular Home view preserves:

- language-specific hero (`English` / `Путунхуа`)
- pilot cohort and assigned track information
- nudge card open/dismiss behavior
- XP overview when `xp_economy` is enabled
- A1–C1 learning level selector
- professional topic cards
- summary progress for terms, 30-day course and final exam
- Putonghua learning-standard banner through the shared banner primitive

## Topics

The Topics surface preserves two states:

1. topic catalogue
2. selected-topic term detail

Selected-topic data continues to use:

`GET /api/language/{language}/terms?topic={topic}&limit=500`

The A1–C1 client-side filter and pronunciation buttons are preserved.

## Quiz

The modular quiz preserves:

- topic selector
- A1–C1 level selector
- maximum 10-question request
- pronunciation / reading presentation
- answer feedback
- retry flow
- scenario handoff
- one practice session per completed quiz
- XP helper purchases

Data contracts:

- `GET /api/language/{language}/quiz?topic=...&level=...&count=10`
- `POST /api/gamification/spend`
- existing `submitPractice('quiz', ...)` compatibility primitive

XP audio help deliberately reuses the existing shared pronunciation primitive so the server-voice/browser-fallback policy does not diverge between modules.

## 30-day course

The module preserves:

- 30-day progress overview
- day selection
- daily term list
- pair exercise
- roleplay handoff
- five-question daily test
- 4/5 pass threshold
- persisted daily result
- practice XP
- summary refresh after a passed day

Data contracts:

- `GET /api/language/{language}/course30`
- `POST /api/course-day/result`
- existing `submitPractice('pair', ...)`
- existing `submitPractice('course_day', ...)`

## Language switching and Pinyin

Two shell interactions are captured by `learning.js` in the capture phase:

- `[data-language]`
- `#pinyinToggle`

This is required because the historical target listeners call legacy `setView()` / `renderView()`. Once the core learning globals are retired, allowing those old handlers to execute would re-enter the retired renderer path.

The modular language switch:

1. updates `app-state`
2. resets language-specific learning/session state
3. persists `/api/me/language`
4. reuses the shared language-data loader
5. navigates through canonical modular navigation to `home`

The modular Pinyin toggle:

1. persists `/api/learning/preferences`
2. updates body/toggle presentation
3. rerenders the current view through canonical navigation

## Legacy boundary after v6.0.14

Removed from `legacy_bridge.js`:

- `renderLearningHome`
- `renderLearningTopics`
- `renderLearningQuiz`
- `renderLearningCourse30`

Newly retired runtime globals include:

- `renderHome`
- `renderTopics`
- `renderQuiz`
- `startQuiz`
- `answerQuiz`
- `buyQuizHelp`
- `renderCourse30`
- `makePairOptions`
- `answerPair`
- `renderDayQuiz`
- `answerDayQuiz`

Practice remains staged:

- `renderRoleplay`
- `renderGames`
- `renderXP`

These are the next renderer family to migrate before physical deletion of large sections from `static/app.js`.

## Compatibility

v6.0.14 does not change:

- backend routes or OpenAPI
- ORM models
- Alembic schema/head
- Chinese/Putonghua source content
- XP/SRS rules
- notification backend
- final exam rules
- runtime APP_VERSION

## Verification

Release-specific verification is defined in:

- `tests/v614_frontend_core_learning_test.py`
- shard `v614` in `scripts/run_release_tests.py`
- `scripts/static_preflight.py`
- `.github/workflows/ci-v614.yml`

The historical v6.0.3 and v6.0.13 regression contracts are also advanced so they require the stricter post-extraction architecture rather than the now-obsolete staged legacy-renderer bridge.
