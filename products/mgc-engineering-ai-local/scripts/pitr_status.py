#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from app.db.session import SessionLocal
from app.services.dr_consistency import postgres_pitr_status


def main() -> int:
    with SessionLocal() as db:
        out = postgres_pitr_status(db)
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0 if out.get("pitr_ready") else 3


if __name__ == "__main__":
    raise SystemExit(main())
