# MGC Languages v5.7.3 — Modular Core, phase 1

This increment introduces a stable runtime boundary before the legacy backend is split into routers and services.

## Modular deployment entrypoint
- Added top-level `asgi.py` as the deployment-facing ASGI entrypoint.
- Docker now starts `uvicorn asgi:app` instead of targeting the monolithic `app.py` directly.
- `mgc_core.runtime` loads the current FastAPI application behind that boundary.
- The FastAPI application object itself remains unchanged, so existing middleware, routes, dependencies and static serving retain their current behavior.

## Runtime route contract
- Added `mgc_core.contracts` with a deterministic route inventory.
- Startup validates critical health, readiness, metrics, auth and metadata routes.
- Missing or duplicate HTTP routes fail closed with `RuntimeContractError` before the server is accepted as a valid deployment target.

## Release engineering
- Added a dedicated `v573` regression shard.
- Added positive and negative tests for the runtime contract.
- Static preflight now compiles `asgi.py` and the complete `mgc_core` package.
- Docker image validation imports the new entrypoint and verifies the contract before accepting the image.
- Existing v5.7.2 concurrency controls, extended content contracts, Docker runtime smoke and diagnostic artifact capture are preserved.

## Compatibility
- No database migration.
- No API path, response or UI change is intended.
- `app.py` remains the legacy implementation module for now; later v5.7.x increments can extract configuration, database, auth, learning and admin domains behind the new boundary one at a time.
