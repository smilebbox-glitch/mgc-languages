#!/usr/bin/env python3
from __future__ import annotations

import csv
import json
import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
SOURCE = DATA / "shop_expansion_v618_source.psv"
SHOP_OUT = DATA / "shop_expansion_v618.json"
PARITY_OUT = DATA / "english_parallel_v618.json"
MANIFEST_OUT = DATA / "v618_content_manifest.json"
ALLOWED_LEVELS = {"A1", "A2", "B1", "B2", "C1"}
CYRILLIC = re.compile(r"[А-Яа-яЁё]")


def load_json(name: str):
    return json.loads((DATA / name).read_text(encoding="utf-8"))


def install_translation_model() -> None:
    import argostranslate.package as package
    import argostranslate.translate as translate

    installed = translate.get_installed_languages()
    if any(lang.code == "ru" for lang in installed) and any(lang.code == "en" for lang in installed):
        try:
            translate.translate("проверка", "ru", "en")
            return
        except Exception:
            pass
    package.update_package_index()
    available = package.get_available_packages()
    candidate = next((p for p in available if p.from_code == "ru" and p.to_code == "en"), None)
    if candidate is None:
        raise RuntimeError("Argos Russian -> English package is unavailable")
    package.install_from_path(candidate.download())


def translate_ru(text: str, cache: dict[str, str]) -> str:
    import argostranslate.translate as translate

    key = " ".join(str(text or "").split()).strip()
    if not key:
        return ""
    if key in cache:
        return cache[key]
    value = " ".join(translate.translate(key, "ru", "en").split()).strip()
    if not value or CYRILLIC.search(value):
        contextual = "Automotive manufacturing term: " + key
        value = " ".join(translate.translate(contextual, "ru", "en").split()).strip()
        value = re.sub(r"^(Automotive manufacturing term|Automotive industry term)\s*:\s*", "", value, flags=re.I)
    if not value:
        raise RuntimeError(f"empty English translation for {key!r}")
    cache[key] = value
    return value


def pinyin_for(text: str) -> str:
    from pypinyin import Style, lazy_pinyin
    return " ".join(lazy_pinyin(text, style=Style.TONE, neutral_tone_with_five=True))


def read_shop_source() -> list[dict[str, str]]:
    with SOURCE.open("r", encoding="utf-8", newline="") as fh:
        rows = list(csv.DictReader(fh, delimiter="|"))
    if len(rows) < 180:
        raise RuntimeError(f"shop expansion unexpectedly small: {len(rows)}")
    required = {"category", "subcategory", "zh", "ru", "en", "level"}
    for index, row in enumerate(rows, start=1):
        missing = [key for key in required if not str(row.get(key, "")).strip()]
        if missing:
            raise RuntimeError(f"shop row {index} missing {missing}")
        if row["level"] not in ALLOWED_LEVELS:
            raise RuntimeError(f"shop row {index} has invalid level {row['level']!r}")
    return rows


def build_shop(rows: list[dict[str, str]]) -> dict[str, list[dict[str, str]]]:
    chinese: list[dict[str, str]] = []
    english: list[dict[str, str]] = []
    counters: Counter[str] = Counter()
    for index, row in enumerate(rows, start=1):
        category = row["category"].strip()
        slug = {"Окраска": "paint", "Логистика": "logistics", "Кузов и компоненты": "body"}.get(category, "shop")
        counters[slug] += 1
        suffix = f"{slug}-{counters[slug]:03d}"
        zh = row["zh"].strip()
        ru = row["ru"].strip()
        en = row["en"].strip()
        level = row["level"].strip()
        subcategory = row["subcategory"].strip()
        example_zh = f"请确认{zh}是否符合工艺要求。"
        chinese.append({
            "id": f"v618-{suffix}",
            "category": category,
            "subcategory": subcategory,
            "zh": zh,
            "pinyin": pinyin_for(zh),
            "ru_read": "",
            "ru": ru,
            "note": "v6.0.18 расширение профессионального словаря по цехам",
            "type": "MGC curated automotive glossary",
            "example_zh": example_zh,
            "example_pinyin": pinyin_for(example_zh),
            "example_ru": f"Подтвердите, что «{ru}» соответствует требованиям процесса.",
            "level": level,
        })
        english.append({
            "id": f"en-v618-{suffix}",
            "topic": category,
            "category": category,
            "subcategory": subcategory,
            "term": en,
            "ru": ru,
            "level": level,
            "example_target": f"Confirm that the {en} meets the process requirement.",
            "example_ru": f"Подтвердите, что «{ru}» соответствует требованиям процесса.",
            "source": "MGC curated automotive glossary v6.0.18",
        })
    return {"chinese": chinese, "english": english}


def build_parallel(chinese_raw: dict, english_raw: dict) -> dict[str, list[dict[str, str]]]:
    source_rows = list(chinese_raw.get("items", []))
    english_rows = list(english_raw.get("items", []))
    needed = len(source_rows) - len(english_rows)
    if needed <= 0:
        return {"items": []}
    cache: dict[str, str] = {}
    generated: list[dict[str, str]] = []
    for row in source_rows:
        if len(generated) >= needed:
            break
        ru = " ".join(str(row.get("ru", "")).split()).strip()
        if not ru:
            continue
        term = translate_ru(ru, cache)
        category = str(row.get("category", "")).strip() or "Автопром"
        subcategory = str(row.get("subcategory", "")).strip() or category
        level = str(row.get("level", "B1")).strip()
        if level not in ALLOWED_LEVELS:
            level = "B1"
        generated.append({
            "id": f"en-parity-{row.get('id')}",
            "topic": category,
            "category": category,
            "subcategory": subcategory,
            "term": term,
            "ru": ru,
            "level": level,
            "example_target": f"Use the term “{term}” correctly in an automotive work instruction.",
            "example_ru": f"Используйте термин «{ru}» корректно в рабочей инструкции для автопрома.",
            "source": "Chinese corpus parity translation v6.0.18",
        })
    if len(generated) != needed:
        raise RuntimeError(f"English parity generation incomplete: expected {needed}, got {len(generated)}")
    return {"items": generated}


def main() -> int:
    chinese_raw = load_json("chinese.json")
    english_raw = load_json("english.json")
    shop_source = read_shop_source()
    shop = build_shop(shop_source)
    install_translation_model()
    parallel = build_parallel(chinese_raw, english_raw)

    SHOP_OUT.write_text(json.dumps(shop, ensure_ascii=False, indent=2), encoding="utf-8")
    PARITY_OUT.write_text(json.dumps(parallel, ensure_ascii=False, indent=2), encoding="utf-8")

    chinese_source = len(chinese_raw["items"]) + len(shop["chinese"])
    english_source = len(english_raw["items"]) + len(parallel["items"]) + len(shop["english"])
    if chinese_source != english_source:
        raise RuntimeError(f"source parity failed: Chinese={chinese_source}, English={english_source}")

    category_counts = Counter(item["category"] for item in shop["chinese"])
    manifest = {
        "release": "6.0.18",
        "base_chinese": len(chinese_raw["items"]),
        "base_english": len(english_raw["items"]),
        "generated_english_parallel": len(parallel["items"]),
        "shop_expansion_per_language": len(shop["chinese"]),
        "source_terms_per_language": chinese_source,
        "shop_additions": dict(sorted(category_counts.items())),
        "runtime_note": "Experience extra_terms are added equally to both languages at runtime, preserving parity.",
    }
    MANIFEST_OUT.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
