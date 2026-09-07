#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT/frontend"
REGISTRY="${NPM_CONFIG_REGISTRY:-${1:-}}"
[[ -n "$REGISTRY" ]] || { echo "Set NPM_CONFIG_REGISTRY or pass approved registry URL" >&2; exit 2; }
rm -rf npm-cache/_cacache node_modules
npm install --package-lock-only --ignore-scripts --no-audit --no-fund --registry "$REGISTRY"
npm ci --ignore-scripts --no-audit --no-fund --cache "$PWD/npm-cache" --registry "$REGISTRY"
npm cache verify --cache "$PWD/npm-cache"
# Prove the generated lock/cache work without registry access.
rm -rf node_modules
npm ci --offline --ignore-scripts --no-audit --no-fund --cache "$PWD/npm-cache"
npm run build
rm -rf node_modules dist
printf 'Prepared package-lock.json + offline npm cache from approved registry.\n'
