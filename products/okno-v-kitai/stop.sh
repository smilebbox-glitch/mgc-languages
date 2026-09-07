#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"
exec ./scripts/one-click-stop.sh "$@"
