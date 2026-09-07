from __future__ import annotations

import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INDEX = (ROOT / 'static/index.html').read_text(encoding='utf-8')
MODULE = (ROOT / 'static/frontend/practice_games.js').read_text(encoding='utf-8')
BRIDGE = (ROOT / 'static/frontend/legacy_bridge.js').read_text(encoding='utf-8')
RETIRE = (ROOT / 'static/frontend/legacy_retirement.js').read_text(encoding='utf-8')
NAV = (ROOT / 'static/frontend/navigation.js').read_text(encoding='utf-8')
BOOT = (ROOT / 'static/frontend/boot.js').read_text(encoding='utf-8')
APP = (ROOT / 'static/app.js').read_text(encoding='utf-8')

assets = ['/frontend/learning.js','/frontend/practice_games.js','/frontend/legacy_retirement.js','/frontend/navigation.js']
positions = [INDEX.index(x) for x in assets]
assert positions == sorted(positions), positions
assert INDEX.count('/frontend/practice_games.js') == 1

for token in (
    "Object.freeze(['roleplay', 'games', 'xp'])",
    "frontend.register('practice-games'",
    "event.stopImmediatePropagation()",
    "legacy().ensureChineseStandardBanner()",
    "view === 'games' ? 'games'",
    "view === 'xp' ? 'xp_economy'",
    "/roleplays", "/api/games/", "/api/gamification/me",
    "/api/gamification/rewards", "/api/gamification/spend",
    "legacy().submitPractice(", "legacy().playPronunciation",
):
    assert token in MODULE, token

for function_name in ('renderRoleplay','answerScenario','renderGames','startGame','finishGame','renderXP','renderXpPack','buyReward'):
    assert f'function {function_name}' in MODULE, function_name

for token in ('renderPracticeRoleplay','renderPracticeGames','renderPracticeXP'):
    assert token not in MODULE, token
    assert token not in BRIDGE, token

for name in ('renderRoleplay','renderGames','renderXP'):
    assert repr(name) in RETIRE, name
    assert f'function {name}' not in APP, name

assert "frontend.get('practice-games').owns(view)" in NAV
assert "frontend.get('practice-games').navigate(view)" in NAV
assert "'practice-games'" in BOOT
assert len(APP.encode('utf-8')) < 30_000

for script in ('practice_games.js','navigation.js','legacy_bridge.js','legacy_retirement.js','boot.js'):
    subprocess.run(['node','--check',str(ROOT / 'static/frontend' / script)], check=True, cwd=ROOT)

print('PASS: practice-games owns roleplay/games/xp and physical shell contains no practice renderers')
