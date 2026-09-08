from __future__ import annotations

import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CHAINS = (ROOT / "static/frontend/decision_chains_v622.js").read_text(encoding="utf-8")
CSS = (ROOT / "static/decision_chains_v622.css").read_text(encoding="utf-8")
INDEX = (ROOT / "static/index.html").read_text(encoding="utf-8")
BOOT = (ROOT / "static/frontend/boot.js").read_text(encoding="utf-8")

# v6.0.22 must build on v6.0.21 difficulty/scene detection rather than create a second backend game engine.
assert 'frontend.get("game-depth-v621")' in CHAINS
assert "depth().effectiveDifficulty(index)" in CHAINS
assert "depth().detectScene(session.game_type, item)" in CHAINS
assert "level === \"shift\" || level === \"expert\"" in CHAINS
assert "CHAIN_STEPS = 3" in CHAINS
assert "/api/games/" not in CHAINS

# Eight automotive decision families cover real production escalation patterns.
for family in ["line_stop", "quality", "logistics", "welding", "paint", "safety", "engineering", "supplier"]:
    assert f"{family}: {{" in CHAINS, family
for marker in [
    "Andon / Line Stop", "Quality Escalation", "Material Shortage", "Body Shop Containment",
    "Paint Process Recovery", "Safety Near Miss", "Engineering Change", "Supplier Escalation",
]:
    assert marker in CHAINS, marker

# Every chain changes the interaction flow: decisions lock the original task until the 3-step chain is completed.
for marker in [
    "v622-chain-locked", "data-v622-option", "data-v622-next", "record.risks.push",
    "Последствие неправильного решения", "Production judgement", "DECISION CHAIN COMPLETE",
]:
    assert marker in CHAINS or marker in CSS, marker
assert "lockStage(stage)" in CHAINS
assert "unlockStage(stage)" in CHAINS
assert "record.step >= CHAIN_STEPS - 1" in CHAINS

# Language learning stays embedded in the production decision: Chinese + pinyin and English are both present.
for marker in [
    "Рабочая фраза · 中文", "Shop-floor English", "请立即隔离受影响和可疑的车辆。",
    "Qǐng quèrèn kùcún", "Confirm ETA, quantity, owner", "请确认负责人",
]:
    assert marker in CHAINS, marker

# Decision-chain judgement does not add a parallel XP farming path.
assert "не создаёт отдельный XP-фарм" in CHAINS
assert "awarded" not in CHAINS
assert "spendable_xp" not in CHAINS

# Assets load before the readiness gate and remain part of all later pilots.
assert "/decision_chains_v622.css" in INDEX
assert "/frontend/decision_chains_v622.js" in INDEX
assert INDEX.index("decision_chains_v622.js") < INDEX.index("frontend/boot.js")
assert "'decision-chains-v622'" in BOOT
version = re.search(r"pilotCandidate: 'v6\.0\.(\d+)'", BOOT)
assert version and int(version.group(1)) >= 22
assert ".v622-chain-panel" in CSS
assert ".v622-chain-locked" in CSS
assert "http://" not in CHAINS and "https://" not in CHAINS

subprocess.run(["node", "--check", str(ROOT / "static/frontend/decision_chains_v622.js")], check=True, cwd=ROOT)
subprocess.run(["node", "--check", str(ROOT / "static/frontend/boot.js")], check=True, cwd=ROOT)

print("PASS: v6.0.22 adds three-step production decision chains with consequences, bilingual shop-floor phrases and no parallel XP path")
