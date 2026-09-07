from __future__ import annotations

import json
import os
import sys


def env_int(name: str, default: int, minimum: int, maximum: int) -> int:
    raw = os.getenv(name, str(default)).strip()
    try:
        value = int(raw)
    except ValueError as exc:
        raise SystemExit(f"ERROR: {name} must be an integer") from exc
    if not minimum <= value <= maximum:
        raise SystemExit(f"ERROR: {name} must be between {minimum} and {maximum}")
    return value


def capacity_report() -> dict[str, int | bool]:
    workers = env_int("WEB_CONCURRENCY", 1, 1, 16)
    pool_size = env_int("DB_POOL_SIZE", 5, 1, 100)
    max_overflow = env_int("DB_MAX_OVERFLOW", 10, 0, 200)
    postgres_max = env_int("POSTGRES_MAX_CONNECTIONS", 100, 20, 2000)
    reserve = env_int("DB_CONNECTION_RESERVE", 20, 5, 500)
    auxiliary = env_int("CAPACITY_EXPECTED_AUX_CONNECTIONS", 8, 0, 200)
    per_worker_peak = pool_size + max_overflow
    application_peak = workers * per_worker_peak
    usable_for_app = postgres_max - reserve - auxiliary
    ok = usable_for_app >= 1 and application_peak <= usable_for_app
    return {
        "workers": workers,
        "db_pool_size": pool_size,
        "db_max_overflow": max_overflow,
        "per_worker_peak_connections": per_worker_peak,
        "application_peak_connections": application_peak,
        "postgres_max_connections": postgres_max,
        "reserved_connections": reserve,
        "expected_aux_connections": auxiliary,
        "usable_application_connections": max(0, usable_for_app),
        "headroom_after_application_peak": max(0, usable_for_app - application_peak),
        "ok": ok,
    }


def main() -> int:
    report = capacity_report()
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    if not report["ok"]:
        print(
            "ERROR: configured worker/pool peak exceeds the PostgreSQL connection budget; "
            "reduce WEB_CONCURRENCY/DB_POOL_SIZE/DB_MAX_OVERFLOW or raise POSTGRES_MAX_CONNECTIONS safely",
            file=sys.stderr,
        )
        return 2
    print("PASS: PostgreSQL connection budget is safe for configured worker/pool topology")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
