#!/usr/bin/env bash
set -euo pipefail

failures=0
warns=0
pass() { printf 'PASS  %s\n' "$1"; }
warn() { printf 'WARN  %s\n' "$1"; warns=$((warns+1)); }
fail() { printf 'FAIL  %s\n' "$1"; failures=$((failures+1)); }

command -v docker >/dev/null 2>&1 && pass "docker CLI available" || fail "docker CLI is required"
if command -v docker >/dev/null 2>&1; then
  docker compose version >/dev/null 2>&1 && pass "docker compose v2 available" || fail "docker compose v2 is required"
  docker info >/dev/null 2>&1 && pass "docker daemon reachable" || fail "docker daemon is not reachable for current user"
fi

mem_kb=$(awk '/MemTotal:/ {print $2}' /proc/meminfo 2>/dev/null || echo 0)
if (( mem_kb >= 1800000 )); then pass "host memory >= ~2 GB"; else warn "host memory below recommended 2 GB"; fi

disk_kb=$(df -Pk . | awk 'NR==2 {print $4}')
if (( disk_kb >= 5000000 )); then pass "free disk >= ~5 GB"; else warn "free disk below recommended 5 GB"; fi

if [[ -f .env ]]; then
  pass ".env present"
  # shellcheck disable=SC1091
  set -a; source .env; set +a
  if [[ "${APP_BIND_ADDRESS:-127.0.0.1}" == "0.0.0.0" && "${ALLOW_PUBLIC_BIND:-NO}" != "YES" ]]; then
    fail "APP_BIND_ADDRESS=0.0.0.0 requires explicit ALLOW_PUBLIC_BIND=YES and network controls"
  else
    pass "application bind policy accepted"
  fi
  if [[ "${AUTH_MODE:-disabled}" == "proxy" ]]; then
    [[ -n "${AUTH_PROXY_SECRET:-}" ]] && pass "AUTH_PROXY_SECRET configured" || fail "AUTH_MODE=proxy requires AUTH_PROXY_SECRET"
    [[ -z "${ADMIN_API_TOKEN:-}" ]] && pass "legacy ADMIN_API_TOKEN disabled in proxy mode" || warn "ADMIN_API_TOKEN remains enabled in proxy mode; remove after SSO validation"
  else
    [[ -n "${ADMIN_API_TOKEN:-}" ]] && pass "pre-SSO ADMIN_API_TOKEN configured" || warn "ADMIN_API_TOKEN empty: /admin mutations will not be available in disabled auth mode"
  fi
  [[ -n "${AUDIT_HMAC_KEY:-}" ]] && pass "AUDIT_HMAC_KEY configured" || warn "AUDIT_HMAC_KEY empty: audit chain is SHA-256 only, not keyed HMAC"
  if [[ -z "${SCHEDULER_TOKEN:-}" || "${SCHEDULER_TOKEN:-}" == "change-me-before-pilot" ]]; then fail "SCHEDULER_TOKEN is default/empty; replace it before controlled pilot"; else pass "SCHEDULER_TOKEN configured"; fi
  if [[ -z "${USER_DATA_HMAC_KEY:-}" || "${USER_DATA_HMAC_KEY:-}" == "change-me-user-data-hmac-before-pilot" || ${#USER_DATA_HMAC_KEY} -lt 32 ]]; then fail "USER_DATA_HMAC_KEY is default/short; replace it before controlled pilot"; else pass "USER_DATA_HMAC_KEY configured"; fi
  for pair in "SOURCE_HISTORY_RETENTION_DAYS:${SOURCE_HISTORY_RETENTION_DAYS:-30}:1" "SOURCE_HISTORY_MAX_ROWS:${SOURCE_HISTORY_MAX_ROWS:-5000}:100" "SCHEDULER_LOCK_TTL_SECONDS:${SCHEDULER_LOCK_TTL_SECONDS:-120}:30" "SOURCE_SLA_FX_SECONDS:${SOURCE_SLA_FX_SECONDS:-1800}:60" "SOURCE_SLA_NEWS_SECONDS:${SOURCE_SLA_NEWS_SECONDS:-3600}:60" "USAGE_RETENTION_DAYS:${USAGE_RETENTION_DAYS:-90}:1"; do
    IFS=: read -r key value minimum <<<"$pair"
    if [[ "$value" =~ ^[0-9]+$ ]] && (( value >= minimum )); then pass "$key numeric policy accepted"; else fail "$key must be integer >= $minimum"; fi
  done
  if (( ${SCHEDULER_LOCK_TTL_SECONDS:-120} < ${SCHEDULER_INTERVAL_SECONDS:-300} )); then pass "scheduler lock TTL < scheduler interval"; else warn "SCHEDULER_LOCK_TTL_SECONDS should normally be below SCHEDULER_INTERVAL_SECONDS"; fi
else
  fail ".env missing (copy .env.example and configure pilot secrets)"
fi

if (( failures > 0 )); then
  printf '\n%d failure(s), %d warning(s). Host is NOT ready for pilot deployment.\n' "$failures" "$warns"
  exit 1
fi
printf '\nHost preflight passed with %d warning(s).\n' "$warns"
