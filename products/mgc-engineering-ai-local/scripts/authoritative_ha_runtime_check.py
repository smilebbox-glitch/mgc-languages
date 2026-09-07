#!/usr/bin/env python3
from __future__ import annotations
import json
from app.core.authoritative_ha import authoritative_ha_snapshot

snap = authoritative_ha_snapshot()
print(json.dumps(snap, ensure_ascii=False, sort_keys=True))
raise SystemExit(0 if snap.get("write_safe") else 2)
