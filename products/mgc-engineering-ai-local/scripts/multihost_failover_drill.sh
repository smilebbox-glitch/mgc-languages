#!/usr/bin/env bash
set -euo pipefail
[[ "${MGC_MULTHOST_DRILL_CONFIRM:-}" == "YES" ]] || { echo "Set MGC_MULTHOST_DRILL_CONFIRM=YES to run the disruptive host-loss drill." >&2; exit 2; }
: "${MGC_EXTERNAL_LB_PROBE_URL:?set URL ending in /api/v1/health/lb}"
: "${MGC_HOST_FAILURE_INJECT_CMD:?set controlled host failure injection command}"
: "${MGC_HOST_RECOVER_CMD:?set host recovery command}"
command -v curl >/dev/null || { echo "curl required" >&2; exit 2; }
python scripts/multihost_topology_preflight.py
probe() {
  local body
  body="$(curl --fail --silent --show-error --max-time 10 "$MGC_EXTERNAL_LB_PROBE_URL")" || return 1
  grep -q '"contract"[[:space:]]*:[[:space:]]*"mgc-external-lb-v1"' <<<"$body" && \
  grep -q '"traffic_eligible"[[:space:]]*:[[:space:]]*true' <<<"$body"
}
probe || { echo "External LB baseline is not eligible" >&2; exit 1; }
bash -lc "$MGC_HOST_FAILURE_INJECT_CMD"
recovered=0
for _ in $(seq 1 "${MGC_HOST_FAILOVER_PROBE_ATTEMPTS:-20}"); do
  if probe; then recovered=1; break; fi
  sleep "${MGC_HOST_FAILOVER_PROBE_INTERVAL_SECONDS:-3}"
done
bash -lc "$MGC_HOST_RECOVER_CMD"
(( recovered == 1 )) || { echo "External LB did not restore eligible service after injected host loss" >&2; exit 1; }
echo "PASS: external-LB host-loss failover observed. This does not certify DB/evidence replication or capacity; run authoritative HA and load gates separately."
