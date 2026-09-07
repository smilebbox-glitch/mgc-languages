# Frontend Physical Shell — v6.0.16

## Purpose

v6.0.16 converts `static/app.js` from the historical feature monolith into a small compatibility shell. All feature screens were already migrated to dedicated modules by v6.0.15; this release physically removes their duplicate implementations.

## Result

`static/app.js` now retains only shared primitives required by the current modular frontend:

- shared `state`
- auth/session fallback functions
- `loadLanguage()` bootstrap data
- modular `setView()` handoff
- role/feature visibility controls
- Putonghua learning banner
- `newSessionId()`
- `submitPractice()`
- pronunciation/audio fallback
- service-status/toast/DOM helpers

The compatibility bridge contains exactly 18 shared entries and no feature renderer adapters.

## Removed feature implementations

The shell no longer contains implementations for:

- Home / Topics / Quiz / Course30
- Roleplay / Games / XP
- Notifications
- Assistant / Knowledge
- Final Assessment
- Chinese Reference / Tone Lab
- Manager / Admin
- Content Governance
- Pilot Governance / IT operations UI
- Admin Analytics / user detail

Those features remain available through their dedicated `static/frontend/*.js` owners.

## Navigation

The shell's `setView()` is now a compatibility handoff only. It resolves an owning module and invokes that module's `navigate()` method. It does not contain a `renderView()` table or any renderer fallback.

## Lifecycle

`document.addEventListener('DOMContentLoaded', boot)` remains intentionally present because `session_lifecycle.js` removes that historical listener and installs the modular bootstrap. This preserves the staged lifecycle contract while allowing a later release to eliminate the remaining legacy lifecycle surface entirely.

## Audio and practice

`playPronunciation()` remains shared because multiple modules use the same server-audio/browser-speech fallback and cancellation semantics. `submitPractice()` and `newSessionId()` remain shared because quiz, daily course, Tone Lab, final assessment and roleplay need identical XP/idempotency semantics.

## Regression strategy

v6.0.16 advances older frontend tests rather than deleting them. Tests v6.0.3–v6.0.15 still verify their original module/API responsibilities, but now additionally require the superseded feature functions to be physically absent from `static/app.js`.

The dedicated `v616_frontend_physical_shell_cleanup_test.py` enforces:

- shell size below 30 KB
- exactly 18 bridge entries
- zero feature renderer functions in `app.js`
- modular-owner navigation handoff
- lifecycle compatibility
- JavaScript syntax for shell/bridge/retirement/session files

## Pilot implications

Feature extraction is complete after v6.0.16. The next frontend milestone is not another feature migration. It is a pilot-readiness gate covering real deployment, LAN access, role matrix, persistence, backup/restore, observability, browser compatibility and end-to-end user scenarios.

A successful v6.0.17 readiness gate should be treated as the pilot-candidate boundary rather than continuing indefinite frontend refactoring.
