# v6.0.7 — Frontend Final Assessment

- Added `static/frontend/final_assessment.js` as the canonical owner of the `exam` view.
- Preserved the 50-question A1–C1 final exam and 35/50 pass threshold.
- Preserved final-exam loading through `/api/language/{language}/final-exam`.
- Preserved answer feedback, live score, retry flow and completion state.
- Preserved result submission to `/api/final-exam/result`.
- Preserved practice/XP registration and language summary refresh after completion.
- Extended the legacy bridge only with `newSessionId` and `submitPractice` compatibility helpers.
- Added navigation, boot and script-order integration plus v6.0.7 regression/CI coverage.
- Historical exam functions remain staged fallback definitions in `static/app.js`.
- Backend API, ORM/Alembic, Putonghua content, XP rules and runtime APP_VERSION are unchanged.
