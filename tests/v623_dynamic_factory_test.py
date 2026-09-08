from __future__ import annotations

import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DYNAMIC = (ROOT / "static/frontend/dynamic_factory_v623.js").read_text(encoding="utf-8")
CSS = (ROOT / "static/dynamic_factory_v623.css").read_text(encoding="utf-8")
INDEX = (ROOT / "static/index.html").read_text(encoding="utf-8")
BOOT = (ROOT / "static/frontend/boot.js").read_text(encoding="utf-8")

# v6.0.23 must branch from the existing v6.0.22 decision UI, not create another backend game engine.
assert ".v622-chain-panel" in DYNAMIC
assert "data-v622-option" in DYNAMIC
assert "selected.classList.contains(\"correct\")" in DYNAMIC
assert "consumeChoice(panel, model)" in DYNAMIC
assert "applyDecision(model, step, index, correct)" in DYNAMIC
assert "/api/games/" not in DYNAMIC

# All eight production families carry live state into the next decision.
for family in ["line_stop", "quality", "logistics", "welding", "paint", "safety", "engineering", "supplier"]:
    assert f"{family}: {{" in DYNAMIC, family
for marker in [
    "Авто в зоне риска", "Авто в suspect window", "Запас до run-out", "Кузова в риске",
    "Активная экспозиция", "Конфигурационный риск", "Ясность запроса",
]:
    assert marker in DYNAMIC, marker

# Decisions create concrete downstream consequences instead of only right/wrong feedback.
for marker in [
    "ещё 4 автомобиля вошли в suspect window",
    "ещё 6 автомобилей вошли в suspect window",
    "Ожидание плановой поставки съело 25 минут",
    "Неутверждённая замена создаёт одновременно логистический, BOM и quality risk",
    "BOM изменён без effective point",
    "Состояние после предыдущего решения",
    "Последствия предыдущих решений",
]:
    assert marker in DYNAMIC, marker
assert "model.processed[token]" in DYNAMIC
assert "model.history.push" in DYNAMIC
assert "branchContext(panel, model)" in DYNAMIC

# Supplier dialogue changes based on the quality of the user's escalation and remains bilingual.
for marker in [
    "Поставщик запросил уточнение",
    "Supplier containment подтверждён",
    "请提供零件号、批次和具体缺陷信息",
    "Qǐng tígōng língjiànhào",
    "Please provide the part number, lot, and specific defect details",
    "已确认负责人和时间节点",
]:
    assert marker in DYNAMIC, marker

# Dynamic state is visual and local to the learning flow; it must not create a second XP path.
for marker in ["LIVE FACTORY STATE · v6.0.23", "v623-metrics", "v623-event", "v623-branch-context"]:
    assert marker in DYNAMIC or marker in CSS, marker
assert "не начисляет дополнительный XP" in DYNAMIC
assert "spendable_xp" not in DYNAMIC
assert "awarded_xp" not in DYNAMIC

# Assets load before boot and the readiness contract recognizes the current pilot.
assert "/dynamic_factory_v623.css" in INDEX
assert "/frontend/dynamic_factory_v623.js" in INDEX
assert INDEX.index("dynamic_factory_v623.js") < INDEX.index("frontend/boot.js")
assert "'dynamic-factory-v623'" in BOOT
assert "pilotCandidate: 'v6.0.23'" in BOOT
assert "http://" not in DYNAMIC and "https://" not in DYNAMIC

subprocess.run(["node", "--check", str(ROOT / "static/frontend/dynamic_factory_v623.js")], check=True, cwd=ROOT)
subprocess.run(["node", "--check", str(ROOT / "static/frontend/boot.js")], check=True, cwd=ROOT)

print("PASS: v6.0.23 carries production consequences into later decisions, live factory state and supplier dialogue without adding an XP path")
