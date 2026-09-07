from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from fastapi.routing import APIRoute  # noqa: E402
from pydantic import ValidationError  # noqa: E402
from mgc.routers.terminology_admin import (  # noqa: E402
    CustomTermPayload,
    TermReviewPayload,
    build_terminology_admin_router,
)

assert "mgc.legacy_app" not in sys.modules
assert "app" not in sys.modules


def dependency():
    yield object()


def require_roles(*roles: str):
    def role_dependency():
        return object()
    role_dependency.required_roles = roles
    return role_dependency


def handler(**kwargs):
    return {"ok": True}


handler_names = (
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
router = build_terminology_admin_router(
    db_session=dependency,
    current_user=dependency,
    require_roles=require_roles,
    handlers={name: handler for name in handler_names},
)

expected = {
    ("GET", "/api/language/{language}/topics"),
    ("GET", "/api/language/{language}/terms"),
    ("GET", "/api/admin/terms"),
    ("POST", "/api/admin/terms"),
    ("PATCH", "/api/admin/terms/{term_id}"),
    ("DELETE", "/api/admin/terms/{term_id}"),
    ("GET", "/api/admin/terms/{term_id}/revisions"),
    ("POST", "/api/admin/terms/{term_id}/submit-review"),
    ("POST", "/api/admin/terms/{term_id}/approve"),
    ("POST", "/api/admin/terms/{term_id}/reject"),
    ("POST", "/api/admin/terms/{term_id}/rollback/{revision_no}"),
    ("POST", "/api/admin/terms/import"),
    ("GET", "/api/admin/taxonomy"),
}
actual = set()
for route in router.routes:
    if not isinstance(route, APIRoute):
        continue
    methods = (route.methods or set()) - {"HEAD", "OPTIONS"}
    assert len(methods) == 1
    actual.add((next(iter(methods)), route.path))
    assert route.endpoint.__module__ == "mgc.routers.terminology_admin"
assert actual == expected

payload = CustomTermPayload(
    language="chinese",
    topic="Сварка кузова",
    term="定位销",
    translation="Установочный штифт",
)
assert payload.level == "A1"
assert payload.status == "published"
assert TermReviewPayload().note == ""

try:
    CustomTermPayload(language="chinese", topic="", term="x", translation="y")
    raise AssertionError("empty topic accepted")
except ValidationError:
    pass

try:
    CustomTermPayload(
        language="chinese",
        topic="Сварка кузова",
        term="x",
        translation="y",
        status="invalid",
    )
    raise AssertionError("invalid status accepted")
except ValidationError:
    pass

assert "mgc.legacy_app" not in sys.modules
assert "app" not in sys.modules
print("OK: v5.8.5 terminology/admin router builds independently with exact thirteen-route contract")
