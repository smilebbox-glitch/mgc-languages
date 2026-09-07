from __future__ import annotations

from typing import Any, Callable, Mapping

from fastapi import APIRouter, Depends, File, Query, Request, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session


class CustomTermPayload(BaseModel):
    language: str
    shop: str = Field(default="", max_length=160)
    topic: str = Field(min_length=1, max_length=160)
    subtopic: str = Field(default="", max_length=160)
    level: str = Field(default="A1", pattern="^(A1|A2|B1|B2|C1)$")
    term: str = Field(min_length=1, max_length=500)
    pronunciation: str = Field(default="", max_length=500)
    reading: str = Field(default="", max_length=500)
    translation: str = Field(min_length=1, max_length=500)
    example: str = Field(default="", max_length=3000)
    example_translation: str = Field(default="", max_length=3000)
    tags: str = Field(default="", max_length=1000)
    status: str = Field(default="published", pattern="^(draft|review|published|archived)$")


class TermReviewPayload(BaseModel):
    note: str = Field(default="", max_length=2000)


TERMINOLOGY_ADMIN_HANDLER_NAMES = (
    "language_topics",
    "language_terms",
    "admin_terms",
    "admin_create_term",
    "admin_update_term",
    "admin_delete_term",
    "admin_term_revisions",
    "admin_term_submit_review",
    "admin_term_approve",
    "admin_term_reject",
    "admin_term_rollback",
    "admin_import_terms",
    "admin_taxonomy",
)


def build_terminology_admin_router(
    *,
    db_session: Callable[..., Any],
    current_user: Callable[..., Any],
    require_roles: Callable[..., Callable[..., Any]],
    handlers: Mapping[str, Callable[..., Any]],
) -> APIRouter:
    """Build public terminology and corporate terminology-admin HTTP routes."""
    missing = [name for name in TERMINOLOGY_ADMIN_HANDLER_NAMES if not callable(handlers.get(name))]
    if missing:
        raise RuntimeError(f"terminology/admin router handlers are incomplete: {missing}")

    language_topics_handler = handlers["language_topics"]
    language_terms_handler = handlers["language_terms"]
    admin_terms_handler = handlers["admin_terms"]
    admin_create_term_handler = handlers["admin_create_term"]
    admin_update_term_handler = handlers["admin_update_term"]
    admin_delete_term_handler = handlers["admin_delete_term"]
    admin_term_revisions_handler = handlers["admin_term_revisions"]
    admin_term_submit_review_handler = handlers["admin_term_submit_review"]
    admin_term_approve_handler = handlers["admin_term_approve"]
    admin_term_reject_handler = handlers["admin_term_reject"]
    admin_term_rollback_handler = handlers["admin_term_rollback"]
    admin_import_terms_handler = handlers["admin_import_terms"]
    admin_taxonomy_handler = handlers["admin_taxonomy"]

    router = APIRouter()

    @router.get("/api/language/{language}/topics")
    def language_topics(
        language: str,
        user: Any = Depends(current_user),
        db: Session = Depends(db_session),
    ):
        return language_topics_handler(language=language, user=user, db=db)

    @router.get("/api/language/{language}/terms")
    def language_terms(
        language: str,
        topic: str | None = None,
        level: str | None = None,
        offset: int = Query(default=0, ge=0),
        limit: int = Query(default=60, ge=1, le=500),
        user: Any = Depends(current_user),
        db: Session = Depends(db_session),
    ):
        return language_terms_handler(
            language=language,
            topic=topic,
            level=level,
            offset=offset,
            limit=limit,
            user=user,
            db=db,
        )

    @router.get("/api/admin/terms")
    def admin_terms(
        language: str | None = Query(default=None),
        status: str | None = Query(default=None),
        user: Any = Depends(require_roles("admin", "editor")),
        db: Session = Depends(db_session),
    ):
        return admin_terms_handler(language=language, status=status, user=user, db=db)

    @router.post("/api/admin/terms")
    def admin_create_term(
        payload: CustomTermPayload,
        request: Request,
        user: Any = Depends(require_roles("admin", "editor")),
        db: Session = Depends(db_session),
    ):
        return admin_create_term_handler(payload=payload, request=request, user=user, db=db)

    @router.patch("/api/admin/terms/{term_id}")
    def admin_update_term(
        term_id: int,
        payload: CustomTermPayload,
        request: Request,
        user: Any = Depends(require_roles("admin", "editor")),
        db: Session = Depends(db_session),
    ):
        return admin_update_term_handler(term_id=term_id, payload=payload, request=request, user=user, db=db)

    @router.delete("/api/admin/terms/{term_id}")
    def admin_delete_term(
        term_id: int,
        request: Request,
        user: Any = Depends(require_roles("admin")),
        db: Session = Depends(db_session),
    ):
        return admin_delete_term_handler(term_id=term_id, request=request, user=user, db=db)

    @router.get("/api/admin/terms/{term_id}/revisions")
    def admin_term_revisions(
        term_id: int,
        user: Any = Depends(require_roles("admin", "editor")),
        db: Session = Depends(db_session),
    ):
        return admin_term_revisions_handler(term_id=term_id, user=user, db=db)

    @router.post("/api/admin/terms/{term_id}/submit-review")
    def admin_term_submit_review(
        term_id: int,
        request: Request,
        user: Any = Depends(require_roles("admin", "editor")),
        db: Session = Depends(db_session),
    ):
        return admin_term_submit_review_handler(term_id=term_id, request=request, user=user, db=db)

    @router.post("/api/admin/terms/{term_id}/approve")
    def admin_term_approve(
        term_id: int,
        payload: TermReviewPayload,
        request: Request,
        user: Any = Depends(require_roles("admin")),
        db: Session = Depends(db_session),
    ):
        return admin_term_approve_handler(term_id=term_id, payload=payload, request=request, user=user, db=db)

    @router.post("/api/admin/terms/{term_id}/reject")
    def admin_term_reject(
        term_id: int,
        payload: TermReviewPayload,
        request: Request,
        user: Any = Depends(require_roles("admin")),
        db: Session = Depends(db_session),
    ):
        return admin_term_reject_handler(term_id=term_id, payload=payload, request=request, user=user, db=db)

    @router.post("/api/admin/terms/{term_id}/rollback/{revision_no}")
    def admin_term_rollback(
        term_id: int,
        revision_no: int,
        request: Request,
        user: Any = Depends(require_roles("admin")),
        db: Session = Depends(db_session),
    ):
        return admin_term_rollback_handler(
            term_id=term_id,
            revision_no=revision_no,
            request=request,
            user=user,
            db=db,
        )

    @router.post("/api/admin/terms/import")
    def admin_import_terms(
        request: Request,
        file: UploadFile = File(...),
        default_language: str = Query(default="chinese"),
        user: Any = Depends(require_roles("admin", "editor")),
        db: Session = Depends(db_session),
    ):
        return admin_import_terms_handler(
            request=request,
            file=file,
            default_language=default_language,
            user=user,
            db=db,
        )

    @router.get("/api/admin/taxonomy")
    def admin_taxonomy(
        user: Any = Depends(require_roles("admin", "editor", "manager")),
        db: Session = Depends(db_session),
    ):
        return admin_taxonomy_handler(user=user, db=db)

    return router


__all__ = [
    "CustomTermPayload",
    "TermReviewPayload",
    "TERMINOLOGY_ADMIN_HANDLER_NAMES",
    "build_terminology_admin_router",
]
