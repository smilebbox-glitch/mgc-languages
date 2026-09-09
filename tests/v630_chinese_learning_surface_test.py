from collections import Counter
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from mgc.content_v618 import canonical_learning_rows


def test_same_visible_term_is_kept_once_and_at_lowest_existing_level():
    rows = [
        {"id": "a", "term": "扭矩", "level": "B1", "pronunciation": "niǔjǔ", "translation": "крутящий момент"},
        {"id": "b", "term": "扭矩", "level": "A1", "pronunciation": "niǔjǔ", "translation": "крутящий момент", "example": "请确认扭矩"},
        {"id": "c", "term": "公差", "level": "B1", "pronunciation": "gōngchā", "translation": "допуск"},
    ]
    visible = canonical_learning_rows("chinese", rows)
    assert [row["term"] for row in visible] == ["扭矩", "公差"]
    assert next(row for row in visible if row["term"] == "扭矩")["level"] == "A1"


def test_english_duplicate_matching_is_case_and_whitespace_insensitive():
    rows = [
        {"id": "a", "term": "Quality Gate", "level": "B2", "translation": "контрольная точка качества"},
        {"id": "b", "term": "  quality   gate ", "level": "A2", "translation": "контрольная точка качества"},
    ]
    visible = canonical_learning_rows("english", rows)
    assert len(visible) == 1
    assert visible[0]["level"] == "A2"


def test_real_release_corpus_has_no_visible_cross_level_duplicates_and_keeps_exam_capacity():
    import app
    for language in ("chinese", "english"):
        raw = list(app.TERMS[language])
        assert len(raw) == 2029
        visible = canonical_learning_rows(language, raw)
        terms = [str(row.get("term", "")).strip().casefold() if language == "english" else str(row.get("term", "")).strip() for row in visible]
        assert len(terms) == len(set(terms))
        counts = Counter(str(row.get("level", "")) for row in visible)
        for level in ("A1", "A2", "B1", "B2", "C1"):
            assert counts[level] >= 10, (language, level, counts[level])


def test_chinese_learning_surface_is_loaded_after_game_localization():
    index = (ROOT / "static" / "index.html").read_text(encoding="utf-8")
    game = '/frontend/game_chinese_localization_v630.js'
    surface = '/frontend/chinese_learning_surface_v630.js'
    assert game in index and surface in index
    assert index.index(game) < index.index(surface)


def test_chinese_mode_keeps_ui_russian_and_only_learning_content_gets_pinyin():
    source = (ROOT / "static" / "frontend" / "chinese_learning_surface_v630.js").read_text(encoding="utf-8")
    assert "data-learning-ui-language', 'ru'" in source
    assert "data-learning-content-language" in source
    assert "option_pronunciations" in source
    assert "v630-option-pinyin" in source
    assert "v630-game-learning-pinyin" in source
    # Regression: these UI labels must NOT be translated into Chinese anymore.
    for forbidden_ui_translation in ("下一题", "学习计划", "沟通训练", "XP 学习积分", "游戏能力 · 技能图谱"):
        assert forbidden_ui_translation not in source


def test_content_projection_enriches_chinese_question_options_without_raw_corpus_mutation():
    source = (ROOT / "mgc" / "content_v618.py").read_text(encoding="utf-8")
    assert 'question["option_pronunciations"]' in source
    assert 'legacy.terms_for = terms_for_unique' in source
    assert 'legacy.TERMS = {"chinese": chinese, "english": english}' in source
    assert 'one_visible_term_one_level' in source
