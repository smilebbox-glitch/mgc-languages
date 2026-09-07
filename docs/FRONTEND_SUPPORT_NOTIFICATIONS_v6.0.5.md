# Frontend Support & Notifications — v6.0.5

## Purpose

Move the active `notifications` UI and its user-facing support/error signals into the modular frontend without changing backend notification contracts or rewriting the historical application bundle.

## Owned view

- `notifications`

## Active behavior

`support_notifications.js` loads notification settings and pending nudges through the modular API client, stores them through the shared app-state facade, renders the existing Learning Nudge Engine controls, persists frequency/quiet-window/browser settings, marks nudges as read, and owns Browser Notifications permission handling.

The module also exposes a small support facade for toast messages, service-status show/clear and privacy-safe error-boundary reporting so notification failures do not bypass the modular support path.

## Compatibility

The `learning_nudges` pilot feature gate and its existing disabled-feature message are preserved. The module is loaded before `navigation.js` and captures `data-view="notifications"` before historical bubble handlers, preventing duplicate rendering.

Historical `renderNotifications`, `saveNudgeSettings` and `maybeBrowserNudge` remain in `static/app.js` as staged fallback definitions. Backend routes, database schema, language content, Putonghua scope, XP/SRS and game behavior are unchanged.

## Verification

`tests/v605_frontend_support_notifications_test.py` verifies module ownership, script order, API endpoints, feature gating, Browser Notifications behavior, support/error integration and legacy fallback presence. The `v605` release shard and `ci-v605.yml` make those checks part of the release regression path.
