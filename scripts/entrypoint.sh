#!/bin/sh
set -eu

validate_int() {
  name="$1"
  value="$2"
  min="$3"
  max="$4"
  case "$value" in
    ''|*[!0-9]*)
      echo "ERROR: $name must be an integer between $min and $max" >&2
      exit 2
      ;;
  esac
  if [ "$value" -lt "$min" ] || [ "$value" -gt "$max" ]; then
    echo "ERROR: $name must be between $min and $max" >&2
    exit 2
  fi
}

workers="${WEB_CONCURRENCY:-1}"
limit_concurrency="${UVICORN_LIMIT_CONCURRENCY:-200}"
backlog="${UVICORN_BACKLOG:-2048}"
keep_alive="${UVICORN_KEEP_ALIVE_SECONDS:-5}"

validate_int WEB_CONCURRENCY "$workers" 1 16
validate_int UVICORN_LIMIT_CONCURRENCY "$limit_concurrency" 20 5000
validate_int UVICORN_BACKLOG "$backlog" 128 16384
validate_int UVICORN_KEEP_ALIVE_SECONDS "$keep_alive" 1 60

# Fail closed before migrations/server start if worker-local SQLAlchemy pools could
# exhaust the configured PostgreSQL connection budget.
python scripts/capacity_preflight.py
python scripts/migrate_safe.py

# LAN/pilot deployments can explicitly keep the bootstrap admin credentials in
# sync with .env.lan. This runs once before Uvicorn forks workers, avoiding
# multi-worker credential-update races. Production requires a second explicit
# ALLOW_ADMIN_CREDENTIAL_RESET=true guard inside the sync utility.
python scripts/sync_admin_credentials.py

exec uvicorn asgi:app \
  --host 0.0.0.0 \
  --port 8000 \
  --workers "$workers" \
  --limit-concurrency "$limit_concurrency" \
  --backlog "$backlog" \
  --timeout-keep-alive "$keep_alive" \
  --proxy-headers \
  --forwarded-allow-ips="${FORWARDED_ALLOW_IPS:-*}"
