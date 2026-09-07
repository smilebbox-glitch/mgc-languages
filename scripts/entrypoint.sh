#!/bin/sh
set -eu
python scripts/migrate_safe.py
exec uvicorn app:app --host 0.0.0.0 --port 8000 --proxy-headers --forwarded-allow-ips="*"
