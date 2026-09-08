from __future__ import annotations

import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MISSIONS = (ROOT / "static/frontend/arcade_missions_v620.js").read_text(encoding="utf-8")
CSS = (ROOT / "static/arcade_missions_v620.css").read_text(encoding="utf-8")
INDEX = (ROOT / "static/index.html").read_text(encoding="utf-8")
BOOT = (ROOT / "static/frontend/boot.js").read_text(encoding="utf-8")

# The layer must stay additive over the 20-game arcade rather than inventing
# a second game engine.
assert "frontend.get('game-lab-v618')" in MISSIONS
assert "frontend.get('game-engagement-v618')" in MISSIONS
assert "recommendationsForDepartment" in MISSIONS
assert "engagement().progress()" in MISSIONS

# Three daily missions: department context, discovery, and weak-point recovery.
for marker in ["ЦЕХОВАЯ МИССИЯ", "НОВАЯ МЕХАНИКА", "ТОЧКА РОСТА"]:
    assert marker in MISSIONS, marker
assert "Три короткие миссии на сегодня" in MISSIONS
assert "doneCount + '/3'" in MISSIONS
assert "data-mission-slot" in MISSIONS

# Boss mode is gated by completion of all daily missions and is department-aware.
assert "BOSS_BY_GROUP" in MISSIONS
assert "bossUnlocked = doneCount >= missions.length" in MISSIONS
assert "Boss Shift" in MISSIONS
for group in ["paint", "logistics", "body", "assembly", "quality", "rd", "purchasing", "default"]:
    assert f"{group}:" in MISSIONS, group
for topic in ["Окраска", "Логистика JIT/JIS", "Кузов и компоненты", "Сборка автомобиля", "Качество в автопроме"]:
    assert topic in MISSIONS, topic

# Daily state is separated by user, language and date, and result capture stores scores.
assert "mgc-arcade-missions-v620-" in MISSIONS
assert "userKey()" in MISSIONS
assert "snapshot().language" in MISSIONS
assert "todayKey()" in MISSIONS
assert "daily.scores[mission.slot] = score" in MISSIONS
assert "daily.bossScore" in MISSIONS

# Integration and release contract.
assert "/arcade_missions_v620.css" in INDEX
assert "/frontend/arcade_missions_v620.js" in INDEX
assert INDEX.index("arcade_missions_v620.js") < INDEX.index("frontend/boot.js")
assert "'arcade-missions-v620'" in BOOT
assert "pilotCandidate: 'v6.0.20'" in BOOT
assert ".arcade-missions-v620" in CSS
assert ".boss-shift" in CSS

subprocess.run(["node", "--check", str(ROOT / "static/frontend/arcade_missions_v620.js")], check=True, cwd=ROOT)

print("PASS: v6.0.20 adds three adaptive daily missions and a department-aware Boss Shift over the 20-game arcade")
