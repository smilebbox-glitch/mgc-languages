#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
command -v docker >/dev/null 2>&1 || { echo 'ERROR: Docker is not installed.' >&2; exit 1; }
docker compose version >/dev/null 2>&1 || { echo "ERROR: Docker Compose v2 ('docker compose') is required." >&2; exit 1; }

if [[ ! -f .env ]]; then
  cp .env.airgap.example .env
  echo 'Created .env from .env.airgap.example.'
  echo 'Fill corporate SSO secrets/image pins once, then run: make start' >&2
  exit 2
fi
if grep -Eq 'REPLACE_WITH_|=replace-me$|=replace-with-' .env; then
  echo 'ERROR: .env still contains deployment placeholders. Configure SSO/secrets/image pins first.' >&2
  exit 2
fi

python scripts/build_preflight.py

echo '[1/3] Building application images; Python/npm/system dependencies are installed automatically...'
docker compose build "$@"
echo '[2/3] Starting selected CPU/GPU runtime...'
./scripts/stack.sh up -d --wait
echo '[3/3] Service status:'
./scripts/stack.sh ps
