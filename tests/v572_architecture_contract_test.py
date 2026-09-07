from __future__ import annotations
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.api_contract_guard import audit  # noqa: E402

report = audit()
assert report["ok"], report["errors"]
assert report["stats"]["route_count"] >= 50, report["stats"]
assert report["stats"]["admin_route_count"] >= 10, report["stats"]

print(
    "OK: v5.7.2 architecture contract — unique routes, guarded admin API, "
    "CSRF allowlist, root mount order and monolith size budgets"
)
