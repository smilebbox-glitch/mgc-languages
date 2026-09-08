#!/usr/bin/env python3
from __future__ import annotations

import csv
import json
import re
import time
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
HAN = re.compile(r"[\u3400-\u9fff]")

# Machine translation is only a bootstrap for the large bilingual parity layer.
# Automotive terms that are well known to be ambiguous in generic translation
# are fixed here to an engineering-safe canonical form.
AUTOMOTIVE_OVERRIDES_ZH = {
    "自攻螺钉": "self-tapping screw",
    "左后尾灯": "left rear tail lamp",
    "右后尾灯": "right rear tail lamp",
    "白车身": "body-in-white",
    "扭矩扳手": "torque wrench",
    "电泳涂装": "electrocoating",
    "电泳": "electrocoating",
    "喷漆室": "paint booth",
    "喷房": "spray booth",
    "看板": "kanban",
    "纵梁": "side member",
    "前纵梁": "front side member",
    "后纵梁": "rear side member",
    "面差": "flushness",
    "型面": "surface profile",
    "凹痕": "dent",
    "橘皮": "orange peel",
    "流挂": "paint run / sag",
    "针孔": "pinhole",
    "焊点": "weld spot",
    "焊缝": "weld seam",
    "点焊": "spot welding",
    "工装": "tooling",
    "工装夹具": "fixture",
    "检具": "checking fixture",
    "夹具": "fixture",
    "保险杠": "bumper",
    "翼子板": "fender",
    "侧围": "body side",
    "门槛": "rocker panel / sill",
    "间隙": "gap",
    "总成": "assembly",
    "分总成": "subassembly",
    "钣金件": "sheet-metal part",
    "冲压件": "stamped part",
    "供应链": "supply chain",
    "关税": "customs duty",
    "清关": "customs clearance",
    "报关": "customs declaration",
    "先进先出": "FIFO",
    "顺序供货": "just-in-sequence delivery",
    "准时化": "just-in-time",
    "周转箱": "returnable container",
    "线边仓": "line-side storage",
    "齐套": "kit completeness",
    "补货": "replenishment",
    "物料搬运": "material handling",
    "安全库存": "safety stock",
    "缺料": "material shortage",
}

AUTOMOTIVE_OVERRIDES_RU = {
    "саморез": "self-tapping screw",
    "кузов в белом": "body-in-white",
    "динамометрический ключ": "torque wrench",
    "электрофоретическое покрытие": "electrocoating",
    "окрасочная камера": "paint booth",
    "канбан": "kanban",
    "лонжерон": "side member",
    "перепад поверхностей": "flushness",
    "профиль поверхности": "surface profile",
    "точечная сварка": "spot welding",
    "сварная точка": "weld spot",
    "сварной шов": "weld seam",
    "кузов автомобиля": "vehicle body",
    "боковина кузова": "body side",
    "штампованная деталь": "stamped part",
    "оборотная тара": "returnable container",
    "страховой запас": "safety stock",
    "дефицит материала": "material shortage",
    "таможенная очистка": "customs clearance",
    "таможенное декларирование": "customs declaration",
    "комплектность": "kit completeness",
}


def load_json(name: str):
    return json.loads((DATA / name).read_text(encoding="utf-8"))


def normalize_text(value: str) -> str:
    return " ".join(str(value or "").replace(" ", " ").split()).strip()


def clean_english(value: str) -> str:
    text = normalize_text(value)
    text = re.sub(r"^[\"'“”]+|[\"'“”]+$", "", text).strip()
    text = re.sub(r"\s+([,.;:])", r"\1", text)
    if text.endswith(".") and text.count(".") == 1:
        text = text[:-1].strip()
    if text and text.isupper() is False and len(text) > 1:
        text = text[0].lower() + text[1:]
    return text


def valid_english(value: str) -> bool:
    text = clean_english(value)
    return bool(text) and not CYRILLIC.search(text) and not HAN.search(text)


def make_google_translator():
    from deep_translator import GoogleTranslator
    return GoogleTranslator(source="ru", target="en")


def translate_ru(text: str, translator, cache: dict[str, str], *, zh: str = "") -> str:
    ru = normalize_text(text)
    chinese = normalize_text(zh)
    if not ru:
        return ""
    if chinese in AUTOMOTIVE_OVERRIDES_ZH:
        return AUTOMOTIVE_OVERRIDES_ZH[chinese]
    if ru.casefold() in AUTOMOTIVE_OVERRIDES_RU:
        return AUTOMOTIVE_OVERRIDES_RU[ru.casefold()]
    if ru in cache:
        return cache[ru]

    last_error: Exception | None = None
    for attempt in range(4):
        try:
            value = clean_english(translator.translate(ru))
            if not valid_english(value):
                raise ValueError(f"invalid English translation {value!r}")
            cache[ru] = value
            time.sleep(0.08)
            return value
        except Exception as exc:  # pragma: no cover - network dependent fallback
            last_error = exc
            time.sleep(0.8 * (attempt + 1))
    raise RuntimeError(f"English translation failed for {ru!r}: {last_error}")


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
    for row in rows:
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


