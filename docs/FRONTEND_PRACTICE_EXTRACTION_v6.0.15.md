# Frontend Practice / Games / XP Extraction — v6.0.15

## Purpose

v6.0.15 completes feature-screen extraction from the historical `static/app.js` runtime by converting `static/frontend/practice_games.js` from a navigation wrapper into the canonical implementation for `roleplay`, `games` and `xp`.

## Roleplay

The module preserves the existing scenario contract:

- load scenarios from `/api/language/{language}/roleplays`;
- filter by topic;
- store per-user/per-language attempt history in local storage;
- reveal answer translations after selection;
- persist practice results through the shared `submitPractice` primitive;
- preserve server-controlled XP awards;
- preserve Putonghua banner behavior for Chinese practice.

## Games

The module preserves all four existing short-game modes:

1. Word Match
2. Listening Sprint
3. Phrase Builder
4. Find the Mistake

Session creation still uses `/api/games/{type}/start` and final scoring still uses `/api/games/{session_id}/finish`. The frontend does not calculate authoritative XP awards itself.

Listening continues to use the shared pronunciation layer, including the server-audio/browser fallback behavior already established by the product.

## XP economy

The XP screen now loads directly through the modular API client:

- `/api/gamification/me`;
- `/api/gamification/rewards`;
- `/api/gamification/spend`.

The learning-help reward set remains inline-only where appropriate. Other rewards can still return personalised packs or scenario material.

## Compatibility boundary

The following adapters are removed from `legacy_bridge.js`:

- `renderPracticeRoleplay`;
- `renderPracticeGames`;
- `renderPracticeXP`.

The bridge now contains only shared runtime primitives such as session/bootstrap helpers, `loadLanguage`, `submitPractice`, `newSessionId`, pronunciation, toast, escaping and DOM helpers.

`legacy_retirement.js` now requires `practice-games` and retires the superseded practice/game/XP globals only after the replacement module has loaded.

Historical declarations remain physically present in `static/app.js` for controlled rollback until the next physical-shell cleanup release.

## Regression evolution

The v6.0.4 practice test is upgraded from staged-renderer ownership to direct implementation ownership. The v6.0.13 and v6.0.14 cleanup contracts are also advanced so they no longer require practice renderers in the bridge.

A dedicated `v615` regression verifies:

- all three views are owned by the module;
- roleplay/practice API parity;
- game start/finish API parity;
- XP/reward API parity;
- pronunciation integration;
- feature gates;
- absence of feature renderer adapters from the bridge;
- runtime retirement of old practice globals;
- script ordering and JavaScript syntax.

## Pilot readiness impact

After v6.0.15 all end-user and admin feature screens have a modular owner. The remaining frontend work before a pilot is no longer another feature migration. It is primarily:

1. physical reduction of `static/app.js` into a small shell/shared-runtime layer;
2. deployment and pilot-readiness validation, including login/roles, LAN access, persistence, backups/recovery, observability, browser/audio fallbacks and a clean end-to-end smoke path.

The existing hosted GitHub Actions startup failure (`steps=[]`) remains an external verification blocker and should be resolved or bypassed with an equivalent controlled CI environment before production-like pilot approval.
