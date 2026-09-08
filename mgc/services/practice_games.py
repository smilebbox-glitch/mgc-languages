from __future__ import annotations

import hashlib
import json
import random
import secrets
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session


MAX_GAME_ANSWERS = 5
GAME_TYPES = (
    "match",
    "listening",
    "mistake",
    "phrase",
    "hotspot",
    "assembly_order",
    "shop_route",
    "tool_select",
    "defect_detective",
    "safety_spot",
    "quality_gate",
    "logistics_route",
    "kanban",
    "bom_builder",
    "spec_check",
    "rapid_recall",
    "memory_pairs",
    "odd_one_out",
    "dialogue_choice",
    "shift_incident",
)

CAR_PARTS = (
    {"zone": "hood", "ru": "капот", "en": "hood", "zh": "发动机罩"},
    {"zone": "windshield", "ru": "ветровое стекло", "en": "windshield", "zh": "挡风玻璃"},
    {"zone": "mirror", "ru": "наружное зеркало", "en": "outside mirror", "zh": "外后视镜"},
    {"zone": "door", "ru": "дверь", "en": "door", "zh": "车门"},
    {"zone": "fender", "ru": "крыло", "en": "fender", "zh": "翼子板"},
    {"zone": "headlamp", "ru": "передняя фара", "en": "headlamp", "zh": "前大灯"},
    {"zone": "bumper", "ru": "передний бампер", "en": "front bumper", "zh": "前保险杠"},
    {"zone": "wheel", "ru": "колесо", "en": "wheel", "zh": "车轮"},
)

SHOPS = (
    {"id": "stamping", "ru": "Штамповка", "en": "Press Shop", "zh": "冲压车间"},
    {"id": "welding", "ru": "Сварка", "en": "Body Shop", "zh": "焊装车间"},
    {"id": "paint", "ru": "Окраска", "en": "Paint Shop", "zh": "涂装车间"},
    {"id": "assembly", "ru": "Сборка", "en": "Assembly Shop", "zh": "总装车间"},
    {"id": "quality", "ru": "Качество", "en": "Quality", "zh": "质量"},
    {"id": "logistics", "ru": "Логистика", "en": "Logistics", "zh": "物流"},
)

TOOLS = (
    {"ru": "динамометрический ключ", "en": "torque wrench", "zh": "扭矩扳手", "task_ru": "затянуть крепеж заданным моментом"},
    {"ru": "штангенциркуль", "en": "caliper", "zh": "游标卡尺", "task_ru": "измерить размер детали"},
    {"ru": "толщиномер", "en": "coating thickness gauge", "zh": "涂层测厚仪", "task_ru": "проверить толщину лакокрасочного покрытия"},
    {"ru": "сканер штрихкода", "en": "barcode scanner", "zh": "条码扫描器", "task_ru": "подтвердить партию материала"},
    {"ru": "щуп зазоров", "en": "feeler gauge", "zh": "塞尺", "task_ru": "проверить зазор"},
    {"ru": "мультиметр", "en": "multimeter", "zh": "万用表", "task_ru": "проверить напряжение и сопротивление"},
    {"ru": "краскораспылитель", "en": "spray gun", "zh": "喷枪", "task_ru": "нанести лакокрасочный материал"},
    {"ru": "вилочный погрузчик", "en": "forklift", "zh": "叉车", "task_ru": "переместить паллету"},
)

DEFECTS = (
    {"visual": "scratch", "ru": "царапина", "en": "scratch", "zh": "划痕"},
    {"visual": "dent", "ru": "вмятина", "en": "dent", "zh": "凹痕"},
    {"visual": "orange-peel", "ru": "апельсиновая корка", "en": "orange peel", "zh": "橘皮"},
    {"visual": "paint-run", "ru": "подтек краски", "en": "paint run", "zh": "流挂"},
    {"visual": "pinhole", "ru": "игольчатая пора", "en": "pinhole", "zh": "针孔"},
    {"visual": "weld-spatter", "ru": "сварочные брызги", "en": "weld spatter", "zh": "焊接飞溅"},
    {"visual": "gap", "ru": "неверный зазор", "en": "incorrect gap", "zh": "间隙异常"},
    {"visual": "flush", "ru": "перепад поверхностей", "en": "flushness deviation", "zh": "面差异常"},
)

