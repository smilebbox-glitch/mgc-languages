from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

entrypoint = (ROOT / "scripts/entrypoint.sh").read_text(encoding="utf-8")
lan_compose = (ROOT / "docker-compose.lan.yml").read_text(encoding="utf-8")
lan_env = (ROOT / ".env.lan.example").read_text(encoding="utf-8")
launcher = (ROOT / "scripts/start_lan_windows.ps1").read_text(encoding="utf-8")
launcher_cmd = (ROOT / "start-lan.cmd").read_text(encoding="utf-8")
gitignore = (ROOT / ".gitignore").read_text(encoding="utf-8")

# Production/pilot runtime must use the modular ASGI boundary, not the legacy facade.
assert "uvicorn asgi:app" in entrypoint
assert "uvicorn app:app" not in entrypoint
assert "--host 0.0.0.0" in entrypoint
assert "--workers \"$workers\"" in entrypoint
assert "WEB_CONCURRENCY" in entrypoint
assert "between 1 and 16" in entrypoint

# LAN profile is shared-network capable and uses PostgreSQL for concurrent users.
assert "name: mgc-languages-lan" in lan_compose
assert "image: postgres:16.4-alpine" in lan_compose
assert "postgresql+psycopg://" in lan_compose
assert "AUTO_CREATE_SCHEMA: \"false\"" in lan_compose
assert "READY_REQUIRE_POSTGRES: \"true\"" in lan_compose
assert "TRUSTED_HOSTS: ${MGC_TRUSTED_HOSTS:-*}" in lan_compose
assert "WEB_CONCURRENCY: ${WEB_CONCURRENCY:-2}" in lan_compose
assert '"${MGC_BIND_ADDRESS:-0.0.0.0}:${MGC_PORT:-8080}:8080"' in lan_compose
assert "backend:\n    internal: true" in lan_compose
assert "./deploy/nginx/default.conf:/etc/nginx/conf.d/default.conf:ro" in lan_compose

# The database/app stay off the host network; nginx is the only published edge service.
db_block, rest = lan_compose.split("\n  app:\n", 1)
app_block, nginx_and_after = rest.split("\n  nginx:\n", 1)
nginx_block = nginx_and_after.split("\nnetworks:\n", 1)[0]
assert "ports:" not in db_block
assert "ports:" not in app_block
assert "ports:" in nginx_block

# Template defaults are suitable for a closed office LAN and explicitly document hardening.
assert "MGC_BIND_ADDRESS=0.0.0.0" in lan_env
assert "MGC_TRUSTED_HOSTS=*" in lan_env
assert "REGISTRATION_ENABLED=true" in lan_env
assert "WEB_CONCURRENCY=2" in lan_env
assert "Corporate rollout" in lan_env or "corporate rollout" in lan_env

# Windows one-click launcher auto-discovers LAN IP and writes explicit trusted hosts.
assert "Get-LanIPv4" in launcher
assert 'MGC_TRUSTED_HOSTS' in launcher
assert 'docker @composeArgs' in launcher
assert 'docker-compose.lan.yml' in launcher
assert 'http://${LanIp}:$Port' in launcher
assert 'MGC_ADMIN_PASSWORD' in launcher
assert 'powershell.exe' in launcher_cmd.lower()

# Runtime secrets stay local while the example remains tracked.
assert ".env.*" in gitignore
assert "!.env.lan.example" in gitignore

print("OK: v5.9.3 multi-user LAN deployment uses modular ASGI, PostgreSQL, nginx edge and LAN-aware one-click startup")
