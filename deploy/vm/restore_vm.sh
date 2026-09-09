#!/usr/bin/env bash
set -euo pipefail
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/common.sh"

check_compose_version
require_cmd gzip
require_env_file

backup="${1:-}"
[[ -n "$backup" && -f "$backup" ]] || {
  echo "Usage: bash deploy/vm/restore_vm.sh backups/vm/<backup>.sql.gz [--yes]" >&2
  exit 2
}

if [[ "${2:-}" != "--yes" ]]; then
  read -r -p "Restore $backup and replace current database content? Type RESTORE: " answer
  [[ "$answer" == "RESTORE" ]] || { echo "Cancelled."; exit 0; }
fi

compose up -d db
for _ in $(seq 1 30); do
  if compose exec -T db sh -c 'pg_isready -U "$POSTGRES_USER" -d "$POSTGRES_DB"' >/dev/null 2>&1; then
    break
  fi
  sleep 2
done

compose stop app nginx >/dev/null 2>&1 || true
gzip -dc "$backup" | compose exec -T db sh -c 'psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB"'
compose up -d app nginx
wait_ready 90
bash "$VM_DIR/check_vm.sh"
echo "Restore completed: $backup"
