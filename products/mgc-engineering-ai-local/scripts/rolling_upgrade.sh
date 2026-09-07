#!/usr/bin/env bash
set -euo pipefail

# v6.3.34 controlled Compose rolling upgrade.
# Safe order for 6.3.33 -> 6.3.34: new workers first (they accept the adjacent-patch envelope),
# then singleton Beat, then API. This prevents a new producer from sending work to old workers.
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

TARGET_VERSION="${MGC_TARGET_VERSION:-6.3.34}"
DRAIN_TIMEOUT="${WORKER_DRAIN_TIMEOUT_SECONDS:-600}"
READY_TIMEOUT="${ROLLING_READY_TIMEOUT_SECONDS:-180}"

if [[ "$TARGET_VERSION" != "6.3.34" ]]; then
  echo "Refusing rollout: this release script is certified only for target 6.3.34" >&2
  exit 2
fi

python scripts/rolling_upgrade_preflight.py
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

docker compose config >/dev/null

# Refuse to jump over the certified adjacent-patch window.
if docker compose ps --status running --services 2>/dev/null | grep -qx api; then
  read -r SOURCE_VERSION SOURCE_SCHEMA < <(docker compose exec -T api python -c 'from app.core.runtime_contract import APP_VERSION,SCHEMA_VERSION; print(APP_VERSION,SCHEMA_VERSION)')
  python scripts/cutover_contract_check.py --source-version "$SOURCE_VERSION" --source-schema "$SOURCE_SCHEMA" --target-version "$TARGET_VERSION" --target-schema "6.3.13" --max-patch 1
fi

running_services() { docker compose ps --status running --services 2>/dev/null || true; }
is_running() { running_services | grep -qx "$1"; }

wait_healthy() {
  local service="$1" deadline=$((SECONDS + READY_TIMEOUT))
  while (( SECONDS < deadline )); do
    local cid status
    cid="$(docker compose ps -q "$service" 2>/dev/null || true)"
    if [[ -n "$cid" ]]; then
      status="$(docker inspect --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}' "$cid" 2>/dev/null || true)"
      if [[ "$status" == "healthy" || "$status" == "running" ]]; then return 0; fi
    fi
    sleep 3
  done
  echo "Service $service failed readiness window" >&2
  return 1
}

drain_and_recreate() {
  local service="$1" prefix="$2"
  if ! is_running "$service"; then
    echo "SKIP $service (not running/profile-disabled)"
    return 0
  fi
  echo "Draining $service ($prefix)..."
  docker compose exec -T "$service" python -m app.workers.drain_cli --prefix "$prefix" --timeout "$DRAIN_TIMEOUT"
  echo "Recreating $service with target image..."
  MGC_VERSION="$TARGET_VERSION" docker compose up -d --no-deps --force-recreate "$service"
  wait_healthy "$service"
}

recreate_service() {
  local service="$1"
  if ! is_running "$service"; then
    echo "SKIP $service (not running/profile-disabled)"
    return 0
  fi
  MGC_VERSION="$TARGET_VERSION" docker compose up -d --no-deps --force-recreate "$service"
  wait_healthy "$service"
}

# New workers accept v6.3.33 task envelopes while the old API remains the producer.
drain_and_recreate worker interactive@
drain_and_recreate worker-cpu cpu@
drain_and_recreate worker-io io@
drain_and_recreate worker-cad cad@
drain_and_recreate worker-ai ai@

# Exactly one Beat leader may publish scheduled work; advisory lock prevents duplicate leaders.
recreate_service beat

# Only after the worker fleet is compatible do we switch the producer/API.
recreate_service api

# Verify authoritative readiness through the internal API before replacing presentation layers.
if is_running gateway; then
  deadline=$((SECONDS + READY_TIMEOUT))
  while (( SECONDS < deadline )); do
    if docker compose exec -T gateway wget -q -O - http://api:8080/api/v1/health/ready >/tmp/mgc-ready.json 2>/dev/null; then
      grep -q '"status":"ready"\|"status": "ready"' /tmp/mgc-ready.json && break
    fi
    sleep 3
  done
  grep -q '"status":"ready"\|"status": "ready"' /tmp/mgc-ready.json || { echo "API readiness failed after upgrade" >&2; exit 1; }
fi

recreate_service frontend
recreate_service gateway

echo "Rolling upgrade to $TARGET_VERSION completed. Production authorization remains a separate human gate."
