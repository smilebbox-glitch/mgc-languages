from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STATIC = ROOT / "static"
MANIFEST = json.loads((ROOT / "RELEASE_MANIFEST_v6.0.30.json").read_text(encoding="utf-8"))
INDEX = (STATIC / "index.html").read_text(encoding="utf-8")
BOOT = (STATIC / "frontend/boot.js").read_text(encoding="utf-8")
CONFIG = (ROOT / "mgc/config.py").read_text(encoding="utf-8")
WORLD_JS = (STATIC / "frontend/game_world_v630.js").read_text(encoding="utf-8")
WORLD_CSS = (STATIC / "game_world_v630.css").read_text(encoding="utf-8")

from mgc.services.practice_games import GAME_TYPES, MAX_GAME_ANSWERS

assert MANIFEST["release"] == "6.0.30", MANIFEST.get("release")
assert MANIFEST["base_release"] == "6.0.29", MANIFEST.get("base_release")
assert MANIFEST["status"] == "game-world-expansion", MANIFEST.get("status")
assert MANIFEST["game_contract"]["count"] == 20
assert MANIFEST["game_contract"]["max_answers_per_session"] == 5
assert MANIFEST["game_contract"]["anti_farm"] == "unchanged"
assert list(GAME_TYPES) == MANIFEST["game_contract"]["game_types"], (list(GAME_TYPES), MANIFEST["game_contract"]["game_types"])
assert MAX_GAME_ANSWERS == 5, MAX_GAME_ANSWERS

assert 'APP_VERSION = os.getenv("APP_VERSION", "6.0.30").strip() or "6.0.30"' in CONFIG, "config version"
assert "pilotCandidate: 'v6.0.30'" in BOOT, "boot version"
assert '<link rel="stylesheet" href="/game_world_v630.css">' in INDEX, "Game World CSS not loaded"
assert '<script src="/frontend/game_world_v630.js" defer></script>' in INDEX, "Game World JS not loaded"

# Parse the declared GAME_WORLD object keys rather than depending on one formatting style.
world_block = re.search(r"const GAME_WORLD = Object\.freeze\(\{(.*?)\}\);", WORLD_JS, flags=re.S)
assert world_block, "GAME_WORLD mapping not found"
world_source = world_block.group(1)
for game_type in MANIFEST["game_contract"]["game_types"]:
    assert re.search(rf"(?:^|\s|,)['\"]?{re.escape(game_type)}['\"]?\s*:", world_source), f"missing Game World mapping: {game_type}"

for scene in MANIFEST["game_world"]["scenes"]:
    assert scene in WORLD_JS or scene in WORLD_CSS, f"missing scene: {scene}"

for marker in (
    "prefers-reduced-motion",
    "gw30-conveyor",
    "gw30-car",
    "gw30-robot",
    "gw30-hud",
    "Базовый",
    "Средний",
    "Продвинутый",
):
    assert marker in WORLD_CSS or marker in WORLD_JS, f"missing Game World marker: {marker}"

for rel in MANIFEST["critical_files"]:
    path = ROOT / rel
    assert path.is_file() and path.stat().st_size > 0, f"critical file missing: {rel}"

subprocess.run(["node", "--check", str(STATIC / "frontend/game_world_v630.js")], check=True, cwd=ROOT)
subprocess.run(["node", "--check", str(STATIC / "frontend/boot.js")], check=True, cwd=ROOT)

print("PASS: v6.0.30 Game World maps all 20 games while preserving max-five, anti-farm and runtime boundaries")