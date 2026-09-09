"""Runtime activation for the v6.0.18 bilingual automotive corpus.

The generated JSON files are committed build artifacts. This module keeps the
large legacy runtime untouched while making the expanded Chinese/English
corpora authoritative for every endpoint that reads ``legacy_app.TERMS``.

v6.0.30 additionally installs a presentation-safe learning projection:
- a visible term appears in one CEFR level only;
- duplicate visible terms are collapsed for learning endpoints without changing
  the frozen 2029/2029 raw release corpus or term IDs;
- Chinese quiz choices expose pinyin when the visible answer itself is Chinese.
"""
from __future__ import annotations

from collections import Counter, defaultdict
import re
import unicodedata
from typing import Any


_RELEASE = "6.0.18"
_LEVEL_ORDER = {"A1": 0, "A2": 1, "B1": 2, "B2": 3, "C1": 4}
_SHOP_TOPIC = {
    "Окраска": "Окраска",
    "Логистика": "Логистика JIT/JIS",
    "Кузов и компоненты": "Кузов и компоненты",
}
_BODY_TOPIC = {
    "id": "body-components",
    "label": "Кузов и компоненты",
    "description": "Кузовные детали, наружные и внутренние компоненты, крепёж, остекление, уплотнения и монтаж.",
}


def _with_shop_topic(item: dict[str, Any]) -> dict[str, Any]:
    category = str(item.get("category", "")).strip()
    if category in _SHOP_TOPIC:
        item["topic"] = _SHOP_TOPIC[category]
    return item


def _assert_unique_ids(language: str, rows: list[dict[str, Any]]) -> None:
    counts = Counter(str(row.get("id", "")) for row in rows)
    duplicates = sorted(key for key, value in counts.items() if key and value > 1)
    if duplicates:
        raise RuntimeError(f"v6.0.18 duplicate {language} term ids: {duplicates[:10]}")


def _visible_term_key(language: str, value: Any) -> str:
    """Normalize only the visible lemma/phrase, not its translation.

    The user-facing contract is intentionally strict: the same visible term
    must not reappear in A1 and again in B1. NFKC handles full-width variants;
    whitespace/case normalization catches accidental formatting duplicates.
    """
    text = unicodedata.normalize("NFKC", str(value or "")).strip()
    text = re.sub(r"\s+", " ", text)
    return text if language == "chinese" else text.casefold()


def _row_richness(row: dict[str, Any]) -> tuple[int, int, int]:
    fields = ("pronunciation", "reading", "example", "example_pronunciation", "example_translation")
    populated = sum(1 for field in fields if str(row.get(field, "")).strip())
    text_size = sum(len(str(row.get(field, ""))) for field in fields)
    return populated, text_size, -len(str(row.get("id", "")))


