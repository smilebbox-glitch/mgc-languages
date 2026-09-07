from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
ALLOWED_LEVELS = {"A1", "A2", "B1", "B2", "C1", "C2"}

SCHEMAS = {
    "english": {
        "path": DATA_DIR / "english.json",
        "required": {"id", "topic", "category", "subcategory", "term", "ru", "level", "example_target", "example_ru"},
        "semantic": ("term", "ru"),
    },
    "chinese": {
        "path": DATA_DIR / "chinese.json",
        "required": {"id", "category", "subcategory", "zh", "pinyin", "ru", "level", "example_zh", "example_ru"},
        "semantic": ("zh", "ru"),
    },
}


def _nonempty(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _has_han(value: str) -> bool:
    return any("\u4e00" <= ch <= "\u9fff" for ch in value)


def validate_language(language: str) -> dict[str, Any]:
    spec = SCHEMAS[language]
    data = json.loads(spec["path"].read_text(encoding="utf-8"))
    items = data.get("items")
    errors: list[str] = []
    warnings: list[str] = []
    if not isinstance(items, list) or not items:
        return {"language": language, "items": 0, "errors": ["top-level items must be a non-empty list"], "warnings": []}

    seen_ids: set[str] = set()
    semantic_counter: Counter[tuple[str, str]] = Counter()
    categories: Counter[str] = Counter()
    levels: Counter[str] = Counter()

    for index, item in enumerate(items):
        where = f"items[{index}]"
        if not isinstance(item, dict):
            errors.append(f"{where}: item must be an object")
            continue

        missing = sorted(field for field in spec["required"] if not _nonempty(item.get(field)) and field != "id")
        if item.get("id") is None or str(item.get("id")).strip() == "":
            missing.insert(0, "id")
        if missing:
            errors.append(f"{where}: missing/empty required fields: {', '.join(missing)}")

        item_id = str(item.get("id", "")).strip()
        if item_id:
            if item_id in seen_ids:
                errors.append(f"{where}: duplicate id {item_id}")
            seen_ids.add(item_id)

        level = str(item.get("level", "")).strip()
        if level and level not in ALLOWED_LEVELS:
            errors.append(f"{where}: unsupported level {level!r}")
        if level:
            levels[level] += 1

        category = str(item.get("category", "")).strip()
        if category:
            categories[category] += 1

        left_key, right_key = spec["semantic"]
        left = str(item.get(left_key, "")).strip().casefold()
        right = str(item.get(right_key, "")).strip().casefold()
        if left and right:
            semantic_counter[(left, right)] += 1

        if language == "chinese":
            pinyin = str(item.get("pinyin", "")).strip()
            if pinyin and _has_han(pinyin):
                errors.append(f"{where}: pinyin contains Han characters")
            if _nonempty(item.get("example_zh")) and not _nonempty(item.get("example_pinyin")):
                warnings.append(f"{where}: example_zh has no example_pinyin")
        else:
            term = str(item.get("term", "")).strip()
            if term and _has_han(term):
                warnings.append(f"{where}: English term contains Han characters")

    duplicates = [key for key, count in semantic_counter.items() if count > 1]
    if duplicates:
        warnings.append(f"{len(duplicates)} repeated semantic term/translation pairs; review intentional duplicates")

    if len(categories) < 3:
        warnings.append(f"only {len(categories)} categories detected")
    if len(levels) < 3:
        warnings.append(f"only {len(levels)} proficiency levels detected")

    return {
        "language": language,
        "items": len(items),
        "unique_ids": len(seen_ids),
        "categories": dict(categories.most_common()),
        "levels": dict(sorted(levels.items())),
        "errors": errors,
        "warnings": warnings[:100],
    }


def audit() -> dict[str, Any]:
    reports = [validate_language("english"), validate_language("chinese")]
    errors = [f"{r['language']}: {message}" for r in reports for message in r["errors"]]
    warnings = [f"{r['language']}: {message}" for r in reports for message in r["warnings"]]
    return {"ok": not errors, "errors": errors, "warnings": warnings, "languages": reports}


def main() -> int:
    report = audit()
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if report["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
