from __future__ import annotations

import os
import signal
import subprocess
import time

from sqlalchemy import text

from app.core.config import get_settings
from app.core.deployment_safety import record_component_heartbeat, remove_component_heartbeat
from app.db.session import engine

_LOCK_ID = 6316001
_STOP = False


def _node() -> str:
    return f"beat@{os.environ.get('HOSTNAME') or 'local'}"


def _try_lock(conn) -> bool:
    if conn.dialect.name != "postgresql":
        return True
    return bool(conn.execute(text("SELECT pg_try_advisory_lock(:key)"), {"key": _LOCK_ID}).scalar_one())


def _assert_lock_session(conn) -> None:
    # The advisory lock is session-scoped. Losing this connection means leadership is lost;
    # fail closed and terminate Beat before another instance can become leader.
    conn.execute(text("SELECT 1"))


def _unlock(conn) -> None:
    if conn.dialect.name == "postgresql":
        try:
            conn.execute(text("SELECT pg_advisory_unlock(:key)"), {"key": _LOCK_ID})
        except Exception:
            pass


def main() -> int:
    global _STOP
    cfg = get_settings()
    wait_seconds = max(int(getattr(cfg, "scheduler_leader_retry_seconds", 10)), 2)
    heartbeat_seconds = max(int(getattr(cfg, "deployment_component_heartbeat_ttl_seconds", 120)) // 3, 10)
    child: subprocess.Popen | None = None

    with engine.connect() as conn:
        if bool(getattr(cfg, "scheduler_leader_lock_enabled", True)):
            while not _try_lock(conn):
                record_component_heartbeat("beat", node=_node(), state="standby")
                time.sleep(wait_seconds)

        record_component_heartbeat("beat", node=_node(), state="active")
        child = subprocess.Popen([
            "celery", "-A", "app.workers.celery_app.celery", "beat", "--loglevel=INFO"
        ])

        def stop(signum, _frame):
            global _STOP
            _STOP = True
            record_component_heartbeat("beat", node=_node(), state="draining")
            if child and child.poll() is None:
                child.send_signal(signal.SIGTERM if signum != signal.SIGINT else signal.SIGINT)

        signal.signal(signal.SIGTERM, stop)
        signal.signal(signal.SIGINT, stop)

        next_heartbeat = time.monotonic() + heartbeat_seconds
        exit_code = 0
        try:
            while child.poll() is None and not _STOP:
                time.sleep(1)
                now = time.monotonic()
                if now >= next_heartbeat:
                    try:
                        _assert_lock_session(conn)
                    except Exception:
                        # Leadership proof is gone. Stop the publisher before any retry/reconnect.
                        record_component_heartbeat("beat", node=_node(), state="draining")
                        child.terminate()
                        try:
                            child.wait(timeout=30)
                        except subprocess.TimeoutExpired:
                            # Do not continue publishing if warm shutdown itself is stuck.
                            child.kill()
                            child.wait(timeout=10)
                        return 75
                    record_component_heartbeat("beat", node=_node(), state="active")
                    next_heartbeat = now + heartbeat_seconds
            if child.poll() is None:
                child.terminate()
            exit_code = int(child.wait())
            return exit_code
        finally:
            remove_component_heartbeat("beat", node=_node())
            _unlock(conn)


if __name__ == "__main__":
    raise SystemExit(main())