def existing_parallel_by_id() -> dict[str, dict[str, str]]:
    """Use the committed parity corpus as a deterministic translation memory.

    The external translator is only a fallback for genuinely new Chinese rows.
    This makes CI reproducible and prevents a public translation outage from
    invalidating an already-reviewed 1479-row corpus.
    """
    if not PARITY_OUT.exists():
        return {}
    try:
        payload = json.loads(PARITY_OUT.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return {
        str(row.get("id", "")): row
        for row in payload.get("items", [])
        if str(row.get("id", ""))
    }


def build_parallel(chinese_raw: dict, english_raw: dict) -> dict[str, list[dict[str, str]]]:
    source_rows = list(chinese_raw.get("items", []))
    english_rows = list(english_raw.get("items", []))
    needed = len(source_rows) - len(english_rows)
    if needed <= 0:
        return {"items": []}

    translation_memory = existing_parallel_by_id()
    translator = None
    cache: dict[str, str] = {}
    generated: list[dict[str, str]] = []
    source_counts: Counter[str] = Counter()

    for row in source_rows:
        if len(generated) >= needed:
            break
        ru = normalize_text(row.get("ru", ""))
        zh = normalize_text(row.get("zh", ""))
        if not ru:
            continue

        parity_id = f"en-parity-{row.get('id')}"
        override = AUTOMOTIVE_OVERRIDES_ZH.get(zh) or AUTOMOTIVE_OVERRIDES_RU.get(ru.casefold())
        previous = translation_memory.get(parity_id, {})
        previous_term = clean_english(previous.get("term", ""))

        if override:
            term = override
            source_counts["automotive_override"] += 1
        elif valid_english(previous_term):
            term = previous_term
            source_counts["committed_translation_memory"] += 1
        else:
            if translator is None:
                translator = make_google_translator()
            term = translate_ru(ru, translator, cache, zh=zh)
            source_counts["google_fallback"] += 1

        category = str(row.get("category", "")).strip() or "Автопром"
        subcategory = str(row.get("subcategory", "")).strip() or category
        level = str(row.get("level", "B1")).strip()
        if level not in ALLOWED_LEVELS:
            level = "B1"
        generated.append({
            "id": parity_id,
            "topic": category,
            "category": category,
            "subcategory": subcategory,
            "term": term,
            "ru": ru,
            "level": level,
            "example_target": f"Use the term “{term}” correctly in an automotive work instruction.",
            "example_ru": f"Используйте термин «{ru}» корректно в рабочей инструкции для автопрома.",
            "source": "Chinese corpus parity translation v6.0.18 / reviewed automotive glossary",
        })

    if len(generated) != needed:
        raise RuntimeError(f"English parity generation incomplete: expected {needed}, got {len(generated)}")

    by_ru = {item["ru"].casefold(): item["term"].casefold() for item in generated}
    required_pairs = {
        "саморез": "self-tapping screw",
        "кузов в белом": "body-in-white",
        "динамометрический ключ": "torque wrench",
        "канбан": "kanban",
        "лонжерон": "side member",
        "перепад поверхностей": "flushness",
    }
    for russian, expected in required_pairs.items():
        if russian in by_ru and by_ru[russian] != expected:
            raise RuntimeError(f"automotive glossary regression: {russian!r} -> {by_ru[russian]!r}, expected {expected!r}")
    for item in generated:
        term = item["term"]
        if CYRILLIC.search(term) or HAN.search(term):
            raise RuntimeError(f"non-English characters leaked into parity term: {item['id']}={term!r}")
        if term.casefold() in {"selfie", "left-light", "watch", "liang", "face difference", "the wrench"}:
            raise RuntimeError(f"known bad machine translation leaked into corpus: {item['id']}={term!r}")

    build_parallel.source_counts = dict(source_counts)
    return {"items": generated}


def main() -> int:
    chinese_raw = load_json("chinese.json")
    english_raw = load_json("english.json")
    shop_source = read_shop_source()
    shop = build_shop(shop_source)
    parallel = build_parallel(chinese_raw, english_raw)

    SHOP_OUT.write_text(json.dumps(shop, ensure_ascii=False, indent=2), encoding="utf-8")
    PARITY_OUT.write_text(json.dumps(parallel, ensure_ascii=False, indent=2), encoding="utf-8")

    chinese_source = len(chinese_raw["items"]) + len(shop["chinese"])
    english_source = len(english_raw["items"]) + len(parallel["items"]) + len(shop["english"])
    if chinese_source != english_source:
        raise RuntimeError(f"source parity failed: Chinese={chinese_source}, English={english_source}")

    category_counts = Counter(item["category"] for item in shop["chinese"])
    translation_sources = getattr(build_parallel, "source_counts", {})
    manifest = {
        "release": "6.0.18",
        "base_chinese": len(chinese_raw["items"]),
        "base_english": len(english_raw["items"]),
        "generated_english_parallel": len(parallel["items"]),
        "shop_expansion_per_language": len(shop["chinese"]),
        "source_terms_per_language": chinese_source,
        "shop_additions": dict(sorted(category_counts.items())),
        "english_translation": "committed translation memory + automotive override glossary; Google fallback only for new/missing rows",
        "english_translation_sources": translation_sources,
        "runtime_note": "Experience extra_terms are added equally to both languages at runtime, preserving parity.",
    }
    MANIFEST_OUT.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
