from __future__ import annotations

import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INDEX = (ROOT / 'static/index.html').read_text(encoding='utf-8')
MODULE = (ROOT / 'static/frontend/practice_games.js').read_text(encoding='utf-8')
BRIDGE = (ROOT / 'static/frontend/legacy_bridge.js').read_text(encoding='utf-8')
NAV = (ROOT / 'static/frontend/navigation.js').read_text(encoding='utf-8')
BOOT = (ROOT / 'static/frontend/boot.js').read_text(encoding='utf-8')
APP = (ROOT / 'static/app.js').read_text(encoding='utf-8')

assets = ['/frontend/learning.js', '/frontend/practice_games.js', '/frontend/navigation.js']
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
    "Эта функция пока не включена для вашей волны пилота",
    "renderPracticeRoleplay",
    "renderPracticeGames",
    "renderPracticeXP",
):
    assert token in MODULE, token

for token in (
    "renderPracticeRoleplay: requireFunction('renderRoleplay', renderRoleplay)",
    "renderPracticeGames: requireFunction('renderGames', renderGames)",
    "renderPracticeXP: requireFunction('renderXP', renderXP)",
):
    assert token in BRIDGE, token

assert "frontend.get('practice-games').owns(view)" in NAV
assert "frontend.get('practice-games').navigate(view)" in NAV
assert "'practice-games'" in BOOT

for name in ('renderRoleplay', 'renderGames', 'renderXP'):
    assert f'function {name}' in APP
assert len(APP.encode('utf-8')) < 150_000

for script in ('practice_games.js', 'navigation.js', 'legacy_bridge.js', 'boot.js'):
    subprocess.run(['node', '--check', str(ROOT / 'static/frontend' / script)], check=True, cwd=ROOT)

print('PASS: v6.0.4 practice-games module owns roleplay/games/xp with pilot feature parity and staged fallback')
