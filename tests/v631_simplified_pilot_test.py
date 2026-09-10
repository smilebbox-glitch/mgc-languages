from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def test_release_identity_and_scope() -> None:
    manifest = json.loads(read("RELEASE_MANIFEST_v6.0.31.json"))
    assert manifest["release"] == "6.0.31"
    assert manifest["status"] == "pilot-ui-simplification"
    assert manifest["base_release"] == "6.0.30"
    assert manifest["pilot_ui"]["presentation_exposed"] is False
    assert manifest["pilot_ui"]["three_d_exposed"] is False
    assert manifest["pilot_ui"]["xp_navigation_exposed"] is False
    assert manifest["pilot_ui"]["assistant_navigation_exposed"] is False
    assert manifest["pilot_ui"]["course30_activity_exposed"] is False


def test_pilot_index_is_lightweight() -> None:
    index = read("static/index.html")
    expected_views = ["home", "topics", "quiz", "roleplay", "course30", "games", "exam"]
    for view in expected_views:
        assert f'data-view="{view}"' in index

    forbidden = [
        'data-view="xp"',
        'id="xpPill"',
        'data-view="assistant"',
        '/frontend/assistant_knowledge.js',
        '/frontend/art_direction_v630.js',
        '/frontend/digital_vehicle_3d_v630.js',
        '/frontend/digital_truck_3d_v630.js',
        '/frontend/game_lab_v618.js',
        '/frontend/game_world_v630.js',
        '/frontend/factory_journey_v2_v630.js',
        '/frontend/premium_home_v631.js',
        '/premium_home_v631.css',
        '/executive_visual_v630.css',
        '/executive_polish_v630.css',
        '/art_direction_v630.css',
        '/digital_vehicle_3d_v630.css',
        '/game_world_v630.css',
    ]
    for token in forbidden:
        assert token not in index, token

    assert '/pilot_simplified_v631.css' in index
    assert '/frontend/practice_games.js' in index
    assert '/frontend/games_ui_fix_v631.js' in index


def test_games_have_one_pilot_owner() -> None:
    navigation = read("static/frontend/navigation.js")
    assert "practice-games" in navigation
    assert "game-lab-v618').navigate('games')" not in navigation
    assert '[data-view="games"], [data-go="games"], [data-pilot-target="games"]' in navigation


def test_games_ui_fix_contract() -> None:
    fix = read("static/frontend/games_ui_fix_v631.js")
    assert "session.game_type !== 'match'" in fix
    assert "Array.isArray(item.options)" in fix
    assert "button.dataset.gameAnswer = String(index)" in fix
    assert "button.textContent = String(options[index])" in fix
    assert "payload.answers = payload.answers.map" in fix
    assert "/^\\d+$/.test(value) ? Number(value) : value" in fix
    assert "button.textContent = '← К играм'" in fix
    assert "gameSession: null" in fix
    assert "games.renderGames()" in fix
    subprocess.run(
        ["node", "--check", str(ROOT / "static/frontend/games_ui_fix_v631.js")],
        check=True,
        cwd=ROOT,
    )


def test_course_and_scenarios_are_simplified() -> None:
    css = read("static/pilot_simplified_v631.css")
    assert ".pair-game{display:none!important}" in css
    assert ".scenario-question .reading-line" in css
    assert ".scenario-option .reading-line" in css
    assert "#xpPill" in css
    assert "[data-view=\"assistant\"]" in css


def test_boot_contract_matches_manifest() -> None:
    manifest = json.loads(read("RELEASE_MANIFEST_v6.0.31.json"))
    boot = read("static/frontend/boot.js")
    match = re.search(r"const requiredModules = \[(.*?)\];", boot, flags=re.S)
    assert match
    actual = re.findall(r"'([^']+)'", match.group(1))
    assert actual == manifest["frontend_modules"]
    assert "pilotCandidate: 'v6.0.31'" in boot
    for retired in ["game-lab-v618", "game-engagement-v618", "factory-journey-v619", "assistant-knowledge"]:
        assert retired not in actual


def test_version_and_feature_defaults() -> None:
    config = read("mgc/config.py")
    assert 'APP_VERSION = os.getenv("APP_VERSION", "6.0.31")' in config
    assert '"games":' in config and '"default_enabled":True' in config
    xp_line = next(line for line in config.splitlines() if '"xp_economy"' in line)
    ai_line = next(line for line in config.splitlines() if '"ai_assistant"' in line)
    assert '"default_enabled":False' in xp_line
    assert '"default_enabled":False' in ai_line


def test_local_visual_assets_exist() -> None:
    manifest = json.loads(read("RELEASE_MANIFEST_v6.0.31.json"))
    visual = manifest["visual_assets"]
    for rel in [visual["hero_chinese"], visual["hero_english"], visual["pilot_style"], *visual["topic_assets"]]:
        path = ROOT / rel
        assert path.is_file(), rel
        assert path.stat().st_size > 100, rel


if __name__ == "__main__":
    test_release_identity_and_scope()
    test_pilot_index_is_lightweight()
    test_games_have_one_pilot_owner()
    test_games_ui_fix_contract()
    test_course_and_scenarios_are_simplified()
    test_boot_contract_matches_manifest()
    test_version_and_feature_defaults()
    test_local_visual_assets_exist()
    print("v6.0.31 simplified pilot regression: OK")
