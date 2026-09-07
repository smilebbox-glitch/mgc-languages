from __future__ import annotations

import argparse
import time

from app.core.deployment_safety import record_component_heartbeat
from app.workers.celery_app import celery


def _nodes(prefix: str, timeout: float) -> list[str]:
    stats = celery.control.inspect(timeout=timeout).stats() or {}
    return sorted(n for n in stats if n.startswith(prefix))


def drain(prefix: str, timeout_seconds: int, inspect_timeout: float = 2.0) -> dict:
    nodes = _nodes(prefix, inspect_timeout)
    if not nodes:
        raise RuntimeError(f"No live Celery worker matches prefix {prefix!r}")
    inspect = celery.control.inspect(destination=nodes, timeout=inspect_timeout)
    queues = inspect.active_queues() or {}
    for node in nodes:
        record_component_heartbeat("worker", node=node, state="draining")
        for queue in queues.get(node, []) or []:
            name = queue.get("name") if isinstance(queue, dict) else None
            if name:
                celery.control.cancel_consumer(name, destination=[node], reply=False)
    deadline = time.monotonic() + max(timeout_seconds, 1)
    last_active: dict = {}
    while time.monotonic() < deadline:
        last_active = celery.control.inspect(destination=nodes, timeout=inspect_timeout).active() or {}
        counts = {node: len(last_active.get(node, []) or []) for node in nodes}
        if all(count == 0 for count in counts.values()):
            return {"status": "drained", "nodes": nodes, "active": counts}
        time.sleep(2)
    counts = {node: len(last_active.get(node, []) or []) for node in nodes}
    raise RuntimeError(f"Worker drain timed out with active tasks: {counts}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Stop consuming new work and wait for active Celery tasks to drain.")
    parser.add_argument("--prefix", required=True)
    parser.add_argument("--timeout", type=int, default=600)
    args = parser.parse_args()
    result = drain(args.prefix, args.timeout)
    print(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
