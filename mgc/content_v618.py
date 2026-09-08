"""Runtime activation for the v6.0.18 bilingual automotive corpus.

The generated JSON files are committed build artifacts.  This module keeps the
large legacy runtime untouched while making the expanded Chinese/English
corpora authoritative for every endpoint that reads ``legacy_app.TERMS``.
"""
from __future__ import annotations

from collections import Counter
from typing import Any


_RELEASE = "6.0.18"
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


def apply_v618_content(legacy: Any) -> dict[str, Any]:
    """Replace the in-memory term catalog with the generated parity corpus.

    Safe to call repeatedly.  The function validates bilingual parity and the
    requested 80-term additions for Paint, Logistics and Body/Components.
    """
    if getattr(legacy, "_V618_CONTENT_PATCH_APPLIED", False):
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
    legacy.V618_CONTENT_STATUS = {
        "release": _RELEASE,
        "terms_per_language": len(chinese),
        "base_chinese": int(manifest.get("base_chinese", 0)),
        "base_english": int(manifest.get("base_english", 0)),
        "generated_english_parallel": int(manifest.get("generated_english_parallel", 0)),
        "shop_expansion_per_language": int(manifest.get("shop_expansion_per_language", 0)),
        "shop_additions": dict(expected_shop),
        "runtime_extra_terms_per_language": len(legacy.EXPERIENCE["extra_terms"]),
        "parity": True,
    }
    legacy._V618_CONTENT_PATCH_APPLIED = True
    return dict(legacy.V618_CONTENT_STATUS)


__all__ = ["apply_v618_content"]
