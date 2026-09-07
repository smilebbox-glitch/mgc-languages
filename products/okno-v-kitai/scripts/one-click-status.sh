#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
command -v docker >/dev/null 2>&1 || { echo "Docker is not installed or not in PATH."; exit 1; }
docker compose ps
cid="$(docker compose ps -q china-auto-radar 2>/dev/null || true)"
if [[ -n "$cid" ]]; then
  health="$(docker inspect --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}' "$cid" 2>/dev/null || true)"
  echo "Web health: ${health:-unknown}"
fi
if [[ -f .env ]]; then
  port="$(grep -E '^APP_PORT=' .env | tail -n1 | cut -d= -f2-)"; port="${port:-3000}"
  echo "URL: http://127.0.0.1:${port}"
fi
