# Frontend Practice & Games Module — v6.0.4

## Purpose

Move active navigation ownership for practice/game views out of the historical frontend dispatch without rewriting `static/app.js` while hosted CI is unavailable.

## Owned views

- `roleplay`
- `games`
- `xp`

## Compatibility

The module delegates rendering to exact historical function references exposed by `legacy_bridge.js`, preserving current UI and business behavior while changing ownership.

`games` and `xp` retain their pilot feature gates (`games`, `xp_economy`) and the same disabled-feature error. Roleplay topic selection still resets scenario position/answer state when entered through a topic link.

The module runs before `navigation.js` and captures owned `data-view` / `data-go` clicks before historical bubble handlers, preventing duplicate rendering.

`renderRoleplay`, `renderGames`, and `renderXP` remain fallback definitions in `app.js` until the full CI suite can execute again. Physical deletion is deferred intentionally.

No backend route, XP/SRS algorithm, database schema, content or Putonghua standard is changed by this frontend extraction.
