from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB = Path(tempfile.gettempdir()) / "mgc_languages_v585_terminology_admin.db"
try:
    DB.unlink()
except FileNotFoundError:
    pass

os.environ.update({
    "DATABASE_URL": f"sqlite:///{DB}",
    "AUTO_CREATE_SCHEMA": "true",
    "APP_ENV": "pilot",
    "AUTH_MODE": "local",
    "REGISTRATION_ENABLED": "true",
    "TRUSTED_HOSTS": "testserver,localhost,127.0.0.1",
    "MGC_ADMIN_USERNAME": "v585admin",
    "MGC_ADMIN_PASSWORD": "V585AdminPassword!123456",
    "OIDC_STATE_SECRET": "v585-terminology-runtime-secret-32-bytes-001",
    "TTS_LEGACY_GET_ENABLED": "false",
    "RLS_ENABLED": "true",
    "METRICS_TOKEN": "v585metrics",
    "TTS_CACHE_PERSISTENCE": "ephemeral",
})
sys.path.insert(0, str(ROOT))

from fastapi.routing import APIRoute  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
import app  # noqa: E402
import asgi  # noqa: E402

assert asgi.app is app.app
report = asgi.TERMINOLOGY_ADMIN_ROUTER_BINDING_REPORT
assert report.ok
assert report.route_count == 13
assert report.public_route_count == 2
assert report.admin_term_route_count == 10
assert report.taxonomy_route_count == 1
assert report.route_names_preserved
assert report.response_classes_preserved
assert report.root_mount_order_preserved
assert report.router_module_owned
assert report.auth_core_bound
assert report.terminology_service_bound
assert report.governance_core_bound

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
for method, path in expected:
    routes = [
        route for route in asgi.app.routes
        if isinstance(route, APIRoute)
        and route.path == path
        and method in (route.methods or set())
    ]
    assert len(routes) == 1, (method, path, len(routes))
    assert routes[0].endpoint.__module__ == "mgc.routers.terminology_admin"

user_client = TestClient(asgi.app)
registered = user_client.post(
    "/api/register",
    json={
        "username": "v585user",
        "password": "StrongPass123!",
        "display_name": "Terminology User",
    },
)
assert registered.status_code == 200, registered.text

public_terms = user_client.get("/api/language/chinese/terms", params={"limit": 5})
assert public_terms.status_code == 200, public_terms.text
assert public_terms.json()["total"] >= 5
public_topics = user_client.get("/api/language/chinese/topics")
assert public_topics.status_code == 200, public_topics.text
assert public_topics.json()
forbidden = user_client.get("/api/admin/terms")
assert forbidden.status_code == 403, forbidden.text

admin_client = TestClient(asgi.app)
login = admin_client.post(
    "/api/login",
    json={"username": "v585admin", "password": "V585AdminPassword!123456"},
)
assert login.status_code == 200, login.text
headers = {"X-CSRF-Token": admin_client.cookies.get("mgc_csrf")}

taxonomy = admin_client.get("/api/admin/taxonomy")
assert taxonomy.status_code == 200, taxonomy.text
assert "chinese" in taxonomy.json()["languages"]
assert "english" in taxonomy.json()["languages"]

topic = "v5.8.5 Router Terminology"
payload = {
    "language": "chinese",
    "shop": "R&D / Engineering",
    "topic": topic,
    "subtopic": "Fixture",
    "level": "A2",
    "term": "定位销",
    "pronunciation": "dìng wèi xiāo",
    "reading": "дин вэй сяо",
    "translation": "Установочный штифт",
    "example": "检查定位销位置。",
    "example_translation": "Проверьте положение установочного штифта.",
    "tags": "fixture,quality",
    "status": "draft",
}
created = admin_client.post("/api/admin/terms", headers=headers, json=payload)
assert created.status_code == 200, created.text
created_data = created.json()
term_id = created_data["db_id"]
public_id = created_data["id"]
assert created_data["status"] == "draft"
assert public_id.startswith("custom-")

