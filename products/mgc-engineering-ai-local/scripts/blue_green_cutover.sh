#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"; cd "$ROOT"
TARGET_VERSION="${MGC_CANDIDATE_VERSION:-6.3.34}"
TARGET_SCHEMA="6.3.13"
READY_SAMPLES="${CUTOVER_CANDIDATE_MIN_READY_SAMPLES:-3}"
POST_SAMPLES="${CUTOVER_POST_SWITCH_SAMPLES:-5}"
FAIL_THRESHOLD="${CUTOVER_FAILURE_THRESHOLD:-2}"
SAMPLE_INTERVAL="${CUTOVER_SAMPLE_INTERVAL_SECONDS:-5}"
STATE_DIR="${CUTOVER_STATE_DIR:-storage/.mgc-deployment}"
STATE_FILE="$STATE_DIR/bluegreen.env"
COMPOSE=(docker compose -f docker-compose.yml -f docker-compose.bluegreen.yml)

[[ "$TARGET_VERSION" == "6.3.34" ]] || { echo "This source release certifies candidate 6.3.34 only" >&2; exit 2; }
python scripts/blue_green_cutover_preflight.py
[[ -n "${MGC_TARGET_HOST_ASSURANCE_REPORT:-}" ]] || { echo "Target-host assurance report is required" >&2; exit 2; }
HOST_GUARD=(python scripts/target_host_deployment_guard.py --report "$MGC_TARGET_HOST_ASSURANCE_REPORT")
if [[ -n "${MGC_TARGET_HOST_ASSURANCE_SIGNATURE:-}" ]]; then HOST_GUARD+=(--signature "$MGC_TARGET_HOST_ASSURANCE_SIGNATURE"); fi
if [[ -n "${MGC_TARGET_HOST_ASSURANCE_PUBLIC_KEY:-}" ]]; then HOST_GUARD+=(--public-key "$MGC_TARGET_HOST_ASSURANCE_PUBLIC_KEY"); fi
if [[ "${MGC_REQUIRE_SIGNED_HOST_ASSURANCE:-false}" == "true" ]]; then HOST_GUARD+=(--require-signature); fi
"${HOST_GUARD[@]}"
[[ -n "${MGC_RESILIENCE_CERTIFICATION_REPORT:-}" ]] || { echo "Resilience certification GO report is required" >&2; exit 2; }
[[ -n "${MGC_RESILIENCE_EVIDENCE:-}" ]] || { echo "Signed resilience evidence is required" >&2; exit 2; }
[[ -n "${MGC_RESILIENCE_EVIDENCE_SIGNATURE:-}" ]] || { echo "Resilience evidence detached signature is required" >&2; exit 2; }
[[ -n "${MGC_RESILIENCE_PUBLIC_KEY:-}" ]] || { echo "Resilience evidence public key is required" >&2; exit 2; }
[[ -n "${MGC_RESILIENCE_BASELINE:-}" ]] || { echo "Approved recovery baseline is required" >&2; exit 2; }
[[ -n "${MGC_RESILIENCE_CAMPAIGN:-}" ]] || { echo "Approved drill campaign is required" >&2; exit 2; }
python scripts/resilience_release_guard.py \
  --report "$MGC_RESILIENCE_CERTIFICATION_REPORT" \
  --evidence "$MGC_RESILIENCE_EVIDENCE" \
  --signature "$MGC_RESILIENCE_EVIDENCE_SIGNATURE" \
  --public-key "$MGC_RESILIENCE_PUBLIC_KEY" \
  --baseline "$MGC_RESILIENCE_BASELINE" \
  --campaign "$MGC_RESILIENCE_CAMPAIGN"

"${COMPOSE[@]}" config >/dev/null

docker compose ps --status running --services | grep -qx api || { echo "Stable api service is not running" >&2; exit 2; }
docker compose ps --status running --services | grep -qx gateway || { echo "Gateway service is not running" >&2; exit 2; }

