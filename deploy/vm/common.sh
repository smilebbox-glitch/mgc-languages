#!/usr/bin/env bash
set -euo pipefail

VM_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$VM_DIR/../.." && pwd)"
ENV_FILE="$ROOT_DIR/.env.vm"
COMPOSE_FILE="$ROOT_DIR/docker-compose.vm.prod.yml"
RUNTIME_DIR="$VM_DIR/runtime"
CERT_DIR="$RUNTIME_DIR/certs"
BACKUP_DIR="$ROOT_DIR/backups/vm"

compose() {
  docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" "$@"
}

env_value() {
  local key="$1"
  awk -F= -v k="$key" '$1 == k {sub(/^[^=]*=/, ""); print; exit}' "$ENV_FILE"
}

public_url() {
  local host port
  host="$(env_value MGC_PUBLIC_HOST)"
  port="$(env_value MGC_HTTPS_PORT)"
  if [[ "$port" == "443" ]]; then
    printf 'https://%s\n' "$host"
  else
    printf 'https://%s:%s\n' "$host" "$port"
  fi
}

require_cmd() {
  command -v "$1" >/dev/null 2>&1 || {
    echo "ERROR: required command '$1' is not installed." >&2
    return 1
  }
}

require_env_file() {
  [[ -f "$ENV_FILE" ]] || {
    echo "ERROR: $ENV_FILE does not exist. Run: bash deploy/vm/setup_vm.sh" >&2
    exit 2
  }
  if grep -q 'CHANGE_ME_' "$ENV_FILE"; then
    echo "ERROR: $ENV_FILE still contains CHANGE_ME placeholders." >&2
    exit 2
  fi
}

check_compose_version() {
  require_cmd docker
  docker compose version >/dev/null 2>&1 || {
    echo "ERROR: Docker Compose v2 is required (docker compose)." >&2
    exit 2
  }
}

wait_ready() {
  local url tries
  url="$(public_url)/health/ready"
  tries="${1:-90}"
  for _ in $(seq 1 "$tries"); do
    if curl -kfsS --connect-timeout 2 --max-time 5 "$url" >/tmp/mgc-vm-ready.json 2>/dev/null; then
      cat /tmp/mgc-vm-ready.json
      return 0
    fi
    sleep 2
  done
  echo "ERROR: service did not become ready: $url" >&2
  compose ps -a >&2 || true
  compose logs --no-color --tail 120 app nginx db >&2 || true
  return 1
}
