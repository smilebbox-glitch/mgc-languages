from __future__ import annotations

import argparse
import json
import os
import secrets
from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from mgc.database import SessionLocal
from mgc.security import make_password_hash, token_digest
from mgc.legacy_app import LoginSession, User


def main() -> int:
    parser = argparse.ArgumentParser(description="Seed short-lived authenticated load-test fixtures")
    parser.add_argument("--count", type=int, default=20)
    parser.add_argument("--prefix", default="loadtest")
    parser.add_argument("--session-minutes", type=int, default=60)
    args = parser.parse_args()

    if os.getenv("LOAD_TEST_FIXTURES_ENABLED", "").strip().lower() != "true":
        raise SystemExit("ERROR: set LOAD_TEST_FIXTURES_ENABLED=true explicitly; this utility is test-only")
    if os.getenv("APP_ENV", "development").strip().lower() == "production":
        raise SystemExit("ERROR: load-test fixture seeding is disabled in APP_ENV=production")

    count = max(1, min(500, args.count))
    prefix = args.prefix.strip().lower()
    if not prefix or any(ch not in "abcdefghijklmnopqrstuvwxyz0123456789_-" for ch in prefix):
        raise SystemExit("ERROR: prefix must contain only lowercase letters, digits, '_' or '-'")
    minutes = max(5, min(24 * 60, args.session_minutes))
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=minutes)
    password_hash = make_password_hash(secrets.token_urlsafe(24))
    sessions: list[dict[str, object]] = []

    with SessionLocal() as db:
        for index in range(count):
            username = f"{prefix}-{index + 1:03d}"[:80]
            user = db.scalar(select(User).where(User.username == username))
            if user is None:
                user = User(
                    username=username,
                    display_name=f"Load Test {index + 1:03d}",
                    password_hash=password_hash,
                    role="user",
                    department="LoadTest",
                    preferred_language="chinese",
                )
                db.add(user)
                db.flush()
            raw_token = secrets.token_urlsafe(36)
            db.add(
                LoginSession(
                    token_hash=token_digest(raw_token),
                    user_id=user.id,
                    expires_at=expires_at,
                )
            )
            sessions.append({"username": username, "user_id": user.id, "session_token": raw_token})
        db.commit()

    print(
        json.dumps(
            {
                "fixture": "mgc-authenticated-load",
                "count": len(sessions),
                "expires_at": expires_at.isoformat(),
                "sessions": sessions,
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
