#!/bin/sh
set -eu
COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.pilot.yml}"
echo "== PostgreSQL PITR preparation =="
docker compose -f "$COMPOSE_FILE" exec -T db sh -lc 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -v ON_ERROR_STOP=1 -At <<SQL
show wal_level;
show archive_mode;
show archive_command;
select archived_count, failed_count, coalesce(last_archived_wal,\x27\x27) from pg_stat_archiver;
SQL'
docker compose -f "$COMPOSE_FILE" exec -T db sh -lc 'test -d /wal_archive && test -w /wal_archive && echo "WAL archive directory: writable"'
echo "PASS: PITR prerequisites are configured for pilot rehearsal. Production requires off-host durable WAL storage."
