# MGC Languages v5.9.3 — Multi-user LAN runbook

## Goal

Run one MGC Languages instance on a Windows/office server so other computers on the same trusted LAN can open it in a browser.

The LAN profile is intentionally different from local development:

- PostgreSQL instead of SQLite;
- nginx is the only service exposed to the host network;
- the application and database stay on an internal Docker network;
- Uvicorn listens on `0.0.0.0` behind nginx;
- the modular production entrypoint is `asgi:app`;
- multiple Uvicorn workers are supported with `WEB_CONCURRENCY`;
- users have separate DB-backed accounts/sessions/progress.

## Windows one-click start

Prerequisite: Docker Desktop is installed and running.

1. Double-click `start-lan.cmd`.
2. On the first launch the script creates `.env.lan` with random database/admin/metrics secrets.
3. The script detects the server LAN IPv4 address and adds it plus the Windows computer name to `MGC_TRUSTED_HOSTS`.
4. Docker builds and starts PostgreSQL, the MGC app and nginx.
5. The console prints a URL such as:

   `http://192.168.10.25:8080`

6. Give that URL to colleagues connected to the same routed LAN/VLAN.
7. In the LAN sandbox profile users may register separate accounts themselves.

`stop-lan.cmd` stops the stack but preserves the PostgreSQL Docker volume.

## Windows Firewall

If the URL works on the server but not on another computer, the most common remaining cause is the host firewall or corporate network ACL.

Allow inbound TCP port `8080` for the **Domain/Private** network profile. IT can use an elevated PowerShell session:

```powershell
New-NetFirewallRule `
  -DisplayName "MGC Languages LAN 8080" `
  -Direction Inbound `
  -Action Allow `
  -Protocol TCP `
  -LocalPort 8080 `
  -Profile Domain,Private
```

Do not open the port to an untrusted/Public network unless MGC IT has approved the network design.

## Manual start

Copy `.env.lan.example` to `.env.lan`, replace all `CHANGE_ME` values, set `MGC_TRUSTED_HOSTS` to the real server IP/DNS names, then run:

```bash
docker compose --env-file .env.lan -f docker-compose.lan.yml up -d --build
```

Check:

```bash
docker compose --env-file .env.lan -f docker-compose.lan.yml ps
```

Readiness:

```text
http://SERVER_IP:8080/health/ready
```

## Concurrent smoke

After the server is running:

```bash
python scripts/multi_user_smoke.py \
  --base-url http://127.0.0.1:8080 \
  --clients 20 \
  --requests 200
```

The tool reports success/failure, requests per second and latency p50/p95/max.

This is an acceptance smoke, **not a capacity guarantee**. The maximum supported user count depends on CPU, RAM, storage latency, PostgreSQL sizing, TTS usage and the actual learning traffic mix.

## Initial sizing knobs

LAN defaults:

- `WEB_CONCURRENCY=2`;
- `DB_POOL_SIZE=5`;
- `DB_MAX_OVERFLOW=5`;
- `TTS_CONCURRENCY=2`.

Do not increase workers blindly. Each Uvicorn worker has its own SQLAlchemy connection pool and in-process telemetry/TTS runtime state. Measure load first, then size workers and PostgreSQL connections together.

## Corporate rollout

The LAN profile is intended for a controlled internal sandbox/pilot. For a broader corporate rollout MGC IT should use the hardened pilot/production controls:

- DNS name instead of sharing a raw IP;
- TLS/HTTPS at nginx/ingress;
- `COOKIE_SECURE=true`;
- corporate OIDC/SSO;
- `REGISTRATION_ENABLED=false`;
- explicit `TRUSTED_HOSTS`, not `*`;
- firewall/ACL restricted to approved corporate networks;
- PostgreSQL backups and restore rehearsal;
- central monitoring/audit/SIEM;
- load test on the target server before announcing a user-capacity number.

## Why the previous local profile was insufficient

The normal `docker-compose.yml` is a developer profile and uses SQLite plus localhost-only trusted hosts. It can be published by Docker, but that does not make it an appropriate concurrent office deployment. The v5.9.3 LAN profile removes those two blockers while keeping the database and application services off the host network.
