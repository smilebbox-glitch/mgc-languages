#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
if [[ "${MGC_REQUIRE_REPRODUCIBLE_BUILD:-false}" == "true" ]]; then
  echo "ERROR: strict reproducible mode requested; use make reproducible-build / scripts/reproducible_build.sh." >&2
  exit 2
fi
command -v docker >/dev/null 2>&1 || { echo 'ERROR: docker is not installed or not in PATH.' >&2; exit 1; }
docker compose version >/dev/null 2>&1 || { echo "ERROR: Docker Compose v2 ('docker compose') is required." >&2; exit 1; }
python scripts/build_preflight.py
MGC_VERSION="${MGC_VERSION:-$(PYTHONPATH=backend python -c 'from app.core.runtime_contract import APP_VERSION; print(APP_VERSION)')}"
export MGC_VERSION
: "${MGC_API_IMAGE:=mgc-engineering-ai-api:${MGC_VERSION}-local}"
: "${MGC_FRONTEND_IMAGE:=mgc-engineering-ai-frontend:${MGC_VERSION}-local}"
: "${MGC_GATEWAY_IMAGE:=mgc-engineering-ai-gateway:${MGC_VERSION}-local}"
: "${MGC_WEBHOOK_IMAGE:=mgc-engineering-ai-webhook-edge:${MGC_VERSION}-local}"
export MGC_API_IMAGE MGC_FRONTEND_IMAGE MGC_GATEWAY_IMAGE MGC_WEBHOOK_IMAGE

echo 'Building local application images; Python/npm/system packages are installed by Dockerfiles.'
docker compose -f docker-compose.airgap.yml -f docker-compose.build.yml build "$@" api frontend gateway webhook-edge

echo
echo 'Build complete.'
echo 'You can also build the default application images directly with:'
echo '  docker compose build'
echo 'One-command build + start:'
echo '  make start'
