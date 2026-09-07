from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB = Path(tempfile.gettempdir()) / "mgc_languages_v597_user_login_department.db"
try:
    DB.unlink()
except FileNotFoundError:
    pass

os.environ.update(
    {
        "DATABASE_URL": f"sqlite:///{DB}",
        "AUTO_CREATE_SCHEMA": "true",
        "APP_ENV": "development",
        "AUTH_MODE": "local",
        "REGISTRATION_ENABLED": "true",
        "TRUSTED_HOSTS": "testserver,localhost,127.0.0.1",
        "OIDC_STATE_SECRET": "v597-user-login-department-secret-32-bytes",
        "MGC_ADMIN_USERNAME": "admin",
        "MGC_ADMIN_PASSWORD": "V597AdminPass!123",
        "MGC_ADMIN_DISPLAY_NAME": "MGC Admin",
        "TTS_LEGACY_GET_ENABLED": "false",
        "TTS_CACHE_PERSISTENCE": "ephemeral",
    }
)
sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient  # noqa: E402
import asgi  # noqa: E402

client = TestClient(asgi.app)

registered = client.post(
    "/api/register",
    json={
        "username": "ivan.ivanov",
        "password": "StrongPass123!",
        "display_name": "Иван Иванов",
        "department": "R&D",
    },
)
assert registered.status_code == 200, registered.text
assert registered.json()["user"]["department"] == "R&D"
assert registered.json()["user"]["display_name"] == "Иван Иванов"

csrf = registered.cookies.get("mgc_csrf") or client.cookies.get("mgc_csrf")
assert csrf
logout = client.post("/api/logout", headers={"X-CSRF-Token": csrf})
assert logout.status_code == 200, logout.text

wrong_department = client.post(
    "/api/login",
    json={
        "username": "ivan.ivanov",
        "password": "StrongPass123!",
        "department": "IT",
    },
)
assert wrong_department.status_code == 401, wrong_department.text
assert "отдел" in wrong_department.json()["detail"].lower()

correct_department = client.post(
    "/api/login",
    json={
        "username": "ivan.ivanov",
        "password": "StrongPass123!",
        "department": "R&D",
    },
)
assert correct_department.status_code == 200, correct_department.text
assert correct_department.json()["user"]["department"] == "R&D"

# Backwards-compatible API clients may omit department; the browser UI requires it.
legacy_client = TestClient(asgi.app)
legacy_login = legacy_client.post(
    "/api/login",
    json={"username": "ivan.ivanov", "password": "StrongPass123!"},
)
assert legacy_login.status_code == 200, legacy_login.text

# Admin authentication is password-based and does not depend on choosing a secret department.
admin_client = TestClient(asgi.app)
admin_login = admin_client.post(
    "/api/login",
    json={
        "username": "admin",
        "password": "V597AdminPass!123",
        "department": "Администрация",
    },
)
assert admin_login.status_code == 200, admin_login.text
assert admin_login.json()["user"]["role"] == "admin"

index_source = (ROOT / "static/index.html").read_text(encoding="utf-8")
assert 'id="department"' in index_source
assert "Выберите отдел" in index_source
for department in (
    "R&D",
    "Производство",
    "Сборка",
    "Сварка",
    "Окраска",
    "Штамповка",
    "Компоненты",
    "Качество",
    "Логистика",
    "Закупки",
    "Финансы",
    "IT",
    "Администрация",
):
    assert f'value="{department}"' in index_source
assert index_source.index('/app.js') < index_source.index('/auth_department.js')

auth_ui_source = (ROOT / "static/auth_department.js").read_text(encoding="utf-8")
assert "department: selectedDepartment" in auth_ui_source
assert "event.stopImmediatePropagation()" in auth_ui_source
assert "Администрация" in auth_ui_source

sync_source = (ROOT / "scripts/sync_admin_credentials.py").read_text(encoding="utf-8")
assert "MGC_ADMIN_SYNC_CREDENTIALS" in sync_source
assert "ALLOW_ADMIN_CREDENTIAL_RESET" in sync_source
assert 'app_env == "production"' in sync_source
assert "make_password_hash(password)" in sync_source
assert "user.department = department" in sync_source

entrypoint = (ROOT / "scripts/entrypoint.sh").read_text(encoding="utf-8")
assert "python scripts/sync_admin_credentials.py" in entrypoint
assert entrypoint.index("migrate_safe.py") < entrypoint.index("sync_admin_credentials.py") < entrypoint.index("exec uvicorn")

launcher = (ROOT / "scripts/start_lan_windows.ps1").read_text(encoding="utf-8")
assert "Введите пароль для admin" in launcher
assert "MGC_ADMIN_DEPARTMENT=Администрация" in launcher
assert "MGC_ADMIN_SYNC_CREDENTIALS=true" in launcher

# The user-facing recommended test password must remain out-of-band, not committed.
for source in (index_source, auth_ui_source, sync_source, entrypoint, launcher):
    assert "MGC-Test-Admin#0809!" not in source

print("PASS: v5.9.7 user registration/login captures department and admin credentials stay configurable")
