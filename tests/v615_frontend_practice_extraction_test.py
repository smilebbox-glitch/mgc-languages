from __future__ import annotations

import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULE = (ROOT / 'static/frontend/practice_games.js').read_text(encoding='utf-8')
BRIDGE = (ROOT / 'static/frontend/legacy_bridge.js').read_text(encoding='utf-8')
RETIRE = (ROOT / 'static/frontend/legacy_retirement.js').read_text(encoding='utf-8')
INDEX = (ROOT / 'static/index.html').read_text(encoding='utf-8')
NAV = (ROOT / 'static/frontend/navigation.js').read_text(encoding='utf-8')
APP = (ROOT / 'static/app.js').read_text(encoding='utf-8')

assert "Object.freeze(['roleplay', 'games', 'xp'])" in MODULE
assert "frontend.register('practice-games'" in MODULE
assert "new Set([" in MODULE and "'hint_small'" in MODULE

for fn in (
    'scenarioProgressKey', 'getScenarioProgress', 'saveScenarioProgress',
    'renderRoleplay', 'answerScenario',
    'startGame', 'finishGame', 'renderGames',
    'renderXpPack', 'buyReward', 'renderXP',
):
    assert f'function {fn}' in MODULE, fn

for token in (
    "/roleplays",
    "legacy().submitPractice(",
    "'scenario-' + item.id",
    "/api/games/",
    "/start?language=",
    "/finish",
    "/api/gamification/me",
    "/api/gamification/rewards",
    "/api/gamification/spend",
    "legacy().playPronunciation",
    "xp_economy",
    "view === 'games' ? 'games'",
    "event.stopImmediatePropagation()",
):
    assert token in MODULE, token

for token in ('renderPracticeRoleplay', 'renderPracticeGames', 'renderPracticeXP'):
    assert token not in MODULE, token
    assert token not in BRIDGE, token

for token in (
    "newSessionId: requireFunction('newSessionId', newSessionId)",
    "submitPractice: requireFunction('submitPractice', submitPractice)",
    "playPronunciation: requireFunction('playPronunciation', playPronunciation)",
    "loadLanguage: requireFunction('loadLanguage', loadLanguage)",
):
    assert token in BRIDGE, token

assert repr('practice-games') in RETIRE
for name in (
    'scenarioProgressKey', 'getScenarioProgress', 'saveScenarioProgress',
    'renderRoleplay', 'answerScenario', 'renderGames', 'startGame',
    'renderXP', 'renderXpPack', 'buyReward', 'xpPanelHTML', 'refreshGamification',
):
    assert repr(name) in RETIRE, name

for name in ('renderRoleplay', 'answerScenario', 'renderGames', 'startGame', 'renderXP', 'renderXpPack', 'buyReward'):
    assert f'function {name}' in APP, name

assert INDEX.index('/frontend/practice_games.js') < INDEX.index('/frontend/legacy_retirement.js')
assert INDEX.index('/frontend/legacy_retirement.js') < INDEX.index('/frontend/navigation.js')
assert "frontend.get('practice-games').navigate(view)" in NAV

bridge_keys = re.findall(r'^\s{6}([A-Za-z][A-Za-z0-9]*):', BRIDGE, flags=re.MULTILINE)
assert len(bridge_keys) <= 18, bridge_keys
assert len(APP.encode('utf-8')) < 150_000

for script in ('practice_games.js', 'legacy_bridge.js', 'legacy_retirement.js', 'navigation.js', 'boot.js'):
    subprocess.run(['node', '--check', str(ROOT / 'static/frontend' / script)], check=True, cwd=ROOT)

print('PASS: v6.0.15 practice/games/XP are canonical and no feature renderer remains in legacy bridge')
