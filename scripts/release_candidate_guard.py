from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = ROOT / "RELEASE_MANIFEST_v6.0.31.json"
BOOT_PATH = ROOT / "static/frontend/boot.js"
INDEX_PATH = ROOT / "static/index.html"
CONFIG_PATH = ROOT / "mgc/config.py"

os.environ.setdefault("AUTO_CREATE_SCHEMA", "false")
os.environ.setdefault("MGC_ADMIN_USERNAME", "")
os.environ.setdefault("MGC_ADMIN_PASSWORD", "")

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from mgc.services.practice_games import GAME_TYPES, MAX_GAME_ANSWERS  # noqa: E402
import app as runtime  # noqa: E402


def parse_boot_modules(boot: str) -> list[str]:
    match = re.search(r"const requiredModules = \[(.*?)\];", boot, flags=re.S)
    if not match:
        raise AssertionError("requiredModules array not found in boot.js")
    return re.findall(r"'([^']+)'", match.group(1))


def check(ok: bool, message: str, failures: list[str]) -> None:
    if not ok:
        failures.append(message)


def public_path(rel: str) -> str:
    return "/" + rel.removeprefix("static/")


def main() -> int:
    parser = argparse.ArgumentParser(description="MGC Languages v6.0.31 simplified Company Pilot release guard")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    failures: list[str] = []
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    boot = BOOT_PATH.read_text(encoding="utf-8")
    index = INDEX_PATH.read_text(encoding="utf-8")
    config = CONFIG_PATH.read_text(encoding="utf-8")

    check(manifest.get("release") == "6.0.31", "manifest release must be 6.0.31", failures)
    check(manifest.get("status") == "pilot-ui-simplification", "status must be pilot-ui-simplification", failures)
    check(manifest.get("base_release") == "6.0.30", "base release must be v6.0.30", failures)
    check(manifest.get("freeze") is False, "v6.0.31 must remain a mutable Company Pilot release", failures)

    check(len(GAME_TYPES) == manifest["games"]["backend_game_types_preserved"], "backend game-type count changed", failures)
    check(MAX_GAME_ANSWERS == manifest["games"]["max_answers_per_session"], "max game answers changed", failures)
    check(set(manifest["games"]["catalog"]).issubset(set(GAME_TYPES)), "pilot game catalog is not a backend subset", failures)

    check(len(runtime.TERMS["chinese"]) == 2029, "Chinese runtime vocabulary must remain 2029", failures)
    check(len(runtime.TERMS["english"]) == 2029, "English runtime vocabulary must remain 2029", failures)
    check(len(runtime.TERMS["chinese"]) == len(runtime.TERMS["english"]), "Chinese/English parity must remain exact", failures)

    actual_modules = parse_boot_modules(boot)
    expected_modules = manifest["frontend_modules"]
    check(actual_modules == expected_modules, "boot requiredModules differs from v6.0.31 manifest", failures)
    check("pilotCandidate: 'v6.0.31'" in boot, "boot.js must publish pilotCandidate v6.0.31", failures)
    check('APP_VERSION = os.getenv("APP_VERSION", "6.0.31")' in config, "default APP_VERSION must be 6.0.31", failures)

    pilot = manifest["pilot_ui"]
    for view in pilot["learner_navigation"]:
        check(f'data-view="{view}"' in index, f"learner navigation missing: {view}", failures)
    check('data-view="xp"' not in index, "XP navigation must not be exposed", failures)
    check('id="xpPill"' not in index, "XP topbar pill must not be exposed", failures)
    check('data-view="assistant"' not in index, "Assistant navigation must not be exposed", failures)
    check('/frontend/assistant_knowledge.js' not in index, "Assistant runtime must not load in pilot index", failures)

    check('/pilot_simplified_v631.css' in index, "simplified pilot stylesheet must load", failures)
    visual = manifest["visual_assets"]
    for rel in [visual["hero_chinese"], visual["hero_english"], visual["pilot_style"], *visual["topic_assets"]]:
        check((ROOT / rel).is_file(), f"pilot visual asset missing: {rel}", failures)

    for rel in manifest["not_loaded_by_pilot_index"]:
        check(public_path(rel) not in index, f"retired pilot asset is still loaded by index: {rel}", failures)

    nav = (ROOT / "static/frontend/navigation.js").read_text(encoding="utf-8")
    check("practice-games" in nav, "Games route must reference practice-games", failures)
    check("game-lab-v618').navigate('games')" not in nav, "Games route must not force game-lab-v618", failures)

    css = (ROOT / visual["pilot_style"]).read_text(encoding="utf-8")
    check(".pair-game{display:none!important}" in css, "30-day Activity block must be hidden in simplified UI", failures)
    check(".scenario-question .reading-line" in css, "scenario Russian reading suppression missing", failures)

    invariants = manifest["invariants"]
    check(invariants.get("database_migrations") == "none", "v6.0.31 must not require a database migration", failures)
    check(invariants.get("game_scoring") == "unchanged", "game scoring must remain unchanged", failures)
    check(invariants.get("api_contract") == "unchanged", "API contract must remain unchanged", failures)
    check(invariants.get("pwa_private_cache_isolation") == "preserved", "PWA private cache isolation must be preserved", failures)

    for rel in manifest["critical_files"]:
        path = ROOT / rel
        check(path.is_file() and path.stat().st_size > 0, f"critical file missing/empty: {rel}", failures)

    deployment = manifest["deployment_contract"]
    for rel in deployment["compose_files"] + deployment["environment_templates"]:
        check((ROOT / rel).is_file(), f"deployment file missing: {rel}", failures)
    check((ROOT / deployment["one_click_windows"]).is_file(), "one-click Company Pilot launcher missing", failures)

    result = {
        "release": "6.0.31",
        "status": "GO" if not failures else "NO-GO",
        "backend_game_types": len(GAME_TYPES),
        "pilot_game_types": len(manifest["games"]["catalog"]),
        "max_answers": MAX_GAME_ANSWERS,
        "frontend_modules": len(actual_modules),
        "vocabulary": {"chinese": len(runtime.TERMS["chinese"]), "english": len(runtime.TERMS["english"])},
        "failures": failures,
    }

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"MGC Languages v6.0.31 Simplified Pilot: {result['status']}")
        print(f"backend game types={result['backend_game_types']} | pilot games={result['pilot_game_types']} | max answers={result['max_answers']}")
        for failure in failures:
            print(f"FAIL: {failure}")

    return 0 if not failures else 2


if __name__ == "__main__":
    raise SystemExit(main())
