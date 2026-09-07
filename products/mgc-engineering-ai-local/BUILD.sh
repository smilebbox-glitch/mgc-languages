#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
python scripts/build_preflight.py
docker compose build "$@"
