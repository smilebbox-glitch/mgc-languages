#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"; cd "$ROOT"
STATE_DIR="${CUTOVER_STATE_DIR:-storage/.mgc-deployment}"
STATE_FILE="$STATE_DIR/bluegreen.env"
READY_TIMEOUT="${ROLLING_READY_TIMEOUT_SECONDS:-180}"
[[ -f "$STATE_FILE" ]] || { echo "No blue/green state file: $STATE_FILE" >&2; exit 2; }
# shellcheck disable=SC1090
source "$STATE_FILE"
: "${STABLE_VERSION:?}" "${STABLE_SCHEMA:?}" "${CANDIDATE_VERSION:?}" "${CANDIDATE_SCHEMA:?}"
python scripts/cutover_contract_check.py \
  --source-version "$CANDIDATE_VERSION" --source-schema "$CANDIDATE_SCHEMA" \
  --target-version "$STABLE_VERSION" --target-schema "$STABLE_SCHEMA" --max-patch "${CUTOVER_MAX_PATCH_ROLLBACK_SKEW:-1}" --rollback

API_UPSTREAM="api:8080" FRONTEND_UPSTREAM="frontend:8080" CUTOVER_GENERATION="rollback-${STABLE_VERSION}" \
  docker compose -f docker-compose.yml -f docker-compose.bluegreen.yml up -d --no-deps --force-recreate gateway

deadline=$((SECONDS + READY_TIMEOUT)); ok=0
while (( SECONDS < deadline )); do
  if docker compose exec -T gateway wget -q -O - http://127.0.0.1:8080/api/v1/health/ready 2>/dev/null | grep -q '"status"[[:space:]]*:[[:space:]]*"ready"'; then ok=1; break; fi
  sleep 3
done
(( ok == 1 )) || { echo "Rollback gateway switched but stable readiness did not recover" >&2; exit 1; }
{
  grep -v '^STATUS=' "$STATE_FILE" || true
  echo 'STATUS=rolled_back'
} > "$STATE_FILE.tmp" && mv "$STATE_FILE.tmp" "$STATE_FILE"
chmod 600 "$STATE_FILE"
echo "PASS: gateway rolled back to stable ${STABLE_VERSION}/${STABLE_SCHEMA}. Candidate remains isolated for diagnostics."
