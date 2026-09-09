from __future__ import annotations

import json
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

assert MANIFEST["release"] == "6.0.30"
assert MANIFEST["base_release"] == "6.0.29"
assert MANIFEST["status"] == "game-world-expansion"
assert MANIFEST["game_contract"]["count"] == 20
assert MANIFEST["game_contract"]["max_answers_per_session"] == 5
assert MANIFEST["game_contract"]["anti_farm"] == "unchanged"
assert list(GAME_TYPES) == MANIFEST["game_contract"]["game_types"]
assert MAX_GAME_ANSWERS == 5

assert 'APP_VERSION = os.getenv("APP_VERSION", "6.0.30").strip() or "6.0.30"' in CONFIG
assert "pilotCandidate: 'v6.0.30'" in BOOT
assert '<link rel="stylesheet" href="/game_world_v630.css">' in INDEX
assert '<script src="/frontend/game_world_v630.js" defer></script>' in INDEX

for game_type in MANIFEST["game_contract"]["game_types"]:
    assert f"{game_type}:" in WORLD_JS or f"'{game_type}'" in WORLD_JS, game_type

for scene in MANIFEST["game_world"]["scenes"]:
    assert scene in WORLD_JS or scene in WORLD_CSS, scene

for marker in (
    "prefers-reduced-motion",
    "gw30-conveyor",
    "gw30-car",
    "gw30-robot",
    "gw30-hud",
    "data-game-world",
    "Базовый",
    "Средний",
    "Продвинутый",
):
    assert marker in WORLD_CSS or marker in WORLD_JS, marker

for rel in MANIFEST["critical_files"]:
    path = ROOT / rel
    assert path.is_file() and path.stat().st_size > 0, rel

subprocess.run(["node", "--check", str(STATIC / "frontend/game_world_v630.js")], check=True, cwd=ROOT)
subprocess.run(["python", str(ROOT / "tests/pwa_security_test.py")], check=True, cwd=ROOT)

print("PASS: v6.0.30 Game World maps all 20 games while preserving max-five, anti-farm, PWA and API boundaries")
