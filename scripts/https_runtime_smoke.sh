#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

HOST="mgc-language-runtime-ci.example.internal"
HTTP_PORT="18080"
HTTPS_PORT="18443"
TLS_DIR="$ROOT/.ci-runtime-tls"
ENV_FILE="$ROOT/.ci-runtime.env"
HEADERS_FILE="$ROOT/.ci-runtime-headers.txt"
BODY_FILE="$ROOT/.ci-runtime-ready.json"

compose() {
  docker compose --env-file "$ENV_FILE" \
    -f docker-compose.pilot.yml \
    -f docker-compose.server-edge.yml "$@"
}

cleanup() {
  set +e
  if [[ -f "$ENV_FILE" ]]; then
    compose down -v --remove-orphans >/dev/null 2>&1 || true
  fi
  rm -rf "$TLS_DIR" "$ENV_FILE" "$HEADERS_FILE" "$BODY_FILE"
}
trap cleanup EXIT

rm -rf "$TLS_DIR"
mkdir -p "$TLS_DIR"
openssl req -x509 -nodes -newkey rsa:2048 \
  -keyout "$TLS_DIR/tls.key" \
  -out "$TLS_DIR/tls.crt" \
  -days 30 \
  -subj "/CN=$HOST" \
  -addext "subjectAltName=DNS:$HOST" >/dev/null 2>&1
chmod 600 "$TLS_DIR/tls.key"

cat > "$ENV_FILE" <<EOF
APP_ENV=pilot
AUTH_MODE=oidc
REGISTRATION_ENABLED=false
COOKIE_SECURE=true
COOKIE_SAMESITE=lax
READY_REQUIRE_OIDC=true
READY_REQUIRE_SECURE_COOKIE=true
RECOVERY_EVIDENCE_REQUIRED=false
MGC_SERVER_NAME=$HOST
MGC_BIND_ADDRESS=127.0.0.1
MGC_HTTP_PORT=$HTTP_PORT
MGC_HTTPS_PORT=$HTTPS_PORT
MGC_PORT=8080
TRUSTED_HOSTS=$HOST,localhost,127.0.0.1
CORS_ORIGINS=
OIDC_DISCOVERY_URL=https://sso.example.invalid/.well-known/openid-configuration
OIDC_CLIENT_ID=ci-runtime-client
OIDC_CLIENT_SECRET=ci-runtime-client-secret-0123456789
OIDC_ALLOWED_GROUP=mgc-language-users
OIDC_STATE_SECRET=ci-runtime-state-secret-012345678901234567890123456789
METRICS_TOKEN=ci-runtime-metrics-token-0123456789012345
POSTGRES_DB=mgc_languages
POSTGRES_USER=mgc_languages
POSTGRES_PASSWORD=ci-runtime-database-password-0123456789
TLS_CERT_FILE=.ci-runtime-tls/tls.crt
TLS_KEY_FILE=.ci-runtime-tls/tls.key
TTS_ENABLED=false
OTEL_ENABLED=false
WEB_CONCURRENCY=1
EOF

python scripts/server_security_preflight.py "$ENV_FILE"

# Start only the request path under test. Backup/maintenance have independent
# acceptance drills and are intentionally not part of this transport smoke.
compose up -d --build db app nginx secure-gateway

ready=0
for attempt in $(seq 1 60); do
  if curl --silent --show-error --fail \
      --cacert "$TLS_DIR/tls.crt" \
      --resolve "$HOST:$HTTPS_PORT:127.0.0.1" \
      -A 'MGC-Mobile-Security-Smoke/1.0' \
      -D "$HEADERS_FILE" \
      -o "$BODY_FILE" \
      "https://$HOST:$HTTPS_PORT/health/ready"; then
    ready=1
    break
  fi
  sleep 2
done

if [[ "$ready" -ne 1 ]]; then
  echo "ERROR: HTTPS readiness endpoint did not become available" >&2
  compose ps >&2 || true
  compose logs --no-color db app nginx secure-gateway >&2 || true
  exit 1
fi

python - "$BODY_FILE" <<'PY'
import json
import sys

with open(sys.argv[1], encoding="utf-8") as handle:
    payload = json.load(handle)

assert payload.get("status") == "ready", payload
checks = payload.get("checks") or {}
database = checks.get("database")
assert database == "ok" or (isinstance(database, dict) and database.get("status") == "ok"), checks
assert checks.get("oidc_required") in {"ok", "not_required"}, checks
assert checks.get("oidc_config") == "ok", checks
print("OK: HTTPS request reached an application that verified PostgreSQL readiness")
PY

grep -qi '^strict-transport-security: max-age=31536000' "$HEADERS_FILE"
grep -qi '^x-content-type-options: nosniff' "$HEADERS_FILE"
grep -qi '^x-frame-options: DENY' "$HEADERS_FILE"
grep -qi '^permissions-policy: .*microphone=()' "$HEADERS_FILE"

http_code="$(curl --silent --output /dev/null --write-out '%{http_code}' \
  -H "Host: $HOST" "http://127.0.0.1:$HTTP_PORT/health/ready")"
[[ "$http_code" == "308" ]] || { echo "ERROR: plaintext HTTP returned $http_code instead of 308" >&2; exit 1; }

unauth_code="$(curl --silent --output /dev/null --write-out '%{http_code}' \
  --cacert "$TLS_DIR/tls.crt" \
  --resolve "$HOST:$HTTPS_PORT:127.0.0.1" \
  -A 'MGC-Mobile-Security-Smoke/1.0' \
  "https://$HOST:$HTTPS_PORT/api/me")"
[[ "$unauth_code" == "401" ]] || { echo "ERROR: unauthenticated /api/me returned $unauth_code instead of 401" >&2; exit 1; }

# Only the secure gateway may publish LAN/server ports. App and PostgreSQL must
# remain Docker-internal and therefore have no host port mapping.
[[ -z "$(compose port app 8000 2>/dev/null || true)" ]] || { echo "ERROR: app port is published to host" >&2; exit 1; }
[[ -z "$(compose port db 5432 2>/dev/null || true)" ]] || { echo "ERROR: PostgreSQL port is published to host" >&2; exit 1; }

# Confirm TLS 1.2 is actually negotiable through the externally exposed edge.
printf '' | openssl s_client \
  -connect "127.0.0.1:$HTTPS_PORT" \
  -servername "$HOST" \
  -CAfile "$TLS_DIR/tls.crt" \
  -tls1_2 -verify_return_error >/dev/null 2>&1

echo "PASS: mobile/server chain client -> HTTPS -> secure gateway -> nginx -> app -> PostgreSQL"