listed = admin_client.get("/api/admin/terms", params={"language": "chinese", "status": "draft"})
assert listed.status_code == 200, listed.text
assert any(row["db_id"] == term_id for row in listed.json())

submitted = admin_client.post(
    f"/api/admin/terms/{term_id}/submit-review",
    headers=headers,
)
assert submitted.status_code == 200, submitted.text
assert submitted.json()["status"] == "review"

approved = admin_client.post(
    f"/api/admin/terms/{term_id}/approve",
    headers=headers,
    json={"note": "v5.8.5 runtime approval"},
)
assert approved.status_code == 200, approved.text
assert approved.json()["status"] == "published"

visible = user_client.get(
    "/api/language/chinese/terms",
    params={"topic": topic, "limit": 20},
)
assert visible.status_code == 200, visible.text
visible_items = visible.json()["items"]
assert len(visible_items) == 1
assert visible_items[0]["id"] == public_id
assert visible_items[0]["translation"] == "Установочный штифт"

topics_after = user_client.get("/api/language/chinese/topics")
assert topics_after.status_code == 200, topics_after.text
assert any(row["label"] == topic for row in topics_after.json())

revisions = admin_client.get(f"/api/admin/terms/{term_id}/revisions")
assert revisions.status_code == 200, revisions.text
revision_data = revisions.json()
assert revision_data["term"]["id"] == public_id
assert len(revision_data["revisions"]) >= 3
assert any(row["decision"] == "approved" for row in revision_data["reviews"])

updated_payload = dict(payload)
updated_payload["translation"] = "Позиционирующий штифт"
updated_payload["status"] = "review"
updated = admin_client.patch(
    f"/api/admin/terms/{term_id}",
    headers=headers,
    json=updated_payload,
)
assert updated.status_code == 200, updated.text
assert updated.json()["translation"] == "Позиционирующий штифт"
assert updated.json()["status"] == "review"

rejected = admin_client.post(
    f"/api/admin/terms/{term_id}/reject",
    headers=headers,
    json={"note": "needs terminology review"},
)
assert rejected.status_code == 200, rejected.text
assert rejected.json()["status"] == "draft"

revisions_after_reject = admin_client.get(f"/api/admin/terms/{term_id}/revisions")
assert revisions_after_reject.status_code == 200
rollback_revision = next(
    row["revision_no"]
    for row in revisions_after_reject.json()["revisions"]
    if row["snapshot"]["translation"] == "Установочный штифт"
)
rolled = admin_client.post(
    f"/api/admin/terms/{term_id}/rollback/{rollback_revision}",
    headers=headers,
)
assert rolled.status_code == 200, rolled.text
assert rolled.json()["translation"] == "Установочный штифт"

csv_content = (
    "language,shop,topic,level,term,translation,status\n"
    "english,R&D / Engineering,v5.8.5 Import,A1,locator pin,установочный штифт,review\n"
).encode("utf-8")
imported = admin_client.post(
    "/api/admin/terms/import",
    headers=headers,
    params={"default_language": "english"},
    files={"file": ("v585_terms.csv", csv_content, "text/csv")},
)
assert imported.status_code == 200, imported.text
assert imported.json()["created"] == 1
assert imported.json()["error_count"] == 0

import_rows = admin_client.get(
    "/api/admin/terms",
    params={"language": "english", "status": "review"},
)
assert import_rows.status_code == 200
assert any(row["topic"] == "v5.8.5 Import" for row in import_rows.json())

deleted = admin_client.delete(f"/api/admin/terms/{term_id}", headers=headers)
assert deleted.status_code == 200, deleted.text
assert deleted.json() == {"ok": True}

openapi = admin_client.get("/openapi.json")
assert openapi.status_code == 200
paths = openapi.json()["paths"]
for _method, path in expected:
    assert path in paths

print("OK: v5.8.5 ASGI terminology/admin router preserves RBAC, review lifecycle, revisions, import and public term visibility")
