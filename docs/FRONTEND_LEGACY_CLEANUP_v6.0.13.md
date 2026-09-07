# Frontend Legacy Cleanup — v6.0.13

## Goal

v6.0.13 starts retiring the historical `static/app.js` runtime surface after the modular extraction work completed in v6.0.3–v6.0.12.

The release deliberately does **not** delete `app.js` wholesale. Core learning and practice screens still depend on legacy renderers, and session/language lifecycle still uses shared historical primitives. The safe boundary is therefore: stop exposing and executing the parts that already have canonical modular owners, while preserving the parts that still have real dependencies.

## Compatibility bridge after v6.0.13

`static/frontend/legacy_bridge.js` remains the single adapter around historical globals. Its allowed surface is now restricted to:

### Shared lifecycle / utility primitives
- state access
- boot and static-event binding
- auth UI configuration
- legacy fallback `setView`
- language loading
- show/hide app and auth shells
- mobile menu closing
- Putonghua standard banner
- session IDs and practice-result helper
- service status and toast
- HTML escaping and DOM query helpers

### Learning renderers still awaiting migration
- `renderHome`
- `renderTopics`
- `renderQuiz`
- `renderCourse30`

### Practice renderers still awaiting migration
- `renderRoleplay`
- `renderGames`
- `renderXP`

Manager/Admin renderers are no longer exported by the bridge.

## Runtime retirement boundary

`static/frontend/legacy_retirement.js` loads after all replacement owner modules and before canonical navigation.

It requires these replacement owners to exist before retirement:

- `support-notifications`
- `assistant-knowledge`
- `final-assessment`
- `content-governance`
- `admin-ops`
- `admin-analytics`
- `manager-admin`
- `chinese-reference`

If any owner is missing, retirement fails fast instead of silently disabling a fallback.

## Retired globals

The release retires 24 historical globals at runtime:

### Notifications
- `renderNotifications`
- `saveNudgeSettings`

### Assistant / Knowledge
- `renderAssistant`
- `askAssistant`
- `renderKnowledge`

### Final Assessment
- `renderExam`
- `startExam`
- `answerExam`

### Manager
- `renderManager`
- `openManagerUser`

### Admin / Governance / IT
- `renderAdmin`
- `itDashboardHTML`
- `pilotGovernanceHTML`
- `bindPilotGovernance`
- `learningErrorTelemetryHTML`
- `bindITDashboard`
- `questionQualityHTML`
- `adminTermCard`
- `adminContentHTML`
- `bindAdminContent`
- `openAdminUser`

### Chinese Reference / Tone Lab
- `toneLabStart`
- `renderToneLabRound`
- `renderChineseBasics`

These names are set to `undefined` only after their canonical replacement modules have loaded.

## Why physical deletion is deferred

`static/app.js` is still responsible for pieces that have not yet been fully extracted. Deleting broad source ranges now would couple unrelated migrations and increase regression risk. v6.0.13 therefore separates two concepts:

1. **Runtime retirement:** completed for superseded feature globals.
2. **Physical source deletion:** deferred until learning/practice renderers and shared lifecycle primitives have been migrated.

This creates a measurable no-return boundary without making the cleanup unsafe.

## Regression protection

`tests/v613_frontend_legacy_cleanup_test.py` verifies:

- script order: replacement owners → retirement → navigation;
- retirement module is loaded exactly once;
- all required replacement owners are declared;
- superseded globals are listed for retirement;
- learning/practice renderers are explicitly *not* retired;
- Manager/Admin exports are absent from the compatibility bridge;
- bridge surface is bounded to 24 entries;
- historical declarations remain in `app.js` for staged source cleanup;
- `node --check` passes for the changed compatibility scripts.

## Next migration boundary

The next meaningful reduction is to migrate one of the two remaining renderer families out of `app.js`:

- learning: `home/topics/quiz/course30`, or
- practice: `roleplay/games/xp`.

Once both families and shared lifecycle primitives are modular, `static/app.js` can be physically replaced by a much smaller shell rather than merely runtime-retired.
