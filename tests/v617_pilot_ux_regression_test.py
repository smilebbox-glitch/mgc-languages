from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INDEX = (ROOT / "static/index.html").read_text(encoding="utf-8")
HOME = (ROOT / "static/frontend/pilot_home.js").read_text(encoding="utf-8")
UX = (ROOT / "static/frontend/pilot_ux_hardening.js").read_text(encoding="utf-8")
OVERRIDES = (ROOT / "static/pilot_overrides.css").read_text(encoding="utf-8")
PRACTICE = (ROOT / "mgc/services/practice_games.py").read_text(encoding="utf-8")
README = (ROOT / "README.md").read_text(encoding="utf-8")

# The release-specific UX layer must be loaded before boot so it can protect the pilot UI.
assert "/frontend/pilot_ux_hardening.js" in INDEX
assert INDEX.index("/frontend/pilot_ux_hardening.js") < INDEX.index("/frontend/boot.js")
assert "/pilot_overrides.css" in INDEX

# Decorative copy removed after pilot review must stay hidden from the rendered service.
for selector in (
    ".pilot-next-head blockquote",
    ".pilot-hero-quote",
    ".pilot-hero-message",
    ".pilot-quote-card",
):
    assert selector in OVERRIDES, selector
assert "display:none!important" in OVERRIDES
assert "Большее цели" not in HOME

# Chinese learning questions must have a safe Pinyin fallback for core automotive terms.
expected_pinyin = {
    "整车装配": "zhěng chē zhuāng pèi",
    "总装": "zǒng zhuāng",
    "焊接": "hàn jiē",
    "涂装": "tú zhuāng",
    "冲压": "chōng yā",
    "质量": "zhì liàng",
    "物流": "wù liú",
    "发动机": "fā dòng jī",
    "变速箱": "biàn sù xiāng",
    "底盘": "dǐ pán",
    "车身": "chē shēn",
}
for hanzi, pinyin in expected_pinyin.items():
    assert f"'{hanzi}': '{pinyin}'" in UX, hanzi
assert ".pilot-pinyin-fallback" in OVERRIDES

# Browser TTS should prefer natural/neural voices and penalize known robotic fallbacks.
for token in (
    "natural|neural|online|premium",
    "xiaoxiao",
    "putonghua",
    "samantha",
    "speechSynthesis",
):
    assert token in UX, token
assert "espeak|festival|compact|robot" in UX
assert "utterance.lang = language === 'chinese' ? 'zh-CN' : 'en-US'" in UX

# XP-farming exercise is intentionally bounded to five answers at backend game generation.
assert re.search(r"^MAX_GAME_ANSWERS\s*=\s*5$", PRACTICE, re.MULTILINE)
assert PRACTICE.count("min(MAX_GAME_ANSWERS, len(") >= 2
assert "selected = rng.sample(pool, min(8, len(pool)))" not in PRACTICE
assert "min(6, len(phrase_pool))" not in PRACTICE

# Professional topic cards use local/offline automotive illustrations.
topic_art = (
    "assembly.svg",
    "welding.svg",
    "paint.svg",
    "stamping.svg",
    "quality.svg",
    "logistics.svg",
)
for name in topic_art:
    path = ROOT / "static" / "pilot" / "topics" / name
    assert path.exists(), path
    ET.parse(path)
    assert f"/pilot/topics/{name}" in OVERRIDES

# Removed hero decorations must not reappear in either language artwork.
for name in ("hero-chinese.svg", "hero-english.svg"):
    art = (ROOT / "static" / "pilot" / name).read_text(encoding="utf-8")
    assert 'x="890"' not in art
    assert 'x="894"' not in art

# README must describe the current pilot behavior, not the superseded quote-card state.
for token in (
    "UX hardening",
    "5 ответами",
    "Natural / Neural",
    "pilot_ux_hardening.js",
    "v617_pilot_ux_regression_test.py",
):
    assert token in README, token
assert "В актуальном пилоте текст карточки зафиксирован" not in README

print("PASS: v6.0.17 user-review UX regressions are covered and current documentation matches the pilot")
