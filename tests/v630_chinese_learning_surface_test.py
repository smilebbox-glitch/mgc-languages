from pathlib import Path

from mgc.content_v618 import canonical_learning_rows


ROOT = Path(__file__).resolve().parents[1]


def test_same_visible_term_is_kept_once_and_at_lowest_existing_level():
    rows = [
        {"id": "a", "term": "扭矩", "level": "B1", "pronunciation": "niǔjǔ", "translation": "крутящий момент"},
        {"id": "b", "term": "扭矩", "level": "A1", "pronunciation": "niǔjǔ", "translation": "крутящий момент", "example": "请确认扭矩"},
        {"id": "c", "term": "公差", "level": "B1", "pronunciation": "gōngchā", "translation": "допуск"},
    ]
    visible = canonical_learning_rows("chinese", rows)
    assert [row["term"] for row in visible] == ["扭矩", "公差"]
    torque = next(row for row in visible if row["term"] == "扭矩")
    assert torque["level"] == "A1"


def test_english_duplicate_matching_is_case_and_whitespace_insensitive():
    rows = [
        {"id": "a", "term": "Quality Gate", "level": "B2", "translation": "контрольная точка качества"},
        {"id": "b", "term": "  quality   gate ", "level": "A2", "translation": "контрольная точка качества"},
    ]
    visible = canonical_learning_rows("english", rows)
    assert len(visible) == 1
    assert visible[0]["level"] == "A2"


def test_chinese_learning_surface_is_loaded_after_game_localization():
    index = (ROOT / "static" / "index.html").read_text(encoding="utf-8")
    game = '/frontend/game_chinese_localization_v630.js'
    surface = '/frontend/chinese_learning_surface_v630.js'
    assert game in index
    assert surface in index
    assert index.index(game) < index.index(surface)


def test_chinese_learning_surface_covers_requested_views_and_pinyin():
    source = (ROOT / "static" / "frontend" / "chinese_learning_surface_v630.js").read_text(encoding="utf-8")
    for view in ("games", "xp", "quiz", "roleplay", "course30"):
        assert f"'{view}'" in source
    assert "option_pronunciations" in source
    assert "v630-option-pinyin" in source
    assert "游戏能力 · 技能图谱" in source
    assert "XP 学习积分" in source
    assert "沟通训练" in source
    assert "学习计划" in source


def test_content_projection_enriches_chinese_question_options_without_raw_corpus_mutation():
    source = (ROOT / "mgc" / "content_v618.py").read_text(encoding="utf-8")
    assert 'question["option_pronunciations"]' in source
    assert 'legacy.terms_for = terms_for_unique' in source
    assert 'legacy.TERMS = {"chinese": chinese, "english": english}' in source
    assert 'one_visible_term_one_level' in source
