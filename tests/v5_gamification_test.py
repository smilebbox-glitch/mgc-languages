from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
DB = Path(tempfile.gettempdir()) / "mgc_languages_v5_test.db"
try:
    DB.unlink()
except FileNotFoundError:
    pass
os.environ["DATABASE_URL"] = f"sqlite:///{DB}"
os.environ["MGC_ADMIN_USERNAME"] = "admin"
os.environ["MGC_ADMIN_PASSWORD"] = "AdminPass123"

from fastapi.testclient import TestClient  # noqa: E402
import app  # noqa: E402

client = TestClient(app.app)

def csrf_headers(c):
    token = c.cookies.get("mgc_csrf")
    return {"X-CSRF-Token": token} if token else {}

r = client.post("/api/register", json={"username": "pilotuser", "password": "PilotPass123", "display_name": "Pilot User"})
assert r.status_code == 200, r.text

profile = client.get("/api/gamification/me").json()
assert profile["level"] == 1 and profile["lifetime_xp"] == 0

r = client.post("/api/practice/result", headers=csrf_headers(client), json={
    "session_id": "quiz-test-001", "kind": "quiz", "language": "chinese",
    "topic": "Сварка кузова", "score": 5, "total": 5,
})
assert r.status_code == 200, r.text
assert r.json()["awarded"] == 40
assert r.json()["profile"]["lifetime_xp"] == 40

quiz = client.get("/api/language/chinese/quiz?topic=Сварка%20кузова&level=A1&count=5").json()
question = quiz["questions"][0]
r = client.post("/api/gamification/spend", headers=csrf_headers(client), json={
    "reward_id": "hint_small", "language": "chinese",
    "context": {"term_id": question["id"], "options": question["options"]},
})
assert r.status_code == 200, r.text
assert r.json()["spent"] == 10
assert r.json()["profile"]["lifetime_xp"] == 40
assert r.json()["profile"]["spendable_xp"] == 30

levels = client.get("/api/gamification/levels").json()
assert len(levels) == 100
assert levels[0]["required_xp"] == 0
assert levels[-1]["level"] == 100 and levels[-1]["title"] == "Легенда"

settings = client.put("/api/notifications/settings", headers=csrf_headers(client), json={
    "mode": "normal", "window_start": "09:00", "window_end": "19:00", "browser_enabled": False,
})
assert settings.status_code == 200

admin = TestClient(app.app)
r = admin.post("/api/login", json={"username": "admin", "password": "AdminPass123"})
assert r.status_code == 200 and r.json()["user"]["role"] == "admin"

r = admin.post("/api/admin/terms", headers=csrf_headers(admin), json={
    "language": "chinese", "shop": "Сварка", "topic": "Сварка кузова", "subtopic": "Robot",
    "level": "A2", "term": "焊枪", "pronunciation": "hànqiāng", "translation": "сварочные клещи",
    "example": "请检查焊枪。", "example_translation": "Проверьте сварочные клещи.", "tags": "pilot", "status": "published",
})
assert r.status_code == 200, r.text
terms = admin.get("/api/language/chinese/terms?topic=Сварка%20кузова&limit=500").json()["items"]
assert any(row["term"] == "焊枪" for row in terms)

analytics = admin.get("/api/admin/analytics")
assert analytics.status_code == 200 and analytics.json()["users"] == 2

print("OK: v5 XP economy, 100 levels, spending, notifications, admin content and analytics")
