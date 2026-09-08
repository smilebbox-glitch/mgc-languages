from __future__ import annotations

import json
import os
import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# Keep this regression test independent from a local developer database.
os.environ.setdefault("AUTO_CREATE_SCHEMA", "false")
os.environ.setdefault("MGC_ADMIN_USERNAME", "")
os.environ.setdefault("MGC_ADMIN_PASSWORD", "")

import app as runtime  # noqa: E402
from mgc.services.practice_games import GAME_TYPES, MAX_GAME_ANSWERS  # noqa: E402

MANIFEST = json.loads((ROOT / "data/v618_content_manifest.json").read_text(encoding="utf-8"))
SHOP = json.loads((ROOT / "data/shop_expansion_v618.json").read_text(encoding="utf-8"))
PARALLEL = json.loads((ROOT / "data/english_parallel_v618.json").read_text(encoding="utf-8"))
INDEX = (ROOT / "static/index.html").read_text(encoding="utf-8")
GAME_LAB = (ROOT / "static/frontend/game_lab_v618.js").read_text(encoding="utf-8")
NAV = (ROOT / "static/frontend/navigation.js").read_text(encoding="utf-8")
PRACTICE = (ROOT / "mgc/services/practice_games.py").read_text(encoding="utf-8")

# Generated source corpus: Chinese and English must have exact parity before
# the shared experience vocabulary is added at runtime.
assert MANIFEST["release"] == "6.0.18"
assert MANIFEST["base_chinese"] == 1735
assert MANIFEST["base_english"] == 256
assert MANIFEST["generated_english_parallel"] == 1479
assert MANIFEST["shop_expansion_per_language"] == 240
assert MANIFEST["source_terms_per_language"] == 1975
assert MANIFEST["shop_additions"] == {
    "Кузов и компоненты": 80,
    "Логистика": 80,
    "Окраска": 80,
}
assert len(PARALLEL["items"]) == 1479

for language in ("chinese", "english"):
    counts = Counter(row["category"] for row in SHOP[language])
    assert counts["Окраска"] == 80
    assert counts["Логистика"] == 80
    assert counts["Кузов и компоненты"] == 80

# Runtime activation is the important contract: users must actually receive
# the generated corpora rather than merely having JSON artifacts in the repo.
assert runtime.V618_CONTENT_STATUS["release"] == "6.0.18"
assert runtime.V618_CONTENT_STATUS["parity"] is True
assert runtime.V618_CONTENT_STATUS["shop_expansion_per_language"] == 240
assert len(runtime.TERMS["chinese"]) == len(runtime.TERMS["english"])
assert len(runtime.TERMS["chinese"]) == 1975 + len(runtime.EXPERIENCE["extra_terms"])

chinese_shop = [row for row in runtime.TERMS["chinese"] if str(row["id"]).startswith("zh-v618-")]
english_shop = [row for row in runtime.TERMS["english"] if str(row["id"]).startswith("en-v618-")]
assert len(chinese_shop) == 240
assert len(english_shop) == 240
assert sum(1 for row in runtime.TERMS["english"] if str(row["id"]).startswith("en-parity-")) == 1479

for category, topic in {
    "Окраска": "Окраска",
    "Логистика": "Логистика JIT/JIS",
    "Кузов и компоненты": "Кузов и компоненты",
}.items():
    zh_rows = [row for row in chinese_shop if row["category"] == category]
    en_rows = [row for row in english_shop if row["category"] == category]
    assert len(zh_rows) == len(en_rows) == 80
    assert all(row["topic"] == topic for row in zh_rows)
    assert all(row["topic"] == topic for row in en_rows)

# Game lab: 20 genuinely named modes, five-answer server cap, visual hotspot
# mechanic, and frontend routing through the new module.
assert len(GAME_TYPES) == 20
assert len(set(GAME_TYPES)) == 20
assert MAX_GAME_ANSWERS == 5
for required in (
    "hotspot", "defect_detective", "logistics_route", "kanban", "bom_builder",
    "spec_check", "memory_pairs", "dialogue_choice", "shift_incident",
):
    assert required in GAME_TYPES

catalog_ids = re.findall(r"\{id:'([^']+)'", GAME_LAB)
assert len(catalog_ids) == 20, catalog_ids
assert len(set(catalog_ids)) == 20
assert set(catalog_ids) == set(GAME_TYPES)
assert "Car Part Hotspot" in GAME_LAB
assert "car-hotspot-stage" in GAME_LAB
assert "data-hotspot-zone" in GAME_LAB
assert "MGC AUTOMOTIVE ARCADE · 20 ИГР" in GAME_LAB
assert "/frontend/game_lab_v618.js" in INDEX
assert INDEX.index("/frontend/game_lab_v618.js") < INDEX.index("/frontend/practice_games.js")
assert "frontend.has('game-lab-v618')" in NAV
assert "GAME_TYPES" in PRACTICE

print(
    "PASS: v6.0.18 has exact Chinese/English vocabulary parity, "
    "80 new terms for each requested shop in both languages, and 20 game modes"
)
