#!/bin/sh
set -eu
COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.pilot.yml}"
BACKUP_DIR="${BACKUP_DIR:-./backups}"
mkdir -p "$BACKUP_DIR"
stamp="$(date -u +%Y%m%dT%H%M%SZ)"
out="$BACKUP_DIR/mgc_languages_base_${stamp}.tar.gz"
# Pilot rehearsal helper. The PostgreSQL bootstrap user is privileged enough for pg_basebackup in this topology.
docker compose -f "$COMPOSE_FILE" exec -T db sh -lc 'set -eu; rm -rf /tmp/mgc-pitr-base; pg_basebackup -U "$POSTGRES_USER" -D /tmp/mgc-pitr-base -Fp -Xs -P; tar -C /tmp -czf - mgc-pitr-base; rm -rf /tmp/mgc-pitr-base' > "$out"
sha256sum "$out" > "$out.sha256"
echo "Base backup: $out"
echo "NOTE: move base backup and WAL archive off-host before treating PITR as a production control."
