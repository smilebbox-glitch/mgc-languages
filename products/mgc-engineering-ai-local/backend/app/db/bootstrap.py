from __future__ import annotations

import time
from contextlib import contextmanager

from sqlalchemy import text
from sqlalchemy.engine import Engine
from sqlalchemy.sql.schema import MetaData

from app.db.migrations import ensure_v6313_schema
from app.core.config import get_settings

# Stable, application-specific advisory-lock key. It is intentionally constant across
# replicas so only one process performs additive startup schema work at a time.
MIGRATION_LOCK_KEY = 606200


@contextmanager
def migration_lock(engine: Engine):
    """Serialize startup schema work on PostgreSQL; SQLite/dev remains a no-op lock.

    A bounded try-lock is used instead of an unbounded advisory lock so a broken/stale
    deployment fails fast enough for an operator to investigate rather than hanging forever.
    """
    if engine.dialect.name != "postgresql":
        yield
        return

    timeout = max(float(get_settings().migration_lock_timeout_seconds), 1.0)
    deadline = time.monotonic() + timeout
    with engine.connect() as conn:
        acquired = False
        while time.monotonic() < deadline:
            acquired = bool(conn.execute(text("SELECT pg_try_advisory_lock(:key)"), {"key": MIGRATION_LOCK_KEY}).scalar())
            if acquired:
                break
            time.sleep(0.5)
        if not acquired:
            raise RuntimeError(f"Timed out waiting for database migration lock after {timeout:.0f}s")
        try:
            yield
        finally:
            conn.execute(text("SELECT pg_advisory_unlock(:key)"), {"key": MIGRATION_LOCK_KEY})
            conn.commit()


def bootstrap_schema(engine: Engine, metadata: MetaData) -> None:
    """Create additive tables/columns and record the expected operational schema version."""
    with migration_lock(engine):
        metadata.create_all(bind=engine)
        ensure_v6313_schema(engine)
