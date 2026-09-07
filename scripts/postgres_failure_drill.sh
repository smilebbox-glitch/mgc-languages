#!/bin/sh
set -eu
# Controlled pilot-only drill. It intentionally interrupts PostgreSQL for a short period.
[ "${CONFIRM_PILOT_DRILL:-}" = "YES" ] || {
  echo "Refusing to interrupt PostgreSQL. Re-run with CONFIRM_PILOT_DRILL=YES on an approved pilot/sandbox only." >&2
  exit 2
}
COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.pilot.yml}"
BASE_URL="${MGC_BASE_URL:-http://localhost:8080}"
cleanup() {
  docker compose -f "$COMPOSE_FILE" unpause db >/dev/null 2>&1 || true
}
trap cleanup EXIT INT TERM

echo "[1/4] Baseline readiness"
python scripts/reliability_drill.py --base-url "$BASE_URL" --expect ready

echo "[2/4] Pause PostgreSQL"
docker compose -f "$COMPOSE_FILE" pause db >/dev/null
sleep 7
python scripts/reliability_drill.py --base-url "$BASE_URL" --expect db-down

echo "[3/4] Resume PostgreSQL"
docker compose -f "$COMPOSE_FILE" unpause db >/dev/null
for i in $(seq 1 30); do
  if python scripts/reliability_drill.py --base-url "$BASE_URL" --expect ready >/dev/null 2>&1; then
    echo "[4/4] PASS: readiness recovered after PostgreSQL resumed"
    exit 0
  fi
  sleep 2
done
echo "FAIL: readiness did not recover within 60 seconds" >&2
exit 1
