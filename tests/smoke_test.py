from __future__ import annotations

import ast
import json
import random
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load_json(name: str):
    return json.loads((ROOT / "data" / name).read_text(encoding="utf-8"))


def load_function(name: str):
    source = (ROOT / "app.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    node = next(item for item in tree.body if isinstance(item, ast.FunctionDef) and item.name == name)
    namespace = {"random": random, "HTTPException": RuntimeError}
    exec(compile(ast.Module(body=[node], type_ignores=[]), "app.py", "exec"), namespace)
    return namespace[name]


topic_for = load_function("topic_for")
make_question = load_function("make_question")
experience = load_json("experience.json")
english = load_json("english.json")["items"]
chinese = load_json("chinese.json")["items"]


def normalized_rows(language: str):
    if language == "english":
        rows = [{
            "id": item["id"],
            "topic": topic_for(item.get("topic", ""), item.get("category", ""), item.get("subcategory", ""), item.get("term", ""), item.get("ru", "")),
            "term": item["term"], "translation": item["ru"], "level": item["level"],
            "pronunciation": "", "example": item.get("example_target", ""),
            "example_pronunciation": "", "example_translation": item.get("example_ru", ""),
        } for item in english]
    else:
        rows = [{
            "id": "zh-" + str(item["id"]),
            "topic": topic_for(item.get("category", ""), item.get("subcategory", ""), item.get("ru", ""), item.get("note", "")),
            "term": item.get("zh", ""), "translation": item.get("ru", ""), "level": item.get("level", "B1"),
            "pronunciation": item.get("pinyin", ""), "example": item.get("example_zh", "") or item.get("zh", ""),
            "example_pronunciation": item.get("example_pinyin", ""),
            "example_translation": item.get("example_ru", "") or item.get("ru", ""),
        } for item in chinese]
    for item in experience["extra_terms"]:
        rows.append({
            "id": language[:2] + "-" + item["id"], "topic": item["topic"], "level": item["level"],
            "term": item["en"] if language == "english" else item["zh"],
            "translation": item["en_ru"] if language == "english" else item["zh_ru"],
            "pronunciation": "" if language == "english" else item["pinyin"],
            "example": item["en"] if language == "english" else item["zh"],
            "example_pronunciation": "" if language == "english" else item["pinyin"],
            "example_translation": item["en_ru"] if language == "english" else item["zh_ru"],
        })
    return rows


topic_labels = [item["label"] for item in experience["topics"]]
assert len(topic_labels) == 21
assert len(set(topic_labels)) == len(topic_labels)

for language in ("english", "chinese"):
    rows = normalized_rows(language)
    counts = Counter(item["topic"] for item in rows)
    assert all(counts[label] >= 5 for label in topic_labels), (language, counts)
    levels = Counter(item["level"] for item in rows)
    assert all(levels[level] >= 10 for level in ("A1", "A2", "B1", "B2", "C1"))
    for topic in topic_labels:
        pool = [item for item in rows if item["topic"] == topic]
        for candidate in pool:
            question = make_question(candidate, pool, random.Random(10), language)
            assert len(question["options"]) == 4
            assert question["options"][question["correct_index"]]
            if language == "chinese":
                assert question["pronunciation"]

roleplays = load_json("app_content.json")["roleplays"] + experience["added_roleplays"]
assert len(roleplays) >= 35
assert len({item["id"] for item in roleplays}) == len(roleplays)
for item in roleplays:
    for field in ("topic", "title", "goal", "roles", "en", "en_ru", "zh", "pinyin", "zh_ru", "prompts"):
        assert item[field], (item["id"], field)

assert len(experience["knowledge"]) >= 12
for item in experience["knowledge"]:
    assert len(item["steps"]) >= 3
    for field in ("situation", "avoid", "en", "en_ru", "zh", "pinyin", "zh_ru"):
        assert item[field], (item["id"], field)

html = (ROOT / "static" / "index.html").read_text(encoding="utf-8")
javascript = (ROOT / "static" / "app.js").read_text(encoding="utf-8")
for removed in ("Переводчик", "Голос", "Карточки", 'data-view="translator"', 'data-view="voice"', 'data-view="learn"'):
    assert removed not in html + javascript, removed
assert "Термины, реальные рабочие ситуации и тренировка коммуникации в Автопромышленности." in javascript
assert "35 из 50" in javascript
assert "Пройти тест дня" in javascript

print("OK: bilingual content, 21 topics, scenario game, daily tests and 35/50 exam rule")
