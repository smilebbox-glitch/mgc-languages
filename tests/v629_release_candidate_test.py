from __future__ import annotations

import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = json.loads((ROOT / "RELEASE_MANIFEST_v6.0.29.json").read_text(encoding="utf-8"))
BOOT = (ROOT / "static/frontend/boot.js").read_text(encoding="utf-8")
V628 = (ROOT / "tests/v628_ux_performance_test.py").read_text(encoding="utf-8")
GUARD = (ROOT / "scripts/release_candidate_guard.py").read_text(encoding="utf-8")

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

for game_type in ("quality_gate", "logistics_route", "bom_builder", "dialogue_choice", "shift_incident"):
    assert game_type in MANIFEST["game_contract"]["game_types"]

assert "pilotCandidate: 'v6.0.29'" in BOOT
assert "v6.0.29 RC1" in BOOT
assert "pilotCandidate: 'v6.0.28'" not in V628
assert "int(pilot_match.group(1)) >= 28" in V628

rules = MANIFEST["freeze_rules"]
for key in ("new_game_types", "new_frontend_modules", "new_database_migrations", "new_xp_paths", "feature_additions_after_rc"):
    assert rules[key] is False

for token in (
    "parse_boot_modules",
    "GAME_TYPES",
    "MAX_GAME_ANSWERS",
    "runtime.TERMS",
    "critical file missing/empty",
    "pilotCandidate: 'v6.0.29'",
    "v6.0.29 must not add a new frontend runtime asset",
):
    assert token in GUARD, token

for rel in MANIFEST["critical_files"]:
    path = ROOT / rel
    assert path.is_file() and path.stat().st_size > 0, rel

for rel in MANIFEST["deployment_contract"]["compose_files"]:
    assert (ROOT / rel).is_file(), rel
for rel in MANIFEST["deployment_contract"]["environment_templates"]:
    assert (ROOT / rel).is_file(), rel
assert (ROOT / MANIFEST["deployment_contract"]["one_click_windows"]).is_file()

subprocess.run(["python", str(ROOT / "scripts/release_candidate_guard.py")], check=True, cwd=ROOT)
subprocess.run(["python", str(ROOT / "scripts/release_candidate_guard.py"), "--json"], check=True, cwd=ROOT)
subprocess.run(["python", str(ROOT / "tests/pwa_security_test.py")], check=True, cwd=ROOT)
subprocess.run(["node", "--check", str(ROOT / "static/frontend/boot.js")], check=True, cwd=ROOT)

print("PASS: v6.0.29 RC1 freezes the pilot feature set, 20-game/max-five contract, frontend modules and deployment readiness")
