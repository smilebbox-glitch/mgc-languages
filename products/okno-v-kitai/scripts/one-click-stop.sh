#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
command -v docker >/dev/null 2>&1 || { echo "Docker is not installed or not in PATH."; exit 1; }
docker compose down
echo "Okno v Kitai stopped. Persistent data volume was preserved."