def canonical_learning_rows(language: str, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return one deterministic learning row per visible term.

    If a term exists in several levels, it is assigned to the earliest level in
    which the corpus already considers it teachable (A1 → C1). This keeps basic
    vocabulary basic and prevents the same visible word from being relearned at
    higher levels. Among duplicates in that canonical level the richest content
    row wins, preserving pronunciation/example quality.

    The raw ``legacy.TERMS`` list is not modified, so release parity, stable IDs
    and archived 2029-term contracts remain intact.
    """
    grouped: dict[str, list[tuple[int, dict[str, Any]]]] = defaultdict(list)
    passthrough: list[tuple[int, dict[str, Any]]] = []
    for index, row in enumerate(rows):
        key = _visible_term_key(language, row.get("term"))
        if not key:
            passthrough.append((index, dict(row)))
            continue
        grouped[key].append((index, row))

    selected: list[tuple[int, dict[str, Any]]] = list(passthrough)
    for entries in grouped.values():
        levels = [str(row.get("level", "")) for _, row in entries if str(row.get("level", "")) in _LEVEL_ORDER]
        canonical_level = min(levels, key=lambda level: _LEVEL_ORDER[level]) if levels else str(entries[0][1].get("level", "A1"))
        same_level = [(index, row) for index, row in entries if str(row.get("level", "")) == canonical_level]
        candidates = same_level or entries
        winner_index, winner = max(candidates, key=lambda pair: (_row_richness(pair[1]), -pair[0]))
        visible = dict(winner)
        visible["level"] = canonical_level
        selected.append((min(index for index, _ in entries), visible))

    selected.sort(key=lambda pair: pair[0])
    return [row for _, row in selected]


def _question_option_value(row: dict[str, Any], level: str) -> str:
    if level == "A1":
        return str(row.get("translation", ""))
    if level == "A2":
        return str(row.get("term", ""))
    if level == "B1":
        return str(row.get("example_translation") or row.get("translation", ""))
    return str(row.get("example") or row.get("term", ""))


def _question_option_pinyin(row: dict[str, Any], level: str) -> str:
    # A1/B1 answers are Russian meanings, so pinyin would be noise. A2 and
    # B2/C1 answers are Chinese and receive term/example pronunciation.
    if level == "A2":
        return str(row.get("pronunciation", ""))
    if level in {"B2", "C1"}:
        return str(row.get("example_pronunciation") or row.get("pronunciation", ""))
    return ""


def _install_learning_projection(legacy: Any) -> None:
    if getattr(legacy, "_V630_LEARNING_PROJECTION_APPLIED", False):
        return

    original_terms_for = legacy.terms_for
    original_make_question = legacy.make_question

    def terms_for_unique(language: str, db: Any) -> list[dict[str, Any]]:
        return canonical_learning_rows(language, list(original_terms_for(language, db)))

    def make_question_with_pinyin(
        item: dict[str, Any], pool: list[dict[str, Any]], rng: Any, language: str
    ) -> dict[str, Any]:
        question = original_make_question(item, pool, rng, language)
        if language != "chinese":
            return question
        level = str(item.get("level", "A1"))
        candidates = [item, *pool]
        option_pinyin: list[str] = []
        for option in question.get("options", []):
            matched = next(
                (row for row in candidates if _question_option_value(row, level) == str(option)),
                None,
            )
            option_pinyin.append(_question_option_pinyin(matched or {}, level))
        question["option_pronunciations"] = option_pinyin
        return question

    legacy.terms_for = terms_for_unique
    legacy.make_question = make_question_with_pinyin
    legacy._V630_LEARNING_PROJECTION_APPLIED = True


def apply_v618_content(legacy: Any) -> dict[str, Any]:
    """Replace the in-memory term catalog with the generated parity corpus.

    Safe to call repeatedly. The function validates bilingual parity and the
    requested 80-term additions for Paint, Logistics and Body/Components.
    """
    if getattr(legacy, "_V618_CONTENT_PATCH_APPLIED", False):
        _install_learning_projection(legacy)
        return dict(getattr(legacy, "V618_CONTENT_STATUS", {}))

    shop = legacy.load_json("shop_expansion_v618.json")
    english_parallel = legacy.load_json("english_parallel_v618.json")
    manifest = legacy.load_json("v618_content_manifest.json")

    chinese = [legacy.normalize_chinese(row) for row in legacy.CHINESE_RAW["items"]]
    chinese.extend(_with_shop_topic(legacy.normalize_chinese(row)) for row in shop["chinese"])
    chinese.extend(legacy.normalize_extra(row, "chinese") for row in legacy.EXPERIENCE["extra_terms"])

    english = [legacy.normalize_english(row) for row in legacy.ENGLISH_RAW["items"]]
    english.extend(legacy.normalize_english(row) for row in english_parallel["items"])
    english.extend(_with_shop_topic(legacy.normalize_english(row)) for row in shop["english"])
    english.extend(legacy.normalize_extra(row, "english") for row in legacy.EXPERIENCE["extra_terms"])

    _assert_unique_ids("Chinese", chinese)
    _assert_unique_ids("English", english)

    if len(chinese) != len(english):
        raise RuntimeError(f"v6.0.18 bilingual parity failed: Chinese={len(chinese)}, English={len(english)}")

    expected_shop = {"Окраска": 80, "Логистика": 80, "Кузов и компоненты": 80}
    actual_shop = Counter(str(row.get("category", "")) for row in shop["chinese"])
    for category, expected in expected_shop.items():
        if actual_shop.get(category, 0) != expected:
            raise RuntimeError(
                f"v6.0.18 {category} expansion mismatch: expected {expected}, got {actual_shop.get(category, 0)}"
            )

    if not any(str(row.get("label", "")) == _BODY_TOPIC["label"] for row in legacy.TOPIC_ROWS):
        legacy.TOPIC_ROWS.append(dict(_BODY_TOPIC))

    legacy.TERMS = {"chinese": chinese, "english": english}
    visible_chinese = canonical_learning_rows("chinese", chinese)
    visible_english = canonical_learning_rows("english", english)
    legacy.V618_CONTENT_STATUS = {
        "release": _RELEASE,
        "terms_per_language": len(chinese),
        "visible_unique_chinese": len(visible_chinese),
        "visible_unique_english": len(visible_english),
        "hidden_duplicate_chinese": len(chinese) - len(visible_chinese),
        "hidden_duplicate_english": len(english) - len(visible_english),
        "base_chinese": int(manifest.get("base_chinese", 0)),
        "base_english": int(manifest.get("base_english", 0)),
        "generated_english_parallel": int(manifest.get("generated_english_parallel", 0)),
        "shop_expansion_per_language": int(manifest.get("shop_expansion_per_language", 0)),
        "shop_additions": dict(expected_shop),
        "runtime_extra_terms_per_language": len(legacy.EXPERIENCE["extra_terms"]),
        "parity": True,
        "one_visible_term_one_level": True,
    }
    legacy._V618_CONTENT_PATCH_APPLIED = True
    _install_learning_projection(legacy)
    return dict(legacy.V618_CONTENT_STATUS)


__all__ = ["apply_v618_content", "canonical_learning_rows"]
