from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from fastapi import FastAPI, Response  # noqa: E402
from fastapi.routing import APIRoute  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import DateTime, ForeignKey, Integer, String, create_engine  # noqa: E402
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402
from mgc.routers.auth import build_auth_router  # noqa: E402


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "v582_users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(80), unique=True)
    display_name: Mapped[str] = mapped_column(String(120))
    password_hash: Mapped[str] = mapped_column(String(300))
    role: Mapped[str] = mapped_column(String(30), default="user")
    department: Mapped[str] = mapped_column(String(160), default="General")


class LoginSession(Base):
    __tablename__ = "v582_login_sessions"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("v582_users.id"))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
Base.metadata.create_all(engine)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)


def db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def make_password_hash(password: str) -> str:
    return "hash:" + password


def verify_password(password: str, stored: str) -> bool:
    return stored == "hash:" + password


def token_digest(value: str) -> str:
    return "d:" + value


def current_user():
    return SimpleNamespace(
        id=999,
        username="core-user",
        display_name="Core User",
        role="user",
        department="General",
        preferred_language="chinese",
    )


def user_view(user):
    return {
        "id": user.id,
        "username": user.username,
        "display_name": user.display_name,
        "role": user.role,
        "department": user.department,
        "preferred_language": getattr(user, "preferred_language", "chinese"),
    }


events: list[str] = []

def audit_event(_db: Session, event_type: str, **_kwargs):
    events.append(event_type)


def rate_limit(*_args, **_kwargs):
    return None


_session_counter = 0

def create_login_session(db: Session, user: User, response: Response):
    global _session_counter
    _session_counter += 1
    raw = f"token-{_session_counter}"
    db.add(LoginSession(
        token_hash=token_digest(raw),
        user_id=user.id,
        expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
    ))
    db.commit()
    response.set_cookie("mgc_session", raw, httponly=True)
    response.set_cookie("mgc_csrf", "csrf-token", httponly=False)
    return {"ok": True, "user": user_view(user), "csrf": "csrf-token"}


def oidc_role(groups: list[str]) -> str:
    return "admin" if "admins" in groups else "user"


router = build_auth_router(
    auth_mode="local",
    registration_enabled=True,
    user_model=User,
    login_session_model=LoginSession,
    db_session=db_session,
    current_user=current_user,
    make_password_hash=make_password_hash,
    verify_password=verify_password,
    token_digest=token_digest,
    rate_limit=rate_limit,
    audit_event=audit_event,
    create_login_session=create_login_session,
    user_view=user_view,
    oidc_role=oidc_role,
    oidc_discovery_url="https://example.invalid/.well-known/openid-configuration",
    oidc_client_id="client",
    oidc_client_secret="secret",
    oidc_scope="openid profile email",
    oidc_username_claim="preferred_username",
    oidc_display_name_claim="name",
    oidc_groups_claim="groups",
    oidc_department_claim="department",
)
routes = [route for route in router.routes if isinstance(route, APIRoute)]
keys = {(next(iter(route.methods)), route.path) for route in routes}
assert keys == {
    ("POST", "/api/register"),
    ("POST", "/api/login"),
    ("POST", "/api/logout"),
    ("GET", "/api/auth/oidc/login"),
    ("GET", "/api/auth/oidc/callback"),
    ("GET", "/api/me"),
}
assert all(route.endpoint.__module__ == "mgc.routers.auth" for route in routes)

application = FastAPI()
application.include_router(router)
client = TestClient(application)
registered = client.post(
    "/api/register",
    json={"username": "router.user", "password": "StrongPass123!", "display_name": "Router User"},
)
assert registered.status_code == 200, registered.text
assert registered.json()["user"]["username"] == "router.user"
assert registered.cookies.get("mgc_session")
assert events[-1] == "auth.register"
assert client.post(
    "/api/register",
    json={"username": "router.user", "password": "StrongPass123!"},
).status_code == 409
assert client.post(
    "/api/login", json={"username": "router.user", "password": "wrong-pass"}
).status_code == 401
logged_in = client.post(
    "/api/login", json={"username": "router.user", "password": "StrongPass123!"}
)
assert logged_in.status_code == 200, logged_in.text
assert events[-1] == "auth.login"
me = client.get("/api/me")
assert me.status_code == 200 and me.json()["username"] == "core-user"
assert client.get("/api/auth/oidc/login").status_code == 404
assert client.get("/api/auth/oidc/callback").status_code == 404
assert "app" not in sys.modules
print("OK: v5.8.2 auth APIRouter is dependency-light and preserves local/OIDC route contracts")
