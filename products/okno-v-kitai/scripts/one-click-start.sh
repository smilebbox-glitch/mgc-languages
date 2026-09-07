#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

say(){ printf '\n==> %s\n' "$1"; }
fail(){ printf '\nERROR: %s\n' "$1" >&2; exit 1; }

get_env(){
  local key="$1"
  local line
  line="$(grep -E "^${key}=" .env 2>/dev/null | tail -n1 || true)"
  printf '%s' "${line#*=}"
}
set_env(){
  local key="$1" value="$2"
  if grep -qE "^${key}=" .env 2>/dev/null; then
    awk -v k="$key" -v v="$value" 'BEGIN{FS="="} $1==k{print k"="v; next} {print}' .env > .env.tmp
    mv .env.tmp .env
  else
    printf '\n%s=%s\n' "$key" "$value" >> .env
  fi
}
secret(){
  od -An -N48 -tx1 /dev/urandom | tr -d ' \n'
}
ensure_secret(){
  local key="$1" placeholder="${2:-}"
  local val="$(get_env "$key")"
  if [[ -z "$val" || ( -n "$placeholder" && "$val" == "$placeholder" ) ]]; then
    set_env "$key" "$(secret)"
  fi
}

say "Checking Docker"
command -v docker >/dev/null 2>&1 || fail "Docker is not installed or is not in PATH. Install Docker Desktop / Docker Engine once, then run START again."
if ! docker compose version >/dev/null 2>&1; then
  fail "Docker Compose v2 is required."
fi
if ! docker info >/dev/null 2>&1; then
  if [[ "$(uname -s)" == "Darwin" ]] && command -v open >/dev/null 2>&1; then
    say "Starting Docker Desktop"
    open -a Docker >/dev/null 2>&1 || true
    for _ in $(seq 1 60); do
      docker info >/dev/null 2>&1 && break
      sleep 2
    done
  fi
fi
docker info >/dev/null 2>&1 || fail "Docker daemon is not running or current user cannot access it."

say "Preparing secure pilot configuration"
if [[ ! -f .env ]]; then
  cp .env.example .env
  printf 'Created .env from .env.example\n'
fi
ensure_secret SCHEDULER_TOKEN change-me-before-pilot
ensure_secret USER_DATA_HMAC_KEY change-me-user-data-hmac-before-pilot
ensure_secret AUDIT_HMAC_KEY
current_version="$(get_env APP_VERSION)"
if [[ -z "$current_version" || "$current_version" == "1.6.0-pilot" ]]; then
  set_env APP_VERSION "1.6.1-pilot"
fi

auth_mode="$(get_env AUTH_MODE)"
auth_mode="${auth_mode:-disabled}"
if [[ "$auth_mode" == "disabled" ]]; then
  ensure_secret ADMIN_API_TOKEN
elif [[ "$auth_mode" == "proxy" ]]; then
  [[ -n "$(get_env AUTH_PROXY_SECRET)" ]] || fail "AUTH_MODE=proxy is configured but AUTH_PROXY_SECRET is empty. Configure the reverse proxy secret, then rerun START."
else
  fail "Unsupported AUTH_MODE='$auth_mode'. Expected disabled or proxy."
fi

# Validate the same critical governance fields required by the controlled pilot.
for spec in \
  "SOURCE_HISTORY_RETENTION_DAYS:1" \
  "SOURCE_HISTORY_MAX_ROWS:100" \
  "SCHEDULER_LOCK_TTL_SECONDS:30" \
  "SOURCE_SLA_FX_SECONDS:60" \
  "SOURCE_SLA_NEWS_SECONDS:60" \
  "USAGE_RETENTION_DAYS:1"; do
  key="${spec%%:*}"; min="${spec##*:}"; val="$(get_env "$key")"
  [[ "$val" =~ ^[0-9]+$ ]] || fail "$key must be an integer."
  (( val >= min )) || fail "$key must be >= $min."
