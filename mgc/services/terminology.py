from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Callable

from sqlalchemy import func, select
from sqlalchemy.orm import Session


@dataclass(frozen=True)
class TerminologyServiceBindings:
    custom_term_view: Callable[[Any], dict[str, Any]]
    terms_for: Callable[[str, Session], list[dict[str, Any]]]
    term_by_id: Callable[[str, str, Session], dict[str, Any] | None]
    term_snapshot: Callable[[Any], dict[str, Any]]
    record_term_revision: Callable[[Session, Any, int | None, str], Any]
    admin_term_response: Callable[[Any], dict[str, Any]]


def build_terminology_service(
    *,
    custom_term_model: Any,
    term_revision_model: Any,
    base_terms: dict[str, list[dict[str, Any]]],
    english_pronunciation: Callable[[str], dict[str, str]],
    pinyin_to_ru_approx: Callable[[str], str],
) -> TerminologyServiceBindings:
    """Build terminology query/revision services without importing app.py."""

    def custom_term_view(row: Any) -> dict[str, Any]:
        return {
            "id": row.public_id,
            "custom": True,
            "language": row.language,
            "shop": row.shop,
            "topic": row.topic,
            "category": row.shop or row.topic,
            "subcategory": row.subtopic or row.topic,
            "level": row.level,
            "term": row.term,
            "pronunciation": row.pronunciation
            or (
                english_pronunciation(row.term)["ipa"]
                if row.language == "english"
                else ""
            ),
            "reading": row.reading
            or (
                english_pronunciation(row.term)["reading"]
                if row.language == "english"
                else pinyin_to_ru_approx(row.pronunciation)
            ),
            "translation": row.translation,
            "example": row.example or row.term,
            "example_pronunciation": row.pronunciation,
            "example_translation": row.example_translation or row.translation,
            "note": row.tags,
            "status": row.status,
            "tags": row.tags,
            "source_type": row.source_type,
            "source_ref": row.source_ref,
        }

    custom_term_view.__name__ = "custom_term_view"
    custom_term_view.__qualname__ = "custom_term_view"

    def terms_for(language: str, db: Session) -> list[dict[str, Any]]:
        rows = list(base_terms[language])
        custom = db.scalars(
            select(custom_term_model)
            .where(
                custom_term_model.language == language,
                custom_term_model.status == "published",
            )
            .order_by(custom_term_model.id)
        ).all()
        rows.extend(custom_term_view(row) for row in custom)
        return rows

    terms_for.__name__ = "terms_for"
    terms_for.__qualname__ = "terms_for"

    def term_by_id(
        language: str,
        term_id: str,
        db: Session,
    ) -> dict[str, Any] | None:
        return next(
            (row for row in terms_for(language, db) if row["id"] == term_id),
            None,
        )

    term_by_id.__name__ = "term_by_id"
    term_by_id.__qualname__ = "term_by_id"

    def term_snapshot(row: Any) -> dict[str, Any]:
        return {
            key: getattr(row, key)
            for key in (
                "language",
                "shop",
                "topic",
                "subtopic",
                "level",
                "term",
                "pronunciation",
                "reading",
                "translation",
                "example",
                "example_translation",
                "tags",
                "source_type",
                "source_ref",
                "status",
            )
        }

    term_snapshot.__name__ = "_term_snapshot"
    term_snapshot.__qualname__ = "_term_snapshot"

    def record_term_revision(
        db: Session,
        row: Any,
        actor_user_id: int | None,
        action: str,
    ) -> Any:
        last_no = db.scalar(
            select(func.max(term_revision_model.revision_no)).where(
                term_revision_model.term_id == row.id
            )
        ) or 0
        revision = term_revision_model(
            term_id=row.id,
            revision_no=int(last_no) + 1,
            action=action,
            snapshot_json=json.dumps(
                term_snapshot(row),
                ensure_ascii=False,
                sort_keys=True,
            ),
            actor_user_id=actor_user_id,
        )
        db.add(revision)
        db.flush()
        return revision

    record_term_revision.__name__ = "record_term_revision"
    record_term_revision.__qualname__ = "record_term_revision"

    def admin_term_response(row: Any) -> dict[str, Any]:
        return {
            **custom_term_view(row),
            "db_id": row.id,
            "created_at": row.created_at.isoformat(),
            "updated_at": row.updated_at.isoformat(),
        }

    admin_term_response.__name__ = "admin_term_response"
    admin_term_response.__qualname__ = "admin_term_response"

    return TerminologyServiceBindings(
        custom_term_view=custom_term_view,
        terms_for=terms_for,
        term_by_id=term_by_id,
        term_snapshot=term_snapshot,
        record_term_revision=record_term_revision,
        admin_term_response=admin_term_response,
    )


__all__ = ["TerminologyServiceBindings", "build_terminology_service"]
