# v6.0.5 — Frontend Support & Notifications

- Added `static/frontend/support_notifications.js` as the canonical active owner for the `notifications` view and user-facing support signals.
- Notification settings and pending nudges now use the modular CSRF-aware API client and shared app-state facade.
- Preserved `learning_nudges` pilot feature gating and the existing disabled-feature semantics.
- Preserved notification frequency, quiet-window, browser opt-in, mark-as-read and Browser Notifications behavior.
- Added modular support helpers for toast messages, service status and privacy-safe error-boundary reporting.
- Navigation now delegates `notifications` to `support-notifications`; capture-phase interception prevents duplicate legacy rendering.
- Historical `renderNotifications`, `saveNudgeSettings` and `maybeBrowserNudge` remain staged fallback definitions in `static/app.js`.
- Added v6.0.5 release shard, static preflight coverage and dedicated GitHub Actions contract checks.
- No backend API, ORM, Alembic, content, Putonghua standard or runtime APP_VERSION changes.
