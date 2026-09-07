# Frontend Learning Module — v6.0.3

## Purpose

Move active navigation ownership for the four most-used learning views out of the historical frontend dispatch without rewriting the large `static/app.js` while GitHub-hosted CI is unavailable.

## Owned views

- `home`
- `topics`
- `quiz`
- `course30`

`static/frontend/learning.js` is loaded after `app-state` and before `navigation`.

## Dispatch model

`navigation.setView(view)` checks `frontend.learning.owns(view)`. Owned views are rendered through `frontend.learning.navigate(view)`; other views still delegate to the historical `setView` during staged migration.

The learning module also captures `data-view` and relevant `data-go` clicks before the historical bubble listeners, preventing double rendering. Topic selection and quiz reset semantics are preserved.

## Compatibility boundary

`legacy_bridge.js` exports exact references to the four historical renderer functions plus `closeMenu` and `ensureChineseStandardBanner`. This means rendering behavior remains unchanged while ownership moves to the module registry.

The historical renderer definitions are intentionally retained as fallback until the full frontend regression suite can execute again. Physical removal from `app.js` should happen only after GitHub Actions runners are restored.

## Invariants

- Putonghua banner remains applied after owned learning renderers.
- loading and error cards preserve existing UI behavior.
- no API/OpenAPI/ORM/Alembic changes.
- no learning content changes.
- `static/app.js` remains unchanged in v6.0.3.