SAFETY = (
    {"visual": "no-glasses", "ru": "нет защитных очков", "en": "missing safety glasses", "zh": "未佩戴护目镜"},
    {"visual": "open-guard", "ru": "открыто защитное ограждение", "en": "open machine guard", "zh": "防护门开启"},
    {"visual": "forklift-walkway", "ru": "погрузчик на пешеходном маршруте", "en": "forklift in pedestrian lane", "zh": "叉车进入人行通道"},
    {"visual": "spill", "ru": "разлив на полу", "en": "floor spill", "zh": "地面泄漏"},
    {"visual": "no-lockout", "ru": "нет блокировки энергии", "en": "missing lockout", "zh": "未执行上锁挂牌"},
    {"visual": "blocked-exit", "ru": "заблокирован аварийный выход", "en": "blocked emergency exit", "zh": "安全出口被堵塞"},
    {"visual": "hot-work", "ru": "огневые работы без защиты", "en": "unprotected hot work", "zh": "动火作业防护不足"},
    {"visual": "loose-load", "ru": "незакрепленный груз", "en": "unsecured load", "zh": "货物未固定"},
)

DIALOGUES = (
    {
        "ru": "Поставщик сообщает о дефекте партии. Какой ответ профессиональнее?",
        "en": ["Please start containment immediately and confirm the clean point.", "Maybe it will be fine.", "Send something later.", "We do not need details."],
        "zh": ["请立即启动遏制措施，并确认清洁点。", "可能没问题。", "以后再发点信息。", "我们不需要细节。"],
        "answer": 0,
    },
    {
        "ru": "Линия остановлена из-за датчика. Что уточнить первым?",
        "en": ["What is the confirmed failure mode and when did the line stop?", "Who is guilty?", "Can we ignore it?", "Is lunch ready?"],
        "zh": ["已确认的故障模式是什么？生产线什么时候停的？", "是谁的责任？", "可以忽略吗？", "午饭准备好了吗？"],
        "answer": 0,
    },
    {
        "ru": "Есть отклонение момента затяжки. Как действовать?",
        "en": ["Please isolate the affected vehicles and define the inspection range.", "Ship everything.", "Delete the record.", "Change the specification now."],
        "zh": ["请隔离受影响车辆，并确定检查范围。", "全部发运。", "删除记录。", "现在修改规范。"],
        "answer": 0,
    },
    {
        "ru": "Груз задержан на таможне. Какой вопрос наиболее полезен?",
        "en": ["Which document is missing and what is the revised ETA?", "Who likes the carrier?", "Can we stop tracking it?", "Is the truck new?"],
        "zh": ["缺少哪份文件？更新后的预计到达时间是什么？", "谁喜欢这个承运商？", "可以停止追踪吗？", "卡车是新的吗？"],
        "answer": 0,
    },
    {
        "ru": "На gate review остается критический открытый вопрос. Что сказать?",
        "en": ["We need an owner, due date and evidence before the gate decision.", "Let us close it verbally.", "It is probably okay.", "No action is required."],
        "zh": ["在阶段决策前，我们需要责任人、截止日期和证据。", "口头关闭就可以。", "应该没问题。", "不需要采取行动。"],
        "answer": 0,
    },
)

