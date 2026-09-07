#!/bin/sh
set -eu
DUMP="${1:?Usage: scripts/restore_rehearsal.sh backups/file.dump}"
COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.pilot.yml}"
BACKUP_DIR="${BACKUP_DIR:-./backups}"
[ -f "$DUMP" ] || { echo "Dump not found: $DUMP" >&2; exit 2; }
mkdir -p "$BACKUP_DIR"
if [ -f "$DUMP.sha256" ]; then sha256sum -c "$DUMP.sha256"; fi
stamp="$(date -u +%Y%m%d%H%M%S)"
verified_at="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
start_epoch="$(date +%s)"
test_db="mgc_restore_check_${stamp}"
cleanup() {
  docker compose -f "$COMPOSE_FILE" exec -T -e TEST_DB="$test_db" db sh -lc 'dropdb -U "$POSTGRES_USER" --if-exists "$TEST_DB"' >/dev/null 2>&1 || true
}
trap cleanup EXIT INT TERM

docker compose -f "$COMPOSE_FILE" exec -T -e TEST_DB="$test_db" db sh -lc 'createdb -U "$POSTGRES_USER" "$TEST_DB"'
cat "$DUMP" | docker compose -f "$COMPOSE_FILE" exec -T -e TEST_DB="$test_db" db sh -lc 'pg_restore -U "$POSTGRES_USER" -d "$TEST_DB" --no-owner --no-privileges'
check_output="$(docker compose -f "$COMPOSE_FILE" exec -T -e TEST_DB="$test_db" db sh -lc 'psql -U "$POSTGRES_USER" -d "$TEST_DB" -v ON_ERROR_STOP=1 -Atc "select version_num from alembic_version; select count(*) from users; select count(*) from custom_terms;"')"
end_epoch="$(date +%s)"
duration_seconds="$((end_epoch-start_epoch))"
dump_base="$(basename "$DUMP")"
evidence="$BACKUP_DIR/restore_evidence_${stamp}.restore-ok.json"
cat > "$evidence" <<JSON
{"verified_at":"$verified_at","dump":"$dump_base","duration_seconds":$duration_seconds,"isolated_database":"$test_db","checks":"schema_head,user_count,custom_term_count","result":"PASS"}
JSON
printf '%s\n' "$check_output"
echo "PASS: backup restored into isolated rehearsal database $test_db; production database was not modified"
echo "Restore evidence: $evidence (duration ${duration_seconds}s)"
