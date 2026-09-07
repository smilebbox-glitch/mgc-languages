# Frontend Final Assessment — v6.0.7

## Purpose

Move active final-exam ownership out of the historical `static/app.js` dispatch path without changing the backend contract or the learner-facing exam semantics.

## Owned view

`static/frontend/final_assessment.js` canonically owns:

- `exam`

`static/frontend/navigation.js` delegates that view to the module before the legacy fallback.

## Preserved exam contract

The module keeps the existing final assessment behavior:

- 50 questions total;
- 10 questions each for A1, A2, B1, B2 and C1;
- pass threshold of 35/50;
- Chinese pronunciation line when supplied by the question payload;
- immediate correct/wrong answer feedback and explanation;
- live score and progress;
- retry after completion.

## API flow

Starting the exam uses:

`GET /api/language/{language}/final-exam`

Completing question 50 preserves the historical completion flow:

1. `POST /api/final-exam/result` with language, score, total and answers array.
2. Submit a practice result through the historical `submitPractice` helper so XP/profile behavior stays unchanged.
3. Refresh `/api/language/{language}/summary` and store it in shared frontend state.

## Compatibility boundary

`legacy_bridge.js` exposes `newSessionId` and `submitPractice` because those helpers still contain shared historical session/XP behavior. They are compatibility primitives, not exam view owners.

The old `renderExam`, `startExam` and `answerExam` functions remain in `static/app.js` as staged fallback definitions. This keeps the refactor reversible while the new module is validated.

## Verification

`tests/v607_frontend_final_assessment_test.py` verifies ownership, script order, endpoints, pass/total constants, result submission, practice integration, summary refresh, navigation delegation, boot registration and staged legacy parity.

The v6.0.7 shard is also included in `scripts/static_preflight.py` and `.github/workflows/ci-v607.yml`.
