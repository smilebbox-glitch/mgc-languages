from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = json.loads((ROOT / "RELEASE_MANIFEST_v6.0.29.json").read_text(encoding="utf-8"))

# v6.0.29 remains an immutable historical RC1 baseline after v6.0.30 supersedes it.
assert MANIFEST["release"] == "6.0.29"
assert MANIFEST["candidate"] == "RC1"
assert MANIFEST["status"] == "pilot-freeze"
assert MANIFEST["base_release"] == "6.0.28"
assert MANIFEST["freeze"] is True
assert MANIFEST["vocabulary_terms_per_language"] == 2029
assert MANIFEST["game_contract"]["count"] == 20
assert MANIFEST["game_contract"]["max_answers_per_session"] == 5
assert MANIFEST["game_contract"]["anti_farm"] == "unchanged"
assert len(MANIFEST["game_contract"]["game_types"]) == 20
assert len(set(MANIFEST["game_contract"]["game_types"])) == 20

rules = MANIFEST["freeze_rules"]
for key in ("new_game_types", "new_frontend_modules", "new_database_migrations", "new_xp_paths", "feature_additions_after_rc"):
    assert rules[key] is False

for rel in MANIFEST["critical_files"]:
    path = ROOT / rel
    assert path.is_file() and path.stat().st_size > 0, rel

print("PASS: archived v6.0.29 RC1 baseline remains intact while current release advances independently")