done

bind_address="$(get_env APP_BIND_ADDRESS)"; bind_address="${bind_address:-127.0.0.1}"
allow_public="$(get_env ALLOW_PUBLIC_BIND)"; allow_public="${allow_public:-NO}"
if [[ "$bind_address" == "0.0.0.0" && "$allow_public" != "YES" ]]; then
  fail "APP_BIND_ADDRESS=0.0.0.0 requires ALLOW_PUBLIC_BIND=YES and explicit network controls."
fi

say "Running host preflight"
bash scripts/host-preflight.sh

say "Validating Docker Compose"
docker compose config >/dev/null

if [[ -f okno-v-kitai-image.tar ]]; then
  say "Loading offline Docker image"
  docker load -i okno-v-kitai-image.tar
  app_version="$(get_env APP_VERSION)"; app_version="${app_version:-1.6.1-pilot}"
  expected_image="okno-v-kitai:${app_version}"
  docker image inspect "$expected_image" >/dev/null 2>&1 || fail "Offline image does not provide expected tag $expected_image."
  say "Starting services without rebuild"
  docker compose up -d --no-build
else
  say "Building application image"
  docker compose build
  say "Starting web + scheduler"
  docker compose up -d
fi

say "Waiting for application readiness"
cid="$(docker compose ps -q china-auto-radar)"
[[ -n "$cid" ]] || fail "Web container was not created. Run: docker compose logs china-auto-radar"
status=""
for _ in $(seq 1 90); do
  status="$(docker inspect --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}' "$cid" 2>/dev/null || true)"
  [[ "$status" == "healthy" ]] && break
  if [[ "$status" == "exited" || "$status" == "dead" ]]; then
    docker compose logs --tail=120 china-auto-radar || true
    fail "Web container stopped during startup."
  fi
  sleep 2
done
[[ "$status" == "healthy" ]] || { docker compose logs --tail=120 china-auto-radar || true; fail "Application did not become healthy."; }

say "Running smoke checks"
docker exec "$cid" node - <<'NODE'
const urls = [
  'http://127.0.0.1:3000/api/health',
  'http://127.0.0.1:3000/api/ready',
  'http://127.0.0.1:3000/api/content?section=travel-guide'
];
for (const url of urls) {
  const r = await fetch(url);
  if (!r.ok) throw new Error(`${url} -> ${r.status}`);
}
console.log('PASS  health/readiness/content');
NODE
if ! docker compose ps --status running --services | grep -qx 'china-auto-radar-scheduler'; then
  fail "Scheduler is not running."
fi
printf 'PASS  scheduler running\n'

port="$(get_env APP_PORT)"; port="${port:-3000}"
url="http://127.0.0.1:${port}"
admin_token="$(get_env ADMIN_API_TOKEN)"
{
  printf 'Okno v Kitai Pilot v1.6.1\n'
  printf 'URL: %s\n' "$url"
  if [[ "$auth_mode" == "disabled" ]]; then
    printf 'Admin API token: %s\n' "$admin_token"
  else
    printf 'Authentication: corporate proxy / SSO\n'
  fi
  printf 'Generated: %s\n' "$(date -u '+%Y-%m-%dT%H:%M:%SZ')"
} > .pilot-access.txt
chmod 600 .env .pilot-access.txt 2>/dev/null || true

say "READY"
printf 'Application: %s\n' "$url"
printf 'Access details: %s/.pilot-access.txt\n' "$ROOT"
printf 'Stop: ./stop.sh    Status: ./status.sh\n'

if [[ "${NO_BROWSER:-0}" != "1" ]]; then
  case "$(uname -s)" in
    Darwin) command -v open >/dev/null 2>&1 && open "$url" >/dev/null 2>&1 || true ;;
    Linux) command -v xdg-open >/dev/null 2>&1 && xdg-open "$url" >/dev/null 2>&1 || true ;;
  esac
fi
