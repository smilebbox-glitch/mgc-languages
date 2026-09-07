#!/usr/bin/env bash
set -euo pipefail
port="${APP_PORT:-3000}"
base="http://127.0.0.1:${port}"

curl -fsS "${base}/api/health" >/dev/null
echo "PASS  /api/health"
curl -fsS "${base}/api/ready" >/dev/null
echo "PASS  /api/ready"
curl -fsS "${base}/api/fx?city=kaluga" >/dev/null
echo "PASS  /api/fx"
curl -fsS "${base}/api/content?section=travel-guide" >/dev/null
echo "PASS  /api/content + SQLite"

if docker compose ps --status running --services 2>/dev/null | grep -qx "china-auto-radar-scheduler"; then
  echo "PASS  scheduler service running"
else
  echo "FAIL  scheduler service is not running"; exit 1
fi

request_id=$(curl -fsSI "${base}/api/health" | awk -F': ' 'tolower($1)=="x-request-id" {gsub("\r", "", $2); print $2; exit}')
[[ -n "$request_id" ]] && echo "PASS  X-Request-ID response header" || { echo "FAIL  X-Request-ID response header missing"; exit 1; }

echo "Smoke checks passed."
