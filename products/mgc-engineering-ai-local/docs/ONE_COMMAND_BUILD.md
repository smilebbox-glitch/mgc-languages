# One-command Docker build — v3.7

## The requested standard command

From the project root:

```bash
docker compose build
```

This now builds the local MGC application images with correct build contexts:

- `backend/` -> API + Celery worker;
- `frontend/` -> React/Vite UI;
- repository root -> hardened Nginx gateway.

Python packages from `backend/requirements.txt`, npm packages from `frontend/package.json`, and required Linux runtime libraries are installed inside the images. They must not be manually installed on the target host.

Docker Compose uses each service's `build.context`; Dockerfile `COPY` paths are resolved inside that context. v3.7 fixes the context/COPY mismatch that existed in the prior build overlay.

## Build and start in one command

After `.env`, corporate SSO and approved image/model pins have been configured once:

```bash
make start
```

Equivalent flow:

```bash
docker compose build
./scripts/stack.sh up -d --wait
```

`make start` remains fail-closed: it will not invent corporate OIDC credentials or silently replace approved air-gap image pins.

## Rebuild after source changes

```bash
docker compose build --no-cache
make up
```

## What the host needs

Only host/runtime prerequisites remain host-managed:

- Docker Engine;
- Docker Compose v2;
- approved CPU/GPU model files;
- imported/pinned infrastructure images for air-gapped production;
- corporate SSO configuration.

Python, npm, FastAPI, Celery, CadQuery, Docling, PyMuPDF and frontend dependencies belong inside Docker images, not on the host.
