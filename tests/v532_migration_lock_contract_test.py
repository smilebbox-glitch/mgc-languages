from pathlib import Path
root=Path(__file__).resolve().parents[1]
script=(root/'scripts/migrate_safe.py').read_text()
entry=(root/'scripts/entrypoint.sh').read_text()
compose=(root/'docker-compose.pilot.yml').read_text()
assert 'pg_try_advisory_lock' in script and 'pg_advisory_unlock' in script
assert 'MIGRATION_LOCK_TIMEOUT_SECONDS' in script and 'alembic' in script
assert 'python scripts/migrate_safe.py' in entry
assert 'MIGRATION_ADVISORY_LOCK_ID:' in compose
print('OK: v5.3.2 serialized PostgreSQL migration contract')
