from __future__ import annotations

import argparse
import json
import logging
import time

from app import MAINTENANCE_INTERVAL_SECONDS, SessionLocal, cleanup_runtime_data, operational_event

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("mgc.maintenance")


def run_once(dry_run: bool = False) -> dict:
    with SessionLocal() as db:
        result = cleanup_runtime_data(db, dry_run=dry_run)
    logger.info(json.dumps({"event":"maintenance_cleanup","result":result}, ensure_ascii=False))
    if not dry_run:
        operational_event("maintenance.cleanup", severity="info", component="maintenance", metadata=result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="MGC Languages bounded runtime-data cleanup")
    parser.add_argument("--loop", action="store_true", help="run forever using MAINTENANCE_INTERVAL_SECONDS")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    if not args.loop:
        run_once(args.dry_run)
        return 0
    while True:
        try:
            run_once(args.dry_run)
        except Exception as exc:
            logger.exception(json.dumps({"event":"maintenance_cleanup_failed","error":type(exc).__name__}, ensure_ascii=False))
        time.sleep(MAINTENANCE_INTERVAL_SECONDS)


if __name__ == "__main__":
    raise SystemExit(main())