read -r STABLE_VERSION STABLE_SCHEMA < <(docker compose exec -T api python -c 'from app.core.runtime_contract import APP_VERSION,SCHEMA_VERSION; print(APP_VERSION,SCHEMA_VERSION)')
python scripts/cutover_contract_check.py --source-version "$STABLE_VERSION" --source-schema "$STABLE_SCHEMA" --target-version "$TARGET_VERSION" --target-schema "$TARGET_SCHEMA" --max-patch "${CUTOVER_MAX_PATCH_ROLLBACK_SKEW:-1}"

MGC_CANDIDATE_VERSION="$TARGET_VERSION" "${COMPOSE[@]}" up -d api-candidate frontend-candidate
read -r CANDIDATE_VERSION CANDIDATE_SCHEMA < <("${COMPOSE[@]}" exec -T api-candidate python -c 'from app.core.runtime_contract import APP_VERSION,SCHEMA_VERSION; print(APP_VERSION,SCHEMA_VERSION)')
[[ "$CANDIDATE_VERSION" == "$TARGET_VERSION" && "$CANDIDATE_SCHEMA" == "$TARGET_SCHEMA" ]] || { echo "Candidate image contract mismatch" >&2; exit 2; }

# Candidate must be consecutively ready before any traffic switch. Health calls also publish its candidate-slot heartbeat.
consecutive=0
while (( consecutive < READY_SAMPLES )); do
  body="$(docker compose exec -T gateway wget -q -O - http://api-candidate:8080/api/v1/health/ready 2>/dev/null || true)"
  if grep -q '"status"[[:space:]]*:[[:space:]]*"ready"' <<<"$body" && grep -q '"version"[[:space:]]*:[[:space:]]*"6.3.34"' <<<"$body"; then
    consecutive=$((consecutive + 1))
  else
    consecutive=0
  fi
  (( consecutive >= READY_SAMPLES )) || sleep "$SAMPLE_INTERVAL"
done

mkdir -p "$STATE_DIR"
cat > "$STATE_FILE" <<EOF
STABLE_VERSION=$STABLE_VERSION
STABLE_SCHEMA=$STABLE_SCHEMA
CANDIDATE_VERSION=$CANDIDATE_VERSION
CANDIDATE_SCHEMA=$CANDIDATE_SCHEMA
STATUS=switching
EOF
chmod 600 "$STATE_FILE"

API_UPSTREAM="api-candidate:8080" FRONTEND_UPSTREAM="frontend-candidate:8080" CUTOVER_GENERATION="candidate-${TARGET_VERSION}" \
  "${COMPOSE[@]}" up -d --no-deps --force-recreate gateway

failures=0
for ((i=1; i<=POST_SAMPLES; i++)); do
  body="$(docker compose exec -T gateway wget -q -O - http://127.0.0.1:8080/api/v1/health/ready 2>/dev/null || true)"
  sample_ok=1
  grep -q '"status"[[:space:]]*:[[:space:]]*"ready"' <<<"$body" || sample_ok=0
  grep -q '"version"[[:space:]]*:[[:space:]]*"6.3.34"' <<<"$body" || sample_ok=0
  if [[ -n "${CUTOVER_SLO_PROBE_CMD:-}" ]]; then bash -lc "$CUTOVER_SLO_PROBE_CMD" || sample_ok=0; fi
  if (( sample_ok == 0 )); then failures=$((failures + 1)); else failures=0; fi
  if (( failures >= FAIL_THRESHOLD )); then
    echo "Post-cutover acceptance failed ${failures} consecutive samples; initiating guarded automatic rollback" >&2
    scripts/blue_green_rollback.sh
    exit 1
  fi
  (( i == POST_SAMPLES )) || sleep "$SAMPLE_INTERVAL"
done

{
  grep -v '^STATUS=' "$STATE_FILE" || true
  echo 'STATUS=candidate_active'
} > "$STATE_FILE.tmp" && mv "$STATE_FILE.tmp" "$STATE_FILE"
chmod 600 "$STATE_FILE"
echo "PASS: candidate ${TARGET_VERSION}/${TARGET_SCHEMA} is serving traffic. Stable remains online for guarded rollback. Production authorization remains human-controlled."
