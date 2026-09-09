#!/usr/bin/env bash
set -euo pipefail
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/common.sh"

check_compose_version
require_cmd curl
require_cmd openssl

if [[ ! -f "$ENV_FILE" ]]; then
  bash "$VM_DIR/setup_vm.sh"
else
  require_env_file
  if [[ ! -s "$CERT_DIR/server.crt" || ! -s "$CERT_DIR/server.key" ]]; then
    bash "$VM_DIR/setup_vm.sh"
  fi
fi

require_env_file
mkdir -p "$CERT_DIR" "$BACKUP_DIR"

openssl x509 -in "$CERT_DIR/server.crt" -noout -checkend 86400 >/dev/null || {
  echo "ERROR: TLS certificate is invalid or expires within 24 hours." >&2
  exit 2
}

compose config --quiet

echo "Building current application image..."
compose build --pull app

echo "Starting PostgreSQL, application and HTTPS gateway..."
compose up -d db app nginx
wait_ready 90

bash "$VM_DIR/check_vm.sh"

echo
echo "Installation complete: $(public_url)"
echo "Initial admin credentials: deploy/vm/runtime/initial-admin.txt"
echo "Keep TCP 5432 and 8000 closed; only the HTTPS gateway is published by this profile."
