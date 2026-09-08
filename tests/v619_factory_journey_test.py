from __future__ import annotations

import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INDEX = (ROOT / "static/index.html").read_text(encoding="utf-8")
BOOT = (ROOT / "static/frontend/boot.js").read_text(encoding="utf-8")
JOURNEY = (ROOT / "static/frontend/factory_journey_v619.js").read_text(encoding="utf-8")
CSS = (ROOT / "static/factory_journey_v619.css").read_text(encoding="utf-8")
GAME_LAB = (ROOT / "static/frontend/game_lab_v618.js").read_text(encoding="utf-8")

assert "frontend.register('factory-journey-v619'" in JOURNEY
assert "FACTORY JOURNEY · v6.0.19" in JOURNEY
assert "Пройдите автомобиль через весь завод" in JOURNEY
assert "Следующая станция открывается" in JOURNEY
assert "journeySignature" in JOURNEY
assert "dataset.journeySignature" in JOURNEY
assert "data-factory-continue" in JOURNEY
assert "data-start-v618-game" in JOURNEY

station_ids = re.findall(r"\{id:'([^']+)', title:'[^']+', subtitle:'[^']+', game:'([^']+)'", JOURNEY)
assert len(station_ids) == 6, station_ids
assert len({station for station, _ in station_ids}) == 6
assert [station for station, _ in station_ids] == ["press", "body", "paint", "assembly", "quality", "logistics"]
assert [game for _, game in station_ids] == [
    "shop_route", "hotspot", "defect_detective", "assembly_order", "quality_gate", "logistics_route"
]

catalog_ids = set(re.findall(r"\{id:'([^']+)'", GAME_LAB))
for _, game in station_ids:
    assert game in catalog_ids, game

assert "/factory_journey_v619.css" in INDEX
assert "/frontend/factory_journey_v619.js" in INDEX
assert INDEX.index("/frontend/game_engagement_v618.js") < INDEX.index("/frontend/factory_journey_v619.js")
assert INDEX.index("/frontend/factory_journey_v619.js") < INDEX.index("/frontend/practice_games.js")
assert "'factory-journey-v619'" in BOOT
assert "pilotCandidate: 'v6.0.19'" in BOOT

for required in (
    ".factory-journey-v619", ".factory-conveyor", ".factory-journey-station",
    ".factory-journey-meter", ".factory-journey-footer", "prefers-reduced-motion",
):
    assert required in CSS, required

subprocess.run(["node", "--check", str(ROOT / "static/frontend/factory_journey_v619.js")], check=True, cwd=ROOT)

print("PASS: v6.0.19 Factory Journey adds a six-station automotive route over the 20-game arcade")