SHIFT_INCIDENTS = (
    {"ru": "У детали обнаружен критический дефект на линии.", "en": ["Stop and contain the affected flow", "Continue production without record", "Hide the defect", "Wait until tomorrow"], "zh": ["停止并遏制受影响的物流", "不记录继续生产", "隐藏缺陷", "等到明天"], "answer": 0},
    {"ru": "На линии заканчивается компонент через 40 минут.", "en": ["Escalate shortage and activate replenishment", "Ignore the signal", "Increase takt time", "Delete stock data"], "zh": ["升级缺料并启动补货", "忽略信号", "提高节拍", "删除库存数据"], "answer": 0},
    {"ru": "В окрасочной камере выросло число частиц.", "en": ["Hold affected bodies and check booth conditions", "Increase paint flow only", "Ship bodies immediately", "Disable inspection"], "zh": ["隔离受影响车身并检查喷房条件", "只增加涂料流量", "立即发运车身", "关闭检查"], "answer": 0},
    {"ru": "Поставщик изменил материал без согласования.", "en": ["Block the change and start formal validation", "Accept it silently", "Change BOM later", "Skip traceability"], "zh": ["阻止变更并启动正式验证", "默认接受", "以后再改BOM", "跳过追溯"], "answer": 0},
    {"ru": "Near miss произошел в высоковольтной зоне.", "en": ["Secure the area and start fact-based investigation", "Restart immediately", "Remove witnesses", "Ignore because nobody was hurt"], "zh": ["隔离区域并启动基于事实的调查", "立即重新启动", "移走目击者", "因为没人受伤所以忽略"], "answer": 0},
)

ASSEMBLY_SEQUENCES = (
    ("Основной производственный поток", [
        {"ru": "Штамповка", "en": "Stamping", "zh": "冲压"},
        {"ru": "Сварка кузова", "en": "Body welding", "zh": "焊装"},
        {"ru": "Окраска", "en": "Painting", "zh": "涂装"},
        {"ru": "Сборка", "en": "Assembly", "zh": "总装"},
        {"ru": "Финальный контроль", "en": "Final inspection", "zh": "终检"},
    ]),
    ("Подготовка к окраске", [
        {"ru": "Обезжиривание", "en": "Degreasing", "zh": "脱脂"},
        {"ru": "Фосфатирование", "en": "Phosphating", "zh": "磷化"},
        {"ru": "Электрофорез", "en": "E-coating", "zh": "电泳涂装"},
        {"ru": "Герметизация", "en": "Sealing", "zh": "涂胶"},
        {"ru": "Финишная окраска", "en": "Topcoat", "zh": "面漆"},
    ]),
    ("Приемка материала", [
        {"ru": "Прибытие", "en": "Arrival", "zh": "到货"},
        {"ru": "Приемка", "en": "Receiving", "zh": "收货"},
        {"ru": "Сканирование", "en": "Scanning", "zh": "扫码"},
        {"ru": "Размещение", "en": "Put-away", "zh": "入库"},
        {"ru": "Пополнение линии", "en": "Line replenishment", "zh": "补货"},
    ]),
    ("Реакция на дефект", [
        {"ru": "Остановить", "en": "Stop", "zh": "停止"},
        {"ru": "Изолировать", "en": "Contain", "zh": "遏制"},
        {"ru": "Проверить", "en": "Inspect", "zh": "检查"},
        {"ru": "Устранить причину", "en": "Correct cause", "zh": "纠正原因"},
        {"ru": "Подтвердить эффективность", "en": "Verify effectiveness", "zh": "验证有效性"},
    ]),
    ("Изменение конструкции", [
        {"ru": "Запрос изменения", "en": "Change request", "zh": "变更申请"},
        {"ru": "Оценка влияния", "en": "Impact assessment", "zh": "影响评估"},
        {"ru": "Согласование", "en": "Approval", "zh": "批准"},
        {"ru": "Валидация", "en": "Validation", "zh": "验证"},
        {"ru": "Внедрение", "en": "Implementation", "zh": "实施"},
    ]),
)

LOGISTICS_SEQUENCES = (
    ["ASN", "Receiving", "Scan", "Put-away", "Line replenishment"],
    ["Pick", "Pack", "Label", "Load", "Ship"],
    ["Booking", "Pickup", "Customs", "Transport", "Delivery"],
    ["Count", "Reconcile", "Correct", "Release", "Report"],
    ["Shortage signal", "Confirm stock", "Expedite", "Deliver", "Close alert"],
)


