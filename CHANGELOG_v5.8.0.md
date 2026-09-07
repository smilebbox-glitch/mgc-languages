# MGC Languages v5.8.0 — Router Extraction

## Architecture

- Moved the historical monolithic implementation byte-for-byte from `app.py` to `mgc/legacy_app.py`.
- Replaced `app.py` with a thin compatibility facade that forwards historical module attributes.
- Added `mgc.routers.system` as the first real FastAPI `APIRouter` extraction.
- Active ownership of `GET /health`, `GET /health/live`, `GET /ready`, `GET /health/ready` and `GET /api/meta` now belongs to `mgc.routers.system`.
- Added `mgc_core.router_bridge` to replace the five legacy APIRoutes in-place, preserving their position before the root static mount.
- Runtime default legacy implementation is now `mgc.legacy_app`; `import app` remains supported.

## Compatibility

- No API path/method changes.
- No database or Alembic changes; expected head remains `c57d0a31f570`.
- No auth/session, XP/SRS, terminology, workflow or UI behavior changes.
- Chinese learning standard remains `Путунхуа (普通话) — стандартный китайский`.

## Verification

- Architecture guard understands active legacy-vs-router ownership and rejects duplicate/missing critical routes.
- Dedicated `v580` core/runtime shard validates facade size, router ownership, root-mount ordering and live health/readiness/meta responses.
- Docker CI asserts `ROUTER_BINDING_REPORT.ok` before runtime smoke.
