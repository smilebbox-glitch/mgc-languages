#!/usr/bin/env bash
set -euo pipefail

VM_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$VM_DIR/../.." && pwd)"
ENV_FILE="$ROOT_DIR/.env.vm"
TEMPLATE_FILE="$ROOT_DIR/.env.vm.example"
RUNTIME_DIR="$VM_DIR/runtime"
CERT_DIR="$RUNTIME_DIR/certs"

require() {
  command -v "$1" >/dev/null 2>&1 || {
    echo "ERROR: '$1' is required. See VM_IT_DIRECTOR.md." >&2
    exit 2
  }
}

set_env() {
  local key="$1" value="$2"
  if grep -q "^${key}=" "$ENV_FILE"; then
    sed -i "s#^${key}=.*#${key}=${value}#" "$ENV_FILE"
  else
    printf '%s=%s\n' "$key" "$value" >> "$ENV_FILE"
  fi
}

read_env() {
  local key="$1"
  awk -F= -v k="$key" '$1 == k {sub(/^[^=]*=/, ""); print; exit}' "$ENV_FILE"
}

require docker
require openssl
require curl
require git
docker compose version >/dev/null 2>&1 || {
  echo "ERROR: Docker Compose v2 is required (docker compose)." >&2
  exit 2
}

umask 077
mkdir -p "$RUNTIME_DIR" "$CERT_DIR" "$ROOT_DIR/backups/vm"

if [[ ! -f "$ENV_FILE" ]]; then
  cp "$TEMPLATE_FILE" "$ENV_FILE"
fi
chmod 600 "$ENV_FILE"

host="${MGC_VM_HOST:-}"
if [[ -z "$host" ]]; then
  host="$(hostname -I 2>/dev/null | awk '{print $1}')"
fi
if [[ -z "$host" ]]; then
  echo "ERROR: cannot detect VM LAN address. Re-run with MGC_VM_HOST=10.0.0.25 or a DNS name." >&2
  exit 2
fi
if [[ ! "$host" =~ ^[A-Za-z0-9.-]+$ ]]; then
  echo "ERROR: MGC_VM_HOST must be an IPv4 address or DNS name." >&2
  exit 2
fi

set_env MGC_PUBLIC_HOST "$host"
set_env MGC_TRUSTED_HOSTS "localhost,127.0.0.1,$host"

replace_secret() {
  local key="$1" marker="$2" value
  value="$(read_env "$key")"
  if [[ -z "$value" || "$value" == "$marker" || "$value" == CHANGE_ME_* ]]; then
    set_env "$key" "$(openssl rand -hex 32)"
  fi
}

replace_secret POSTGRES_PASSWORD CHANGE_ME_DB_PASSWORD
replace_secret OIDC_STATE_SECRET CHANGE_ME_OIDC_SECRET
replace_secret METRICS_TOKEN CHANGE_ME_METRICS_TOKEN

admin_password="$(read_env MGC_ADMIN_PASSWORD)"
if [[ -n "${MGC_VM_ADMIN_PASSWORD:-}" ]]; then
  admin_password="$MGC_VM_ADMIN_PASSWORD"
  set_env MGC_ADMIN_PASSWORD "$admin_password"
elif [[ -z "$admin_password" || "$admin_password" == CHANGE_ME_* ]]; then
  admin_password="$(openssl rand -hex 18)"
  set_env MGC_ADMIN_PASSWORD "$admin_password"
fi

cert_source="${MGC_TLS_CERT_SOURCE:-}"
key_source="${MGC_TLS_KEY_SOURCE:-}"
if [[ -n "$cert_source" || -n "$key_source" ]]; then
  if [[ -z "$cert_source" || -z "$key_source" || ! -s "$cert_source" || ! -s "$key_source" ]]; then
    echo "ERROR: provide both valid MGC_TLS_CERT_SOURCE and MGC_TLS_KEY_SOURCE." >&2
    exit 2
  fi
  install -m 0644 "$cert_source" "$CERT_DIR/server.crt"
  install -m 0600 "$key_source" "$CERT_DIR/server.key"
  set_env MGC_TLS_MODE company
elif [[ ! -s "$CERT_DIR/server.crt" || ! -s "$CERT_DIR/server.key" ]]; then
  if [[ "$host" =~ ^([0-9]{1,3}\.){3}[0-9]{1,3}$ ]]; then
    san="IP:$host"
  else
    san="DNS:$host"
  fi
  openssl req -x509 -newkey rsa:3072 -sha256 -nodes \
    -keyout "$CERT_DIR/server.key" \
    -out "$CERT_DIR/server.crt" \
    -days 365 \
    -subj "/CN=$host" \
    -addext "subjectAltName=$san" \
    -addext "keyUsage=digitalSignature,keyEncipherment" \
    -addext "extendedKeyUsage=serverAuth" >/dev/null 2>&1
  chmod 600 "$CERT_DIR/server.key"
  chmod 644 "$CERT_DIR/server.crt"
  set_env MGC_TLS_MODE self-signed
fi

if grep -q 'CHANGE_ME_' "$ENV_FILE"; then
  echo "ERROR: unresolved CHANGE_ME value remains in $ENV_FILE." >&2
  exit 2
fi

url="https://$host"
port="$(read_env MGC_HTTPS_PORT)"
if [[ "$port" != "443" ]]; then
  url="$url:$port"
fi

credentials="$RUNTIME_DIR/initial-admin.txt"
{
  echo "MGC Languages — initial administrator"
  echo "URL: $url"
  echo "Login: $(read_env MGC_ADMIN_USERNAME)"
  echo "Password: $(read_env MGC_ADMIN_PASSWORD)"
  echo "TLS mode: $(read_env MGC_TLS_MODE)"
  echo "Delete this file after the credentials are transferred to the owner."
} > "$credentials"
chmod 600 "$credentials"

echo "VM configuration prepared."
echo "Host: $host"
echo "URL: $url"
echo "Initial admin credentials: deploy/vm/runtime/initial-admin.txt (mode 600)"
if [[ "$(read_env MGC_TLS_MODE)" == "self-signed" ]]; then
  echo "TLS: self-signed fallback. For phone/PWA use, trust this certificate on devices or replace it with a company-CA certificate."
else
  echo "TLS: company-provided certificate."
fi
