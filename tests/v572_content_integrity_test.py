from __future__ import annotations
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.content_integrity_guard import audit  # noqa: E402

report = audit()
assert report["ok"], report["errors"]
by_language = {row["language"]: row for row in report["languages"]}
assert by_language["english"]["items"] >= 100, by_language["english"]
assert by_language["chinese"]["items"] >= 100, by_language["chinese"]
assert by_language["english"]["unique_ids"] == by_language["english"]["items"]
assert by_language["chinese"]["unique_ids"] == by_language["chinese"]["items"]

print(
    "OK: v5.7.2 language content integrity — required fields, unique IDs, "
    "levels, pinyin sanity and example coverage"
)
