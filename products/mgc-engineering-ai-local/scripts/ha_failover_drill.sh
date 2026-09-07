#!/usr/bin/env bash
set -euo pipefail
[[ "${MGC_HA_DRILL_CONFIRM:-}" == "YES" ]] || { echo "Set MGC_HA_DRILL_CONFIRM=YES to run the disruptive HA failover drill." >&2; exit 2; }
command -v docker >/dev/null || { echo "docker CLI required" >&2; exit 2; }
docker compose version >/dev/null
C=(docker compose -f docker-compose.yml -f docker-compose.ha.yml)

snapshot() {
  "${C[@]}" exec -T api python -c 'import json; from app.core.high_availability import high_availability_snapshot; print(json.dumps(high_availability_snapshot()))'
}
health_via_gateway() {
  "${C[@]}" exec -T gateway wget -q -O - http://127.0.0.1:8080/api/v1/health/live | grep -q '"status":"alive"\|"status": "alive"'
}

python scripts/ha_failover_preflight.py
"${C[@]}" up -d api api-ha worker worker-ha worker-cpu worker-cpu-ha worker-io worker-io-ha beat beat-ha frontend frontend-ha gateway
for _ in $(seq 1 30); do health_via_gateway && break; sleep 2; done
health_via_gateway
snapshot | grep -q '"stable_api_replicas": 2\|"stable_api_replicas": 3' || { echo "HA API redundancy not observed" >&2; exit 1; }

# API instance loss: safe GET/liveness must continue through passive upstream failover.
"${C[@]}" stop api
sleep 3
health_via_gateway
"${C[@]}" start api
for _ in $(seq 1 30); do health_via_gateway && break; sleep 2; done

# Worker-role loss: secondary CPU worker must retain queue capacity.
"${C[@]}" stop worker-cpu
sleep 3
snapshot | grep -q '"cpu": 1\|"cpu": 2' || { echo "CPU worker failover capacity not observed" >&2; exit 1; }
"${C[@]}" start worker-cpu

# Scheduler coordination: killing one Beat must not produce two active leaders.
"${C[@]}" stop beat
sleep "${SCHEDULER_LEADER_RETRY_SECONDS:-12}"
SNAP=$(snapshot)
echo "$SNAP" | grep -q '"scheduler_active_leaders": 1' || { echo "Exactly one scheduler leader not observed after failover" >&2; exit 1; }
echo "$SNAP" | grep -q '"split_brain_risk": false' || { echo "Scheduler split-brain risk detected" >&2; exit 1; }
"${C[@]}" start beat

echo "PASS: live HA failover drill completed. This proves container/service failover on this target only; it does not certify physical host/database/storage HA."
