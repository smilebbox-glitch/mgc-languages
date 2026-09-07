from __future__ import annotations

import os

from sqlalchemy import select

from mgc.database import SessionLocal
from mgc.security import make_password_hash
from mgc.legacy_app import User


def env_true(name: str) -> bool:
    return os.getenv(name, "").strip().lower() in {"1", "true", "yes", "on"}


def main() -> int:
    if not env_true("MGC_ADMIN_SYNC_CREDENTIALS"):
        print("admin credential sync: disabled")
        return 0

    app_env = os.getenv("APP_ENV", "development").strip().lower()
    if app_env == "production" and not env_true("ALLOW_ADMIN_CREDENTIAL_RESET"):
        raise SystemExit(
            "ERROR: admin credential sync is blocked in production unless "
            "ALLOW_ADMIN_CREDENTIAL_RESET=true is explicitly set"
        )

    username = os.getenv("MGC_ADMIN_USERNAME", "admin").strip().lower() or "admin"
    password = os.getenv("MGC_ADMIN_PASSWORD", "")
    display_name = os.getenv("MGC_ADMIN_DISPLAY_NAME", "MGC Admin").strip() or "MGC Admin"
    department = os.getenv("MGC_ADMIN_DEPARTMENT", "Администрация").strip()[:160] or "Администрация"

    if len(password) < 12:
        raise SystemExit("ERROR: MGC_ADMIN_PASSWORD must contain at least 12 characters")
    if password.lower() in {"change_me", "change_me_with_a_long_password", "password", "administrator"}:
        raise SystemExit("ERROR: insecure MGC_ADMIN_PASSWORD is not allowed")

    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.username == username))
        if user is None:
            user = User(
                username=username,
                display_name=display_name,
                password_hash=make_password_hash(password),
                role="admin",
                department=department,
            )
            db.add(user)
        else:
            user.display_name = display_name
            user.password_hash = make_password_hash(password)
            user.role = "admin"
            user.department = department
        db.commit()

    print(f"admin credential sync: OK username={username} department={department}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
