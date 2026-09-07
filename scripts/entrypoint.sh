#!/bin/sh
set -eu

python scripts/migrate_safe.py

workers="${WEB_CONCURRENCY:-1}"
case "$workers" in
  ''|*[!0-9]*)
    echo "ERROR: WEB_CONCURRENCY must be an integer between 1 and 16" >&2
    exit 2
    ;;
esac
if [ "$workers" -lt 1 ] || [ "$workers" -gt 16 ]; then
  echo "ERROR: WEB_CONCURRENCY must be between 1 and 16" >&2
  exit 2
fi

exec uvicorn asgi:app \
  --host 0.0.0.0 \
  --port 8000 \
  --workers "$workers" \
  --proxy-headers \
  --forwarded-allow-ips="${FORWARDED_ALLOW_IPS:-*}"
