#!/usr/bin/env bash
set -euo pipefail
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/common.sh"

check_compose_version
require_cmd curl
require_cmd openssl
require_env_file

compose config --quiet

for service in db app nginx; do
  cid="$(compose ps -q "$service")"
  [[ -n "$cid" ]] || { echo "ERROR: $service container is not running." >&2; exit 1; }
  status="$(docker inspect -f '{{.State.Status}}' "$cid")"
  [[ "$status" == "running" ]] || { echo "ERROR: $service status is $status." >&2; exit 1; }
done

compose exec -T db sh -c 'pg_isready -U "$POSTGRES_USER" -d "$POSTGRES_DB"' >/dev/null
compose exec -T app python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health/ready', timeout=5)" >/dev/null

url="$(public_url)"
curl -kfsS --connect-timeout 3 --max-time 10 "$url/health/live" >/tmp/mgc-vm-live.json
curl -kfsS --connect-timeout 3 --max-time 10 "$url/health/ready" >/tmp/mgc-vm-ready.json
curl -kfsS --connect-timeout 3 --max-time 10 "$url/api/meta" >/tmp/mgc-vm-meta.json
curl -kfsS --connect-timeout 3 --max-time 10 "$url/" >/tmp/mgc-vm-index.html
grep -q '/frontend/boot.js' /tmp/mgc-vm-index.html

openssl x509 -in "$CERT_DIR/server.crt" -noout -checkend 86400 >/dev/null

if [[ -n "$(compose port db 5432 2>/dev/null || true)" ]]; then
  echo "ERROR: database port 5432 must not be published." >&2
  exit 1
fi
if [[ -n "$(compose port app 8000 2>/dev/null || true)" ]]; then
  echo "ERROR: application port 8000 must not be published directly." >&2
  exit 1
fi

printf 'OK: HTTPS %s\n' "$url"
printf 'OK: PostgreSQL internal readiness\n'
printf 'OK: application readiness\n'
printf 'OK: PWA/web shell reachable\n'
printf 'OK: TLS certificate valid for >24h\n'
printf 'OK: DB and app have no host-published ports\n'
compose ps
