#!/bin/sh
set -eu
if [ "${CONFIRM_RESTORE:-}" != "YES" ]; then
  echo "Refusing destructive restore. Set CONFIRM_RESTORE=YES and provide dump path." >&2
  exit 2
fi
DUMP="${1:?Usage: CONFIRM_RESTORE=YES scripts/restore_postgres.sh backups/file.dump}"
COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.pilot.yml}"
[ -f "$DUMP" ] || { echo "Dump not found: $DUMP" >&2; exit 2; }
if [ -f "$DUMP.sha256" ]; then sha256sum -c "$DUMP.sha256"; fi
docker compose -f "$COMPOSE_FILE" exec -T db sh -lc 'dropdb -U "$POSTGRES_USER" --if-exists "$POSTGRES_DB" && createdb -U "$POSTGRES_USER" "$POSTGRES_DB"'
docker compose -f "$COMPOSE_FILE" exec -T db sh -lc 'pg_restore -U "$POSTGRES_USER" -d "$POSTGRES_DB" --clean --if-exists --no-owner --no-privileges' < "$DUMP"
echo "Restore completed. Run: python scripts/container_smoke.py"
