from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone
from http.cookies import SimpleCookie
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from fastapi import HTTPException, Response  # noqa: E402
from sqlalchemy import DateTime, ForeignKey, Integer, String, create_engine, select  # noqa: E402
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

from mgc.auth_core import build_auth_core  # noqa: E402
from mgc.security import token_digest  # noqa: E402


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users_probe"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(80), unique=True)
    role: Mapped[str] = mapped_column(String(30), default="user")
    department: Mapped[str] = mapped_column(String(80), default="General")


class LoginSession(Base):
    __tablename__ = "login_sessions_probe"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users_probe.id"))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
Base.metadata.create_all(engine)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def db_dependency():
    with SessionLocal() as db:
        yield db


rls_calls: list[int] = []


def apply_rls_context(db: Session, user: User) -> None:
    rls_calls.append(user.id)


def user_view(user: User) -> dict:
    return {"id": user.id, "username": user.username, "role": user.role}


core = build_auth_core(
    user_model=User,
    login_session_model=LoginSession,
    db_dependency=db_dependency,
    apply_rls_context=apply_rls_context,
    user_view=user_view,
    session_ttl_hours=12,
    cookie_samesite="lax",
    cookie_secure=False,
)

with SessionLocal() as db:
    user = User(username="probe", role="user", department="R&D")
    admin = User(username="admin", role="admin", department="R&D")
    db.add_all([user, admin])
    db.commit(); db.refresh(user); db.refresh(admin)

    response = Response()
    payload = core.create_login_session(db, user, response)
    assert payload["ok"] is True and payload["user"]["id"] == user.id and payload["csrf"]

    cookies = SimpleCookie()
    for header in response.headers.getlist("set-cookie"):
        cookies.load(header)
    raw_session = cookies["mgc_session"].value
    assert cookies["mgc_session"]["httponly"] is True
    assert cookies["mgc_csrf"]["httponly"] == ""
    assert cookies["mgc_session"]["samesite"].lower() == "lax"

    row = db.scalar(select(LoginSession).where(LoginSession.token_hash == token_digest(raw_session)))
    assert row is not None and row.user_id == user.id
    loaded = core.current_user(raw_session, db)
    assert loaded.id == user.id and rls_calls[-1] == user.id

    admin_only = core.require_roles("admin")
    try:
        admin_only(user)
    except HTTPException as exc:
        assert exc.status_code == 403 and exc.detail == "Недостаточно прав"
    else:
        raise AssertionError("user role unexpectedly passed admin dependency")
    assert admin_only(admin).id == admin.id

    row.expires_at = datetime.now(timezone.utc) - timedelta(minutes=1)
    db.commit()
    try:
        core.current_user(raw_session, db)
    except HTTPException as exc:
        assert exc.status_code == 401 and exc.detail == "Сессия истекла"
    else:
        raise AssertionError("expired session unexpectedly authenticated")
    assert db.scalar(select(LoginSession).where(LoginSession.token_hash == token_digest(raw_session))) is None

assert "app" not in sys.modules, "dependency-light auth core must not import the legacy application"
print("OK: v5.7.5 auth core preserves session cookies, expiry, RLS hook and role enforcement without importing app.py")
