#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import re
import sys
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
STATIC = ROOT / "static"

REQUIRED_JSON = {
    "chinese.json": 1_000_000,
    "chinese_foundations.json": 10_000,
    "english.json": 20_000,
    "experience.json": 500,
    "app_content.json": 1_000,
}

HAN_RE = re.compile(r"[\u3400-\u9fff]")
LEVELS = {"A1", "A2", "B1", "B2", "C1"}


def load_json(name: str) -> Any:
    path = DATA / name
    assert path.is_file(), f"missing source language file: {path}"
    assert path.stat().st_size >= REQUIRED_JSON[name], f"source language file unexpectedly small: {name}"
    value = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(value, (dict, list)) and value, f"empty JSON content: {name}"
    return value


def walk_strings(value: Any):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for key, item in value.items():
            yield str(key)
            yield from walk_strings(item)
    elif isinstance(value, list):
        for item in value:
            yield from walk_strings(item)


def check_required_json() -> dict[str, Any]:
    payloads = {name: load_json(name) for name in REQUIRED_JSON}
    print(f"PASS required JSON files ({len(payloads)})")
    return payloads


def check_chinese_corpus(payload: Any) -> None:
    assert isinstance(payload, dict) and isinstance(payload.get("items"), list)
    items = payload["items"]
    assert len(items) >= 500, "Chinese dictionary unexpectedly small"

    ids: list[str] = []
    han_terms = 0
    for index, row in enumerate(items, start=1):
        assert isinstance(row, dict), f"Chinese item #{index} is not an object"
        for field in ("id", "category", "subcategory", "zh", "pinyin", "ru", "level"):
            assert str(row.get(field, "")).strip(), f"Chinese item #{index} has empty {field}"
        assert row["level"] in LEVELS, f"Chinese item #{index} has unsupported level {row['level']!r}"
        ids.append(str(row["id"]))
        if HAN_RE.search(str(row["zh"])):
            han_terms += 1
        if str(row.get("example_zh", "")).strip():
            assert str(row.get("example_pinyin", "")).strip(), f"Chinese item #{index} has example without pinyin"
            assert str(row.get("example_ru", "")).strip(), f"Chinese item #{index} has example without Russian translation"

    assert len(ids) == len(set(ids)), "duplicate IDs in Chinese dictionary"
    assert han_terms / len(ids) >= 0.95, "too many Chinese dictionary entries have no Han characters"

    strings = [s.strip() for s in walk_strings(payload) if s.strip()]
    han_strings = [s for s in strings if HAN_RE.search(s)]
    assert len(strings) >= 1_000, "Chinese corpus lost too much structured text"
    assert len(han_strings) >= 250, "Chinese corpus no longer contains enough Han-language learning material"
    print(f"PASS Chinese corpus ({len(items)} terms, {len(han_strings)} strings with Han characters)")


def check_foundations(payload: Any) -> None:
    assert isinstance(payload, dict)
    assert len(payload.get("tones", [])) == 5, "Chinese foundations must keep the five-tone teaching model"
    assert payload.get("pinyin", {}).get("formula"), "Pinyin formula is missing"
    assert payload.get("context", {}).get("clues"), "Chinese context clues are missing"
    putonghua = payload.get("putonghua", {})
    assert len(putonghua.get("groups", [])) == 10, "Putonghua reference groups changed unexpectedly"
    assert (payload.get("learning_standard") or {}).get("name") == "Путунхуа (普通话)", "Learning standard must stay Putonghua"

    levels = payload.get("levels", [])
    if levels:
        seen_lessons: set[str] = set()
        for level in levels:
            assert isinstance(level, dict) and level.get("level"), "foundation level is missing its name"
            for lesson in level.get("lessons", []):
                lesson_id = str(lesson.get("id", "")).strip()
                assert lesson_id, "foundation lesson has a blank id"
                assert lesson_id not in seen_lessons, f"duplicate foundation lesson id: {lesson_id}"
                seen_lessons.add(lesson_id)
                assert str(lesson.get("title", "")).strip(), f"foundation lesson {lesson_id} has no title"
    print("PASS Chinese foundations / Putonghua contract")


