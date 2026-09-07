#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"; cd "$ROOT"
STATE_DIR="${CUTOVER_STATE_DIR:-storage/.mgc-deployment}"; STATE_FILE="$STATE_DIR/bluegreen.env"
[[ -f "$STATE_FILE" ]] || { echo "No active blue/green state" >&2; exit 2; }
# shellcheck disable=SC1090
source "$STATE_FILE"
[[ "${STATUS:-}" == "candidate_active" ]] || { echo "Finalize requires STATUS=candidate_active" >&2; exit 2; }
[[ "${CANDIDATE_VERSION:-}" == "6.3.34" && "${CANDIDATE_SCHEMA:-}" == "6.3.13" ]] || { echo "Unexpected candidate contract" >&2; exit 2; }
# Human-invoked finalization upgrades workers/beat/stable API using the existing drain/version fences.
MGC_TARGET_VERSION=6.3.34 scripts/rolling_upgrade.sh
# rolling_upgrade.sh returns gateway to the canonical stable service after the new stable API is ready.
docker compose -f docker-compose.yml -f docker-compose.bluegreen.yml stop api-candidate frontend-candidate >/dev/null || true
{
  grep -v '^STATUS=' "$STATE_FILE" || true
  echo 'STATUS=finalized'
} > "$STATE_FILE.tmp" && mv "$STATE_FILE.tmp" "$STATE_FILE"
chmod 600 "$STATE_FILE"
echo "PASS: v6.3.34 finalized as canonical stable deployment; candidate services stopped."
