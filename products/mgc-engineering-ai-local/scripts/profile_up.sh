#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
profile="${1:-core}"
case "$profile" in core|ai|advanced) ;; *) echo "usage: $0 {core|ai|advanced}" >&2; exit 2;; esac
export DEPLOYMENT_PROFILE="$profile"
exec "$ROOT/scripts/stack.sh" up -d
