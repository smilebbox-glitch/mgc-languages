from __future__ import annotations

import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SHIFT = (ROOT / "static/frontend/shift_simulation_v624.js").read_text(encoding="utf-8")
CSS = (ROOT / "static/shift_simulation_v624.css").read_text(encoding="utf-8")
INDEX = (ROOT / "static/index.html").read_text(encoding="utf-8")
BOOT = (ROOT / "static/frontend/boot.js").read_text(encoding="utf-8")

# v6.0.24 is a dedicated client-side shift mode over the existing game catalog.
assert 'frontend.register("shift-simulation-v624"' in SHIFT
assert 'String(current().view || "") !== "games"' in SHIFT
assert ".v623-catalog-panel" in SHIFT
assert "Начать виртуальную смену" in SHIFT
assert "/api/games/" not in SHIFT

# Five linked shift episodes must exist with priority -> action -> communication -> consequence -> review.
for marker in [
    'const times = ["08:00", "09:35", "11:20", "14:05", "16:25"]',
    'run.phase === "priority"',
    'run.phase === "action"',
    'run.phase === "message"',
    'run.phase === "feedback"',
    "Shift Review",
    "ignoredConsequences(run.selected)",
]:
    assert marker in SHIFT, marker

# Prioritization is real: unhandled incidents degrade live production state.
for marker in [
    "delayImpact",
    "bestPriority(run.queue)",
    "run.priorityPoints",
    "run.history.push({type:\"delay\"",
    "Невыбранные проблемы не исчезнут",
]:
    assert marker in SHIFT, marker

# Branching across episodes uses previous actions and current factory state.
for marker in [
    "run.flags.paintContained ? \"weld_drift\" : \"paint_spread\"",
    "run.flags.supplierExpedite ? \"supplier_traceability\" : \"material_runout\"",
    "run.flags.torqueProtected ? \"first_off\" : \"quality_gate_hold\"",
    "run.metrics.material < 58 || run.flags.unapprovedSubstitution",
    "run.metrics.line < 65 || run.metrics.load > 62",
]:
    assert marker in SHIFT, marker

# The simulation must cover production, quality, logistics, engineering and Chinese supplier work.
for incident in [
    "paint_repeat", "supplier_delay", "torque_alarm", "paint_spread", "material_runout",
    "quality_gate_hold", "weld_drift", "engineering_substitution", "supplier_traceability",
    "line_stop", "sequencing", "china_escalation", "first_off", "handover",
]:
    assert f'{incident}: {{' in SHIFT, incident

for marker in [
    "Стабильность линии", "Защита качества", "Material runway", "Supplier control", "Нагрузка команды",
    "R&D / закупки / логистика", "Китай / поставщик", "Смена / руководство",
]:
    assert marker in SHIFT, marker

# Every handled episode includes a bilingual communication decision and pinyin support.
for marker in [
    "03 · КОММУНИКАЦИЯ",
    "профессиональную реплику на путунхуа",
    "message.zh", "message.pinyin", "message.en", "message.ru",
    "请确认现有库存", "Qǐng quèrèn xiànyǒu kùcún",
    "Confirm one accountable owner",
]:
    assert marker in SHIFT, marker

# End-of-shift review scores operations, prioritization, judgement and language separately.
for marker in [
    "Production control", "Prioritization", "Production judgement", "Language",
    "Главная точка роста", "Языковой разбор", "weakestMetric()", "scorecard()",
]:
    assert marker in SHIFT, marker

# Shift Simulation is explicitly not another XP farm or backend scoring path.
assert "не начисляет отдельный XP" in SHIFT
assert "backend-лимит пяти ответов" in SHIFT
for forbidden in ["awarded_xp", "spendable_xp", "/api/games/"]:
    assert forbidden not in SHIFT, forbidden

# Assets remain loaded before boot. Historical regressions must not pin the active release forever.
assert "/shift_simulation_v624.css" in INDEX
assert "/frontend/shift_simulation_v624.js" in INDEX
assert INDEX.index("shift_simulation_v624.js") < INDEX.index("frontend/boot.js")
assert "'shift-simulation-v624'" in BOOT
assert "pilotCandidate: 'v6.0." in BOOT
assert ".v624-launcher" in CSS
assert ".v624-sim-shell" in CSS
assert ".v624-summary" in CSS
assert "http://" not in SHIFT and "https://" not in SHIFT

subprocess.run(["node", "--check", str(ROOT / "static/frontend/shift_simulation_v624.js")], check=True, cwd=ROOT)
subprocess.run(["node", "--check", str(ROOT / "static/frontend/boot.js")], check=True, cwd=ROOT)

print("PASS: v6.0.24 adds a five-episode linked shift simulation with prioritization, production consequences, bilingual communication and end-of-shift review")
