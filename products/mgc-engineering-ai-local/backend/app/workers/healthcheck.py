from __future__ import annotations

import socket

from app.workers.celery_app import celery


def main() -> int:
    # v6.3.16 workers use role-prefixed node names (cpu@<hostname>, io@<hostname>, ...).
    # Inspect the cluster but accept only a pong whose node suffix matches this container;
    # another healthy worker therefore cannot mask a dead local worker.
    hostname = socket.gethostname()
    reply = celery.control.inspect(timeout=3.0).ping() or {}
    for node, value in reply.items():
        if not str(node).endswith(f"@{hostname}"):
            continue
        if isinstance(value, dict) and value.get("ok") == "pong":
            return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
