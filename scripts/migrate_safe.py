from __future__ import annotations
import os, subprocess, sys, time
from sqlalchemy import create_engine, text

url=os.getenv('DATABASE_URL','').strip()
timeout=max(10,min(600,int(os.getenv('MIGRATION_LOCK_TIMEOUT_SECONDS','120'))))
lock_id=int(os.getenv('MIGRATION_ADVISORY_LOCK_ID','5322026'))

def run_alembic():
    subprocess.run([sys.executable,'-m','alembic','upgrade','head'],check=True)

if not (url.startswith('postgresql') or url.startswith('postgres://')):
    run_alembic()
    print('PASS: Alembic migration completed (non-PostgreSQL lock not required)')
    raise SystemExit(0)

if url.startswith('postgres://'):
    url=url.replace('postgres://','postgresql+psycopg://',1)
elif url.startswith('postgresql://') and '+psycopg' not in url:
    url=url.replace('postgresql://','postgresql+psycopg://',1)

engine=create_engine(url,pool_pre_ping=True)
deadline=time.monotonic()+timeout
with engine.connect() as conn:
    acquired=False
    while time.monotonic()<deadline:
        acquired=bool(conn.execute(text('SELECT pg_try_advisory_lock(:id)'),{'id':lock_id}).scalar())
        if acquired:
            break
        time.sleep(1)
    if not acquired:
        raise SystemExit(f'ERROR: migration advisory lock not acquired within {timeout}s')
    try:
        print('INFO: migration advisory lock acquired')
        run_alembic()
        print('PASS: Alembic migration completed under PostgreSQL advisory lock')
    finally:
        try:
            conn.execute(text('SELECT pg_advisory_unlock(:id)'),{'id':lock_id})
        except Exception:
            pass
engine.dispose()
