#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
./scripts/docker_build.sh "$@"
./scripts/stack.sh up -d --force-recreate
