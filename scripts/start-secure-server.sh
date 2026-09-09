#!/usr/bin/env sh
set -eu

ROOT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
cd "$ROOT_DIR"
umask 077

ENV_FILE="${1:-.env.pilot}"

if [ ! -f "$ENV_FILE" ]; then
  echo "Secure server configuration is missing: $ENV_FILE" >&2
  echo "Create it from .env.company-pilot.example and have IT fill the real DNS, OIDC and TLS values." >&2
  exit 1
fi

if ! command -v docker >/dev/null 2>&1; then
  echo "Docker is required for the secure server profile." >&2
  exit 1
fi

if ! docker compose version >/dev/null 2>&1; then
  echo "Docker Compose v2 is required for the secure server profile." >&2
  exit 1
fi

if ! command -v python3 >/dev/null 2>&1; then
  echo "Python 3 is required for the security preflight." >&2
  exit 1
fi

python3 scripts/server_security_preflight.py "$ENV_FILE"

echo "Validating the complete secure deployment profile..."
docker compose \
  --env-file "$ENV_FILE" \
  -f docker-compose.pilot.yml \
  -f docker-compose.server-edge.yml \
  config --quiet

echo "Building and starting the secure company server profile..."
docker compose \
  --env-file "$ENV_FILE" \
  -f docker-compose.pilot.yml \
  -f docker-compose.server-edge.yml \
  up -d --build

echo "Secure server profile started. External employee traffic is accepted only by the HTTPS gateway; the inner HTTP ingress remains localhost-only."