@dataclass(frozen=True)
class PracticeGameWorkflowBindings:
    save_practice_result: Callable[..., dict[str, Any]]
    start_game: Callable[..., dict[str, Any]]
    finish_game: Callable[..., dict[str, Any]]
    question_attempt: Callable[..., dict[str, Any]]


def practice_raw_xp(kind: str, score: int, total: int) -> int:
    ratio = score / max(1, total)
    if kind == "quiz":
        return 20 + (10 if ratio >= .9 else 0) + (10 if ratio == 1 else 0)
    if kind == "scenario":
        return max(2, score * 5)
    if kind == "pair":
        return 5 if score else 1
    if kind == "course_day":
        return 25 + (10 if ratio == 1 else 0)
    if kind == "tone_lab":
        return 8 + score * 2 + (7 if ratio == 1 else 0)
    return (100 if ratio >= .7 else 25) + (50 if ratio >= .9 else 0)


def chunk_chinese(text_value: str) -> list[str]:
    text_value = text_value.strip()
    if " " in text_value:
        return [item for item in text_value.split() if item]
    return [text_value[index:index + 2] for index in range(0, len(text_value), 2)]


def score_game_answers(correct_answers: list[Any], submitted_answers: list[Any]) -> int:
    score = 0
    for index, correct in enumerate(correct_answers):
        if index >= len(submitted_answers):
            break
        answer = submitted_answers[index]
        if isinstance(correct, list):
            if isinstance(answer, list) and list(answer) == correct:
                score += 1
        elif answer == correct:
            score += 1
    return score


def _target(item: dict[str, Any], language: str) -> str:
    return str(item.get("zh" if language == "chinese" else "en", ""))


def _choice_options(correct: str, alternatives: list[str], rng: random.Random) -> tuple[list[str], int]:
    candidates = [correct] + [value for value in alternatives if value and value != correct]
    unique = list(dict.fromkeys(candidates))
    if len(unique) < 4:
        unique.extend(["—"] * (4 - len(unique)))
    options = unique[:4]
    rng.shuffle(options)
    return options, options.index(correct)


def _term_choice(row: dict[str, Any], pool: list[dict[str, Any]], rng: random.Random, *, prompt: str = "") -> tuple[dict[str, Any], int]:
    distractors = rng.sample([candidate for candidate in pool if candidate["id"] != row["id"]], 3)
    options = [row["translation"], *[candidate["translation"] for candidate in distractors]]
    rng.shuffle(options)
    return ({
        "kind": "choice",
        "id": row["id"],
        "prompt": prompt,
        "term": row["term"],
        "pronunciation": row.get("pronunciation", ""),
        "reading": row.get("reading", ""),
        "options": options,
    }, options.index(row["translation"]))


