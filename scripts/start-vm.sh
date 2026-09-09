#!/usr/bin/env sh
set -eu

ROOT="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
cd "$ROOT"
ENV_FILE=.env.vm
ENV_EXAMPLE=.env.vm.example
COMPOSE="docker compose --env-file $ENV_FILE -f docker-compose.lan.yml -f docker-compose.vm.yml"

need() {
  command -v "$1" >/dev/null 2>&1 || { echo "[NO-GO] Required command not found: $1" >&2; exit 1; }
}

random_hex() {
  od -An -N32 -tx1 /dev/urandom | tr -d ' \n'
}

set_env() {
  key="$1"
  value="$2"
  tmp="${ENV_FILE}.tmp.$$"
  awk -v k="$key" -v v="$value" 'BEGIN{done=0} index($0,k"=")==1 {print k"="v; done=1; next} {print} END{if(!done) print k"="v}' "$ENV_FILE" > "$tmp"
  mv "$tmp" "$ENV_FILE"
}

need docker

docker info >/dev/null 2>&1 || { echo "[NO-GO] Docker daemon is not running." >&2; exit 1; }
docker compose version >/dev/null 2>&1 || { echo "[NO-GO] Docker Compose v2 is required." >&2; exit 1; }

if [ ! -f "$ENV_FILE" ]; then
  cp "$ENV_EXAMPLE" "$ENV_FILE"
  set_env POSTGRES_PASSWORD "$(random_hex)"
  set_env OIDC_STATE_SECRET "$(random_hex)"
  set_env MGC_ADMIN_PASSWORD "$(random_hex)"
  set_env METRICS_TOKEN "$(random_hex)"
  chmod 600 "$ENV_FILE" 2>/dev/null || true
  echo "Created $ENV_FILE with generated local credentials."
fi

# APP_ENV=pilot rejects wildcard trusted hosts. Repair old .env.vm files too and
# allow only loopback plus the VM's detected primary IPv4 address.
IP="$(hostname -I 2>/dev/null | awk '{print $1}' || true)"
TRUSTED_HOSTS="localhost,127.0.0.1"
[ -n "$IP" ] && TRUSTED_HOSTS="$TRUSTED_HOSTS,$IP"
set_env MGC_TRUSTED_HOSTS "$TRUSTED_HOSTS"

echo "Validating CPU-only / no-AI VM configuration..."
$COMPOSE config >/dev/null

echo "Building MGC Languages..."
$COMPOSE build app

echo "Starting PostgreSQL + app + nginx..."
$COMPOSE up -d db app nginx

CID="$($COMPOSE ps -q app)"
[ -n "$CID" ] || { echo "[NO-GO] App container was not created." >&2; exit 1; }

i=0
while [ "$i" -lt 120 ]; do
  STATUS="$(docker inspect --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}' "$CID" 2>/dev/null || true)"
  [ "$STATUS" = healthy ] && break
  case "$STATUS" in exited|dead) $COMPOSE logs --tail=160 app db; exit 1;; esac
  i=$((i+1))
  sleep 2
done

[ "${STATUS:-}" = healthy ] || { $COMPOSE logs --tail=160 app db; echo "[NO-GO] Application did not become healthy." >&2; exit 1; }

PORT="$(awk -F= '$1=="MGC_PORT"{v=$2} END{print v}' "$ENV_FILE")"
[ -n "$PORT" ] || PORT=8080
ADMIN_USER="$(awk -F= '$1=="MGC_ADMIN_USERNAME"{v=$2} END{print v}' "$ENV_FILE")"

echo ""
echo "[GO] MGC Languages VM is ready (CPU-only, server-side AI/TTS disabled)."
echo "Local: http://127.0.0.1:$PORT"
[ -n "$IP" ] && echo "LAN:   http://$IP:$PORT"
echo "Trusted hosts: $TRUSTED_HOSTS"
echo "Admin user: ${ADMIN_USER:-admin}"
echo "Admin password is stored only in $ENV_FILE on this VM."
echo "Stop: docker compose --env-file $ENV_FILE -f docker-compose.lan.yml -f docker-compose.vm.yml down"
