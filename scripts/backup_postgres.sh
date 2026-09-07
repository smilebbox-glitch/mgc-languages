#!/bin/sh
set -eu
COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.pilot.yml}"
BACKUP_DIR="${BACKUP_DIR:-./backups}"
RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-14}"
mkdir -p "$BACKUP_DIR"
stamp="$(date -u +%Y%m%dT%H%M%SZ)"
out="$BACKUP_DIR/mgc_languages_${stamp}.dump"
docker compose -f "$COMPOSE_FILE" exec -T db sh -lc 'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc' > "$out"
sha256sum "$out" > "$out.sha256"
find "$BACKUP_DIR" -type f \( -name '*.dump' -o -name '*.dump.sha256' \) -mtime "+$RETENTION_DAYS" -delete
printf 'Backup: %s\n' "$out"