def build_practice_game_workflows(
    *,
    practice_result_model: Any,
    game_session_model: Any,
    question_attempt_model: Any,
    validate_language: Callable[[str], str],
    consume_daily_quota: Callable[..., Any],
    practice_daily_cap: int,
    game_daily_cap: int,
    require_feature: Callable[..., None],
    terms_for: Callable[[str, Session], list[dict[str, Any]]],
    gamification_view: Callable[[Session, int], dict[str, Any]],
    award_xp: Callable[..., dict[str, Any]],
    get_or_create_srs_card: Callable[..., Any],
    schedule_srs: Callable[..., Any],
    rate_limit: Callable[..., None],
) -> PracticeGameWorkflowBindings:
    """Build endpoint-compatible practice/game workflows without importing app.py."""

    def game_pool(language: str, topic: str, db: Session) -> list[dict[str, Any]]:
        pool = terms_for(language, db)
        if topic:
            filtered = [row for row in pool if row["topic"] == topic]
            if len(filtered) >= 6:
                pool = filtered
        return pool

    def save_practice_result(payload: Any, user: Any, db: Session) -> dict[str, Any]:
        language = validate_language(payload.language)
        existing = db.scalar(select(practice_result_model).where(practice_result_model.session_id == payload.session_id))
        if existing:
            return {"ok": True, "duplicate": True, "profile": gamification_view(db, user.id)}
        consume_daily_quota(db, user.id, "practice_submissions", int(practice_daily_cap))
        if payload.score > payload.total:
            raise HTTPException(400, "Некорректный результат")
        db.add(practice_result_model(
            user_id=user.id,
            session_id=payload.session_id,
            kind=payload.kind,
            language=language,
            topic=payload.topic,
            score=payload.score,
            total=payload.total,
        ))
        raw = practice_raw_xp(payload.kind, payload.score, payload.total)
        award = award_xp(
            db, user.id, payload.kind, payload.topic or payload.session_id, raw,
            language=language, topic=payload.topic,
            idempotency_key=f"practice:{user.id}:{payload.session_id}",
            metadata={"score": payload.score, "total": payload.total}, anti_farm=True,
        )
        db.commit()
        return {"ok": True, "duplicate": False, **award}

    def _generate_items(game_type: str, language: str, pool: list[dict[str, Any]], rng: random.Random) -> tuple[list[dict[str, Any]], list[Any]]:
        selected = rng.sample(pool, min(MAX_GAME_ANSWERS, len(pool)))
        items: list[dict[str, Any]] = []
        answers: list[Any] = []

        if game_type == "match":
            for row in selected:
                item, answer = _term_choice(row, pool, rng, prompt="Сопоставьте термин и точный перевод")
                item["kind"] = "match"
                items.append(item); answers.append(answer)
            return items, answers

        if game_type == "listening":
            for row in selected:
                item, answer = _term_choice(row, pool, rng, prompt="Прослушайте термин и выберите значение")
                item.update({"kind": "listening", "audio_text": row["term"]})
                items.append(item); answers.append(answer)
            return items, answers

        if game_type == "mistake":
            for row in selected:
                item, answer = _term_choice(row, pool, rng, prompt="Какое значение точное?")
                item["kind"] = "mistake"
                items.append(item); answers.append(answer)
            return items, answers

        if game_type == "phrase":
            phrase_rows = [row for row in pool if len((row.get("example") or "").strip()) >= 8] or pool
            selected = rng.sample(phrase_rows, min(MAX_GAME_ANSWERS, len(phrase_rows)))
            for row in selected:
                phrase = row.get("example") or row["term"]
                tokens = phrase.split() if language == "english" else chunk_chinese(phrase)
                shuffled = list(tokens); rng.shuffle(shuffled)
                items.append({"kind": "order", "id": row["id"], "prompt": "Соберите рабочую фразу", "translation": row.get("example_translation") or row["translation"], "tokens": shuffled})
                answers.append(tokens)
            return items, answers

        if game_type == "hotspot":
            parts = list(CAR_PARTS); rng.shuffle(parts)
            zones = [{"id": p["zone"], "label": p["ru"]} for p in CAR_PARTS]
            for part in parts[:MAX_GAME_ANSWERS]:
                items.append({"kind": "hotspot", "prompt": "Найдите деталь на автомобиле", "target": _target(part, language), "translation": part["ru"], "zones": zones})
                answers.append(part["zone"])
            return items, answers

        if game_type == "assembly_order":
            sequences = list(ASSEMBLY_SEQUENCES); rng.shuffle(sequences)
            for title, steps in sequences[:MAX_GAME_ANSWERS]:
                correct = [_target(step, language) for step in steps]
                shuffled = list(correct); rng.shuffle(shuffled)
                items.append({"kind": "order", "prompt": title, "translation": "Расставьте этапы в правильной последовательности", "tokens": shuffled})
                answers.append(correct)
            return items, answers

        if game_type == "shop_route":
            source = list(SHOPS); rng.shuffle(source)
            for shop in source[:MAX_GAME_ANSWERS]:
                correct = shop["ru"]
                options, answer = _choice_options(correct, [s["ru"] for s in SHOPS if s["id"] != shop["id"]], rng)
                items.append({"kind": "shop-route", "prompt": "Отправьте термин в правильный цех", "term": _target(shop, language), "translation": correct, "options": options, "shop": shop["id"]})
                answers.append(answer)
            return items, answers

        if game_type == "tool_select":
            source = list(TOOLS); rng.shuffle(source)
            for tool in source[:MAX_GAME_ANSWERS]:
                correct = _target(tool, language)
                options, answer = _choice_options(correct, [_target(t, language) for t in TOOLS if t is not tool], rng)
                items.append({"kind": "tool", "prompt": tool["task_ru"], "options": options, "translation": tool["ru"]})
                answers.append(answer)
            return items, answers

        if game_type == "defect_detective":
            source = list(DEFECTS); rng.shuffle(source)
            for defect in source[:MAX_GAME_ANSWERS]:
                correct = _target(defect, language)
                options, answer = _choice_options(correct, [_target(d, language) for d in DEFECTS if d is not defect], rng)
                items.append({"kind": "defect", "prompt": "Определите дефект по визуальному признаку", "visual": defect["visual"], "options": options, "translation": defect["ru"]})
                answers.append(answer)
            return items, answers

        if game_type == "safety_spot":
            source = list(SAFETY); rng.shuffle(source)
            for hazard in source[:MAX_GAME_ANSWERS]:
                correct = _target(hazard, language)
                options, answer = _choice_options(correct, [_target(h, language) for h in SAFETY if h is not hazard], rng)
                items.append({"kind": "safety", "prompt": "Что небезопасно в рабочей зоне?", "visual": hazard["visual"], "options": options, "translation": hazard["ru"]})
                answers.append(answer)
            return items, answers

        if game_type == "quality_gate":
            specs = [(10.0, 9.8, 10.2, 10.05, "PASS"), (8.0, 7.9, 8.1, 8.24, "REWORK"), (3.5, 3.4, 3.6, 3.31, "HOLD"), (25.0, 24.5, 25.5, 25.2, "PASS"), (1.2, 1.0, 1.4, 1.58, "REWORK")]
            for nominal, low, high, actual, result in specs:
                options = ["PASS", "REWORK", "HOLD"]; rng.shuffle(options)
                items.append({"kind": "quality-gate", "prompt": f"Спецификация {low:g}–{high:g}; измерено {actual:g}. Решение?", "nominal": nominal, "low": low, "high": high, "actual": actual, "options": options})
                answers.append(options.index(result))
            return items, answers

        if game_type == "logistics_route":
            for sequence in LOGISTICS_SEQUENCES[:MAX_GAME_ANSWERS]:
                correct = list(sequence)
                shuffled = list(correct); rng.shuffle(shuffled)
                items.append({"kind": "order", "prompt": "Восстановите логистическую последовательность", "translation": "Материальный поток", "tokens": shuffled})
                answers.append(correct)
            return items, answers

        if game_type == "kanban":
            cases = [(2, 8, "Пополнить"), (9, 8, "Не пополнять"), (0, 6, "Пополнить"), (12, 10, "Не пополнять"), (4, 5, "Пополнить")]
            for stock, trigger, correct in cases:
                options = ["Пополнить", "Не пополнять", "Заблокировать склад"]; rng.shuffle(options)
                items.append({"kind": "kanban", "prompt": f"Остаток: {stock}; точка заказа: {trigger}. Что делать?", "stock": stock, "trigger": trigger, "options": options})
                answers.append(options.index(correct))
            return items, answers

        if game_type == "bom_builder":
            systems = {
                "Кузов": ["bumper", "door", "fender", "hood"],
                "Интерьер": ["seat", "instrument panel", "headliner", "carpet"],
                "Электрика": ["ECU", "sensor", "wiring harness", "relay"],
                "Шасси": ["brake disc", "subframe", "steering rack", "damper"],
                "Логистика": ["pallet", "returnable container", "label", "barcode"],
            }
            for subsystem, parts in systems.items():
                part = rng.choice(parts)
                options = list(systems.keys()); rng.shuffle(options)
                items.append({"kind": "bom", "prompt": "К какой подсистеме относится компонент?", "term": part, "options": options})
                answers.append(options.index(subsystem))
            return items, answers

        if game_type == "spec_check":
            checks = [("Gap", 3.0, 2.5, 3.5, 3.2), ("Flush", 0.0, -0.5, 0.5, 0.8), ("Torque", 45, 43, 47, 44), ("Film thickness", 110, 95, 125, 132), ("Pressure", 2.0, 1.8, 2.2, 2.1)]
            for name, nominal, low, high, actual in checks:
                correct = "В допуске" if low <= actual <= high else "Вне допуска"
                options = ["В допуске", "Вне допуска", "Недостаточно данных"]; rng.shuffle(options)
                items.append({"kind": "spec", "prompt": f"{name}: допуск {low:g}–{high:g}, факт {actual:g}", "nominal": nominal, "actual": actual, "options": options})
                answers.append(options.index(correct))
            return items, answers

        if game_type == "rapid_recall":
            for row in selected:
                item, answer = _term_choice(row, pool, rng, prompt="10 секунд: выберите перевод")
                item["kind"] = "rapid"
                item["seconds"] = 10
                items.append(item); answers.append(answer)
            return items, answers

        if game_type == "memory_pairs":
            for row in selected:
                distractors = rng.sample([candidate for candidate in pool if candidate["id"] != row["id"]], 3)
                cards = [row["translation"], *[candidate["translation"] for candidate in distractors]]
                rng.shuffle(cards)
                items.append({"kind": "memory", "prompt": "Откройте карточку-пару", "term": row["term"], "cards": cards, "pronunciation": row.get("pronunciation", "")})
                answers.append(cards.index(row["translation"]))
            return items, answers

        if game_type == "odd_one_out":
            by_topic: dict[str, list[dict[str, Any]]] = {}
            for row in pool:
                by_topic.setdefault(str(row.get("topic", "")), []).append(row)
            usable = [rows for rows in by_topic.values() if len(rows) >= 3]
            if not usable:
                usable = [pool]
            for _ in range(MAX_GAME_ANSWERS):
                same = rng.choice(usable)
                same_sample = rng.sample(same, min(3, len(same)))
                other_pool = [row for row in pool if row not in same]
                odd = rng.choice(other_pool or pool)
                values = same_sample + [odd]
                rng.shuffle(values)
                items.append({"kind": "odd", "prompt": "Какой термин выбивается из группы?", "options": [row["term"] for row in values], "hint": same_sample[0].get("topic", "")})
                answers.append(values.index(odd))
            return items, answers

        if game_type == "dialogue_choice":
            for dialogue in DIALOGUES:
                options = list(dialogue["zh" if language == "chinese" else "en"])
                correct_value = options[dialogue["answer"]]
                rng.shuffle(options)
                items.append({"kind": "dialogue", "prompt": dialogue["ru"], "options": options})
                answers.append(options.index(correct_value))
            return items, answers

        if game_type == "shift_incident":
            for incident in SHIFT_INCIDENTS:
                options = list(incident["zh" if language == "chinese" else "en"])
                correct_value = options[incident["answer"]]
                rng.shuffle(options)
                items.append({"kind": "incident", "prompt": incident["ru"], "options": options})
                answers.append(options.index(correct_value))
            return items, answers

        raise HTTPException(404, "Неизвестная игра")

    def start_game(game_type: str, language: str, topic: str, user: Any, db: Session) -> dict[str, Any]:
        language = validate_language(language)
        require_feature(db, user.id, "games")
        if game_type not in GAME_TYPES:
            raise HTTPException(404, "Неизвестная игра")
        consume_daily_quota(db, user.id, "game_starts", int(game_daily_cap))
        pool = game_pool(language, topic, db)
        if len(pool) < 6:
            raise HTTPException(400, "Недостаточно терминов для игры")

        public_id = secrets.token_urlsafe(18)
        rng = random.Random(secrets.randbits(64))
        items, answers = _generate_items(game_type, language, pool, rng)
        items = items[:MAX_GAME_ANSWERS]
        answers = answers[:MAX_GAME_ANSWERS]
        if not items or len(items) != len(answers):
            raise HTTPException(500, "Не удалось сформировать игровую сессию")

        db.add(game_session_model(
            public_id=public_id,
            user_id=user.id,
            game_type=game_type,
            language=language,
            topic=topic,
            payload_json=json.dumps({"items": items, "answers": answers}, ensure_ascii=False),
            total=len(items),
        ))
        db.commit()
        return {"session_id": public_id, "game_type": game_type, "language": language, "topic": topic, "items": items, "total": len(items)}

    def finish_game(session_id: str, payload: Any, request: Any, user: Any, db: Session) -> dict[str, Any]:
        rate_limit(request, "game_finish", 120, 60)
        session = db.scalar(select(game_session_model).where(
            game_session_model.public_id == session_id,
            game_session_model.user_id == user.id,
        ))
        if not session:
            raise HTTPException(404, "Игровая сессия не найдена")
        if session.status == "completed":
            return {"ok": True, "duplicate": True, "score": session.score, "total": session.total, "profile": gamification_view(db, user.id)}

        data = json.loads(session.payload_json)
        score = score_game_answers(data.get("answers", []), payload.answers)
        session.status = "completed"
        session.score = score
        session.completed_at = datetime.now(timezone.utc)
        raw = 10 + score * 3 + (10 if score == session.total else 0)
        award = award_xp(
            db, user.id, f"game:{session.game_type}", session.topic or session.game_type, raw,
            language=session.language, topic=session.topic,
            idempotency_key=f"game:{user.id}:{session.public_id}",
            metadata={"score": score, "total": session.total}, anti_farm=True,
        )
        db.commit()
        return {"ok": True, "score": score, "total": session.total, **award}

    def question_attempt(payload: Any, user: Any, db: Session) -> dict[str, Any]:
        language = validate_language(payload.language)
        if payload.session_id:
            existing = db.scalar(select(question_attempt_model).where(
                question_attempt_model.user_id == user.id,
                question_attempt_model.session_id == payload.session_id,
                question_attempt_model.question_id == payload.question_id,
            ))
            if existing:
                return {"ok": True, "duplicate": True}
        consume_daily_quota(db, user.id, "practice_submissions", int(practice_daily_cap))
        selected_hash = hashlib.sha256(payload.selected.encode("utf-8")).hexdigest() if payload.selected else ""
        db.add(question_attempt_model(
            user_id=user.id,
            session_id=payload.session_id,
            question_id=payload.question_id,
            term_id=payload.term_id,
            language=language,
            topic=payload.topic,
            kind=payload.kind,
            correct=payload.correct,
            response_ms=payload.response_ms,
            selected_hash=selected_hash,
        ))
        if payload.term_id:
            term = next((row for row in terms_for(language, db) if row["id"] == payload.term_id), None)
            if term:
                card = get_or_create_srs_card(db, user.id, language, payload.term_id, payload.topic or term.get("topic", ""))
                schedule_srs(card, 5 if payload.correct else 1)
        db.commit()
        return {"ok": True}

    for name, fn in {
        "save_practice_result": save_practice_result,
        "start_game": start_game,
        "finish_game": finish_game,
        "question_attempt": question_attempt,
    }.items():
        fn.__name__ = name
        fn.__qualname__ = name

    return PracticeGameWorkflowBindings(
        save_practice_result=save_practice_result,
        start_game=start_game,
        finish_game=finish_game,
        question_attempt=question_attempt,
    )


__all__ = [
    "PracticeGameWorkflowBindings",
    "MAX_GAME_ANSWERS",
    "GAME_TYPES",
    "build_practice_game_workflows",
    "practice_raw_xp",
    "chunk_chinese",
    "score_game_answers",
]
