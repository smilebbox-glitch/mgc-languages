from __future__ import annotations

import re
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INDEX = (ROOT / 'static/index.html').read_text(encoding='utf-8')
HOME = (ROOT / 'static/frontend/pilot_home.js').read_text(encoding='utf-8')
NAV = (ROOT / 'static/frontend/navigation.js').read_text(encoding='utf-8')
BOOT = (ROOT / 'static/frontend/boot.js').read_text(encoding='utf-8')
CSS = (ROOT / 'static/pilot.css').read_text(encoding='utf-8')
RUNBOOK = (ROOT / 'docs/COMPANY_PILOT_RUNBOOK_v6.0.17.md').read_text(encoding='utf-8')
UAT = (ROOT / 'docs/PILOT_UAT_v6.0.17.md').read_text(encoding='utf-8')
ENV = (ROOT / '.env.company-pilot.example').read_text(encoding='utf-8')
ONE_CLICK = (ROOT / 'docs/ONE_CLICK_START_v6.0.17.md').read_text(encoding='utf-8')
BAT = (ROOT / 'START_COMPANY_PILOT.bat').read_text(encoding='utf-8')
PS1 = (ROOT / 'scripts/start_company_pilot.ps1').read_text(encoding='utf-8')

# Pilot home is loaded before legacy learning so its capture-phase Home ownership wins.
assert INDEX.index('/frontend/pilot_home.js') < INDEX.index('/frontend/learning.js')
assert INDEX.index('/frontend/learning.js') < INDEX.index('/frontend/navigation.js')
assert '/pilot.css' in INDEX
assert "frontend.register('pilot-home'" in HOME
assert "String(view || '') === 'home'" in HOME
assert "frontend.get('pilot-home').owns(view)" in NAV
assert NAV.index("frontend.get('pilot-home')") < NAV.index("frontend.get('learning')")
assert "'pilot-home'" in BOOT

# Approved bilingual pilot behavior.
for token in (
    'Китайский язык для автопрома',
    'English for the automotive industry',
    'Фраза дня',
    'План на сегодня',
    'Быстрый доступ',
    'Подборка терминов',
    'Информация о китайском',
):
    assert token in HOME or token in INDEX, token
assert 'About English' not in INDEX
assert 'Pilot · Wave' not in HOME
assert 'Сценарий смены' not in HOME
assert 'Новая сегодня' not in HOME
assert 'обновляются ежедневно' not in HOME

# Homepage quote grammar regression guard.
assert 'Большие цели начинаются с маленьких слов.' in HOME
assert 'Большее цели' not in HOME

# Daily phrase is deterministic per calendar day and refreshes after midnight.
for token in (
    'function dayNumber(date)',
    'function dailyPhrase(language, date)',
    'Date.UTC(d.getFullYear(), d.getMonth(), d.getDate())',
    'function scheduleMidnightRefresh()',
    'new Date(now.getFullYear(), now.getMonth(), now.getDate() + 1',
):
    assert token in HOME, token
assert HOME.count("['") >= 32, 'expected bilingual curated phrase pools'
for i in range(1, 8):
    assert f"/pilot/phrase-' + ((index % 7" in HOME if i == 1 else True
    path = ROOT / 'static' / 'pilot' / f'phrase-{i}.svg'
    assert path.exists(), path
    ET.parse(path)
for name in ('hero-chinese.svg', 'hero-english.svg'):
    path = ROOT / 'static' / 'pilot' / name
    assert path.exists(), path
    ET.parse(path)

# Sidebar follows approved pilot information architecture: notifications stay in top/right UI, not left nav.
assert 'data-view="notifications"' in INDEX  # top notification button remains
sidebar = INDEX[INDEX.index('<aside id="sidebar"'):INDEX.index('</aside>')]
assert 'data-view="notifications"' not in sidebar
assert 'Информация о китайском' in sidebar

# Company launch gate is secure-by-default template + executable preflight/runbook/UAT.
for token in (
    'AUTH_MODE=oidc', 'REGISTRATION_ENABLED=false', 'COOKIE_SECURE=true',
    'READY_REQUIRE_OIDC=true', 'READY_REQUIRE_SECURE_COOKIE=true',
    'READY_REQUIRE_RLS=true', 'READY_REQUIRE_TERM_APPROVAL=true',
):
    assert token in ENV, token
for token in ('GO / GO WITH ACTIONS / NO-GO', 'no open S1/S2', 'company_pilot_preflight.py'):
    assert token.lower() in (RUNBOOK + UAT).lower(), token

# One-click Windows startup must preserve the corporate safety gate instead of bypassing it.
for path in (ROOT / 'START_COMPANY_PILOT.bat', ROOT / 'scripts/start_company_pilot.ps1', ROOT / 'docs/ONE_CLICK_START_v6.0.17.md'):
    assert path.exists(), path
assert 'start_company_pilot.ps1' in BAT
for token in (
    'docker info',
    'docker compose version',
    'company_pilot_preflight.py',
    '--strict-corporate',
    'docker-compose.pilot.yml',
    ' build',
    ' up -d',
    '/health/ready',
    'Start-Process',
):
    assert token in PS1, token
assert 'down -v' not in PS1.lower()
assert 'one double-click' in ONE_CLICK.lower()

for script in ('pilot_home.js', 'navigation.js', 'boot.js'):
    subprocess.run(['node', '--check', str(ROOT / 'static/frontend' / script)], check=True, cwd=ROOT)
subprocess.run([sys.executable, '-m', 'py_compile', str(ROOT / 'scripts/company_pilot_preflight.py')], check=True, cwd=ROOT)

# Visual system has responsive company-pilot layouts.
for token in ('.pilot-dashboard', '.pilot-hero-chinese', '.pilot-hero-english', '.pilot-next-grid', '@media(max-width:820px)'):
    assert token in CSS, token

print('PASS: v6.0.17 company pilot candidate has approved bilingual UI, daily rotation, one-click startup and GO/NO-GO operations gate')
