#!/usr/bin/env bash
set -euo pipefail
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/common.sh"

check_compose_version
require_cmd gzip
require_cmd sha256sum
require_env_file
mkdir -p "$BACKUP_DIR"
umask 077

timestamp="$(date -u +%Y%m%dT%H%M%SZ)"
backup="$BACKUP_DIR/mgc_languages_${timestamp}.sql.gz"
meta="$backup.meta"

cid="$(compose ps -q db)"
[[ -n "$cid" ]] || { echo "ERROR: database container is not running." >&2; exit 1; }

compose exec -T db sh -c 'pg_dump --clean --if-exists --no-owner --no-privileges -U "$POSTGRES_USER" -d "$POSTGRES_DB"' | gzip -9 > "$backup"
[[ -s "$backup" ]] || { echo "ERROR: backup file is empty." >&2; rm -f "$backup"; exit 1; }
chmod 600 "$backup"

{
  echo "created_utc=$timestamp"
  echo "git_sha=$(git -C "$ROOT_DIR" rev-parse HEAD 2>/dev/null || echo unknown)"
  echo "database=$(env_value POSTGRES_DB)"
  echo "sha256=$(sha256sum "$backup" | awk '{print $1}')"
} > "$meta"
chmod 600 "$meta"

echo "Backup created: $backup"
echo "Metadata: $meta"
