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
            if list(answer) == correct:
                score += 1
        elif answer == correct:
            score += 1
    return score


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
        existing = db.scalar(
            select(practice_result_model).where(
                practice_result_model.session_id == payload.session_id
            )
        )
        if existing:
            return {
                "ok": True,
                "duplicate": True,
                "profile": gamification_view(db, user.id),
            }
        consume_daily_quota(
            db,
            user.id,
            "practice_submissions",
            int(practice_daily_cap),
        )
        if payload.score > payload.total:
            raise HTTPException(400, "Некорректный результат")
        db.add(
            practice_result_model(
                user_id=user.id,
                session_id=payload.session_id,
                kind=payload.kind,
                language=language,
                topic=payload.topic,
                score=payload.score,
                total=payload.total,
            )
        )
        raw = practice_raw_xp(payload.kind, payload.score, payload.total)
        award = award_xp(
            db,
            user.id,
            payload.kind,
            payload.topic or payload.session_id,
            raw,
            language=language,
            topic=payload.topic,
            idempotency_key=f"practice:{user.id}:{payload.session_id}",
            metadata={"score": payload.score, "total": payload.total},
            anti_farm=True,
        )
        db.commit()
        return {"ok": True, "duplicate": False, **award}

    def start_game(
        game_type: str,
        language: str,
        topic: str,
        user: Any,
        db: Session,
    ) -> dict[str, Any]:
        language = validate_language(language)
        require_feature(db, user.id, "games")
        if game_type not in {"match", "listening", "mistake", "phrase"}:
            raise HTTPException(404, "Неизвестная игра")
        consume_daily_quota(db, user.id, "game_starts", int(game_daily_cap))
        pool = game_pool(language, topic, db)
        if len(pool) < 6:
            raise HTTPException(400, "Недостаточно терминов для игры")

        public_id = secrets.token_urlsafe(18)
        rng = random.Random(secrets.randbits(64))
        selected = rng.sample(pool, min(MAX_GAME_ANSWERS, len(pool)))
        items: list[dict[str, Any]] = []
        answers: list[Any] = []

        if game_type == "match":
            items = [
                {
                    "id": row["id"],
                    "term": row["term"],
                    "pronunciation": row.get("pronunciation", ""),
                    "reading": row.get("reading", ""),
                    "translation": row["translation"],
                }
                for row in selected
            ]
            answers = [row["id"] for row in selected]
        elif game_type == "listening":
            for row in selected:
                distractors = rng.sample(
                    [candidate for candidate in pool if candidate["id"] != row["id"]],
                    3,
                )
                options = [
                    row["translation"],
                    *[candidate["translation"] for candidate in distractors],
                ]
                rng.shuffle(options)
                items.append(
                    {
                        "id": row["id"],
                        "audio_text": row["term"],
                        "pronunciation": row.get("pronunciation", ""),
                        "reading": row.get("reading", ""),
                        "options": options,
                    }
                )
                answers.append(options.index(row["translation"]))
        elif game_type == "mistake":
            for row in selected:
                distractors = rng.sample(
                    [candidate for candidate in pool if candidate["id"] != row["id"]],
                    3,
                )
                options = [
                    row["translation"],
                    *[candidate["translation"] for candidate in distractors],
                ]
                rng.shuffle(options)
                items.append(
                    {
                        "id": row["id"],
                        "term": row["term"],
                        "pronunciation": row.get("pronunciation", ""),
                        "reading": row.get("reading", ""),
                        "options": options,
                    }
                )
                answers.append(options.index(row["translation"]))
        else:
            phrase_rows = [
                row for row in pool if len((row.get("example") or "").strip()) >= 8
            ]
            phrase_pool = phrase_rows or pool
            selected = rng.sample(phrase_pool, min(MAX_GAME_ANSWERS, len(phrase_pool)))
            for row in selected:
                phrase = row.get("example") or row["term"]
                tokens = phrase.split() if language == "english" else chunk_chinese(phrase)
                shuffled = list(tokens)
                rng.shuffle(shuffled)
                items.append(
                    {
                        "id": row["id"],
                        "translation": row.get("example_translation") or row["translation"],
                        "tokens": shuffled,
                    }
                )
                answers.append(tokens)

        db.add(
            game_session_model(
                public_id=public_id,
                user_id=user.id,
                game_type=game_type,
                language=language,
                topic=topic,
                payload_json=json.dumps(
                    {"items": items, "answers": answers},
                    ensure_ascii=False,
                ),
                total=len(items),
            )
        )
        db.commit()
        return {
            "session_id": public_id,
            "game_type": game_type,
            "language": language,
            "topic": topic,
            "items": items,
            "total": len(items),
        }

    def finish_game(
        session_id: str,
        payload: Any,
        request: Any,
        user: Any,
        db: Session,
    ) -> dict[str, Any]:
        rate_limit(request, "game_finish", 120, 60)
        session = db.scalar(
            select(game_session_model).where(
                game_session_model.public_id == session_id,
                game_session_model.user_id == user.id,
            )
        )
        if not session:
            raise HTTPException(404, "Игровая сессия не найдена")
        if session.status == "completed":
            return {
                "ok": True,
                "duplicate": True,
                "score": session.score,
                "total": session.total,
                "profile": gamification_view(db, user.id),
            }

        data = json.loads(session.payload_json)
        score = score_game_answers(data.get("answers", []), payload.answers)
        session.status = "completed"
        session.score = score
        session.completed_at = datetime.now(timezone.utc)
        raw = 10 + score * 3 + (10 if score == session.total else 0)
        award = award_xp(
            db,
            user.id,
            f"game:{session.game_type}",
            session.topic or session.game_type,
            raw,
            language=session.language,
            topic=session.topic,
            idempotency_key=f"game:{user.id}:{session.public_id}",
            metadata={"score": score, "total": session.total},
            anti_farm=True,
        )
        db.commit()
        return {"ok": True, "score": score, "total": session.total, **award}

    def question_attempt(payload: Any, user: Any, db: Session) -> dict[str, Any]:
        language = validate_language(payload.language)
        if payload.session_id:
            existing = db.scalar(
                select(question_attempt_model).where(
                    question_attempt_model.user_id == user.id,
                    question_attempt_model.session_id == payload.session_id,
                    question_attempt_model.question_id == payload.question_id,
                )
            )
            if existing:
                return {"ok": True, "duplicate": True}

        consume_daily_quota(
            db,
            user.id,
            "practice_submissions",
            int(practice_daily_cap),
        )
        selected_hash = (
            hashlib.sha256(payload.selected.encode("utf-8")).hexdigest()
            if payload.selected
            else ""
        )
        db.add(
            question_attempt_model(
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
            )
        )
        if payload.term_id:
            term = next(
                (row for row in terms_for(language, db) if row["id"] == payload.term_id),
                None,
            )
            if term:
                card = get_or_create_srs_card(
                    db,
                    user.id,
                    language,
                    payload.term_id,
                    payload.topic or term.get("topic", ""),
                )
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
    "build_practice_game_workflows",
    "practice_raw_xp",
    "chunk_chinese",
    "score_game_answers",
]