def check_app_content(payload: Any) -> None:
    assert isinstance(payload, dict)
    topics = payload.get("topics", [])
    roleplays = payload.get("roleplays", [])
    assert len(topics) >= 8, "automotive topic catalog is unexpectedly small"
    assert len(roleplays) >= 4, "roleplay catalog is unexpectedly small"

    topic_ids = [str(item.get("id", "")).strip() for item in topics]
    assert all(topic_ids), "topic id cannot be blank"
    assert len(topic_ids) == len(set(topic_ids)), "topic ids must be unique"

    roleplay_ids: set[str] = set()
    for item in roleplays:
        rid = str(item.get("id", "")).strip()
        assert rid and rid not in roleplay_ids, f"blank or duplicate roleplay id: {rid!r}"
        roleplay_ids.add(rid)
        for field in ("title", "goal", "en", "en_ru", "zh", "pinyin", "zh_ru"):
            assert str(item.get(field, "")).strip(), f"roleplay {rid} is missing {field}"
        assert HAN_RE.search(str(item["zh"])), f"roleplay {rid} Chinese phrase has no Han characters"
    print(f"PASS automotive topics/roleplays ({len(topics)} topics, {len(roleplays)} roleplays)")


def check_other_corpora(english: Any, experience: Any) -> None:
    assert isinstance(english, dict) and isinstance(english.get("items"), list)
    items = english["items"]
    assert len(items) >= 100, "English dictionary unexpectedly small"
    ids: list[str] = []
    for index, row in enumerate(items, start=1):
        for field in ("id", "topic", "term", "ru", "level"):
            assert str(row.get(field, "")).strip(), f"English item #{index} has empty {field}"
        assert row["level"] in LEVELS, f"English item #{index} has unsupported level {row['level']!r}"
        ids.append(str(row["id"]))
    assert len(ids) == len(set(ids)), "duplicate IDs in English dictionary"

    english_strings = [s.strip() for s in walk_strings(english) if s.strip()]
    experience_strings = [s.strip() for s in walk_strings(experience) if s.strip()]
    assert len(english_strings) >= 100, "English corpus is unexpectedly small"
    assert len(experience_strings) >= 10, "experience/help content is unexpectedly small"
    assert any(re.search(r"[A-Za-z]{4,}", s) for s in english_strings), "English corpus has no usable English text"
    print(f"PASS English and experience corpora ({len(items)} English terms)")


def check_static_assets() -> None:
    expected = {
        "index.html": 5_000,
        "app.js": 20_000,
        "styles.css": 5_000,
    }
    for name, minimum in expected.items():
        path = STATIC / name
        assert path.is_file(), f"missing runtime static asset: {name}"
        assert path.stat().st_size >= minimum, f"runtime static asset unexpectedly small: {name}"
    html = (STATIC / "index.html").read_text(encoding="utf-8")
    assert "MGC Languages" in html
    assert "Путунхуа" in html
    assert 'src="/app.js"' in html
    print("PASS static UI contract")


def check_runtime_ingestion(chinese: Any, english: Any) -> None:
    db_path = Path(tempfile.gettempdir()) / "mgc_languages_content_contract.db"
    try:
        db_path.unlink()
    except FileNotFoundError:
        pass
    os.environ.update({
        "DATABASE_URL": f"sqlite:///{db_path}",
        "AUTO_CREATE_SCHEMA": "true",
        "APP_ENV": "development",
        "AUTH_MODE": "local",
        "REGISTRATION_ENABLED": "true",
        "OIDC_STATE_SECRET": "content-contract-state-secret-32-bytes",
    })
    sys.path.insert(0, str(ROOT))
    import app  # noqa: E402

    assert app.APP_VERSION == "5.7.1", app.APP_VERSION
    assert "chinese" in app.TERMS and "english" in app.TERMS
    assert len(app.TERMS["chinese"]) >= len(chinese["items"])
    assert len(app.TERMS["english"]) >= len(english["items"])
    for language in ("chinese", "english"):
        for row in app.TERMS[language][:25]:
            for field in ("id", "topic", "term", "pronunciation", "translation", "level"):
                assert str(row.get(field, "")).strip(), f"normalized {language} term has empty {field}: {row!r}"
    print(
        f"PASS runtime language ingestion (Chinese={len(app.TERMS['chinese'])}, "
        f"English={len(app.TERMS['english'])})"
    )


def main() -> None:
    payloads = check_required_json()
    check_chinese_corpus(payloads["chinese.json"])
    check_foundations(payloads["chinese_foundations.json"])
    check_app_content(payloads["app_content.json"])
    check_other_corpora(payloads["english.json"], payloads["experience.json"])
    check_static_assets()
    check_runtime_ingestion(payloads["chinese.json"], payloads["english.json"])
    print("PASS language content contracts")


if __name__ == "__main__":
    main()
