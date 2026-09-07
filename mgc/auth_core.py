from __future__ import annotations

import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Callable

from fastapi import Cookie, Depends, HTTPException, Response
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from .security import role_allowed, token_digest


@dataclass(frozen=True)
class AuthCoreBindings:
    current_user: Callable[..., Any]
    require_roles: Callable[..., Callable[..., Any]]
    create_login_session: Callable[..., dict[str, Any]]


def build_auth_core(
    *,
    user_model: Any,
    login_session_model: Any,
    db_dependency: Callable[..., Any],
    apply_rls_context: Callable[..., None],
    user_view: Callable[[Any], dict[str, Any]],
    session_ttl_hours: int,
    cookie_samesite: str,
    cookie_secure: bool,
) -> AuthCoreBindings:
    """Build model-aware authentication dependencies without importing app.py.

    The legacy application still owns ORM model declarations during the modular
    migration. Models and DB/session hooks are injected explicitly so this module
    stays independent of the monolithic API module and can become the canonical
    auth/session implementation incrementally.
    """

    def current_user(
        mgc_session: str | None = Cookie(default=None),
        db: Session = Depends(db_dependency),
    ) -> Any:
        if not mgc_session:
            raise HTTPException(401, "Требуется вход")
        session = db.scalar(
            select(login_session_model).where(
                login_session_model.token_hash == token_digest(mgc_session)
            )
        )
        if not session:
            raise HTTPException(401, "Сессия не найдена")
        expires = session.expires_at
        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=timezone.utc)
        if expires <= datetime.now(timezone.utc):
            db.delete(session)
            db.commit()
            raise HTTPException(401, "Сессия истекла")
        user = db.get(user_model, session.user_id)
        if not user:
            raise HTTPException(401, "Пользователь не найден")
        apply_rls_context(db, user)
        return user

    current_user.__name__ = "current_user"
    current_user.__qualname__ = "current_user"

    def require_roles(*roles: str) -> Callable[..., Any]:
        allowed = tuple(roles)

        def dependency(user: Any = Depends(current_user)) -> Any:
            if not role_allowed(str(getattr(user, "role", "")), allowed):
                raise HTTPException(403, "Недостаточно прав")
            return user

        dependency.__name__ = "require_roles_dependency"
        dependency.__qualname__ = "require_roles_dependency"
        return dependency

    def create_login_session(db: Session, user: Any, response: Response) -> dict[str, Any]:
        raw = secrets.token_urlsafe(36)
        csrf = secrets.token_urlsafe(24)
        now = datetime.now(timezone.utc)
        expiry = now + timedelta(hours=session_ttl_hours)
        db.execute(
            delete(login_session_model)
            .where(login_session_model.expires_at <= now)
            .execution_options(synchronize_session=False)
        )
        db.add(
            login_session_model(
                token_hash=token_digest(raw),
                user_id=user.id,
                expires_at=expiry,
            )
        )
        db.commit()
        max_age = session_ttl_hours * 3600
        response.set_cookie(
            "mgc_session",
            raw,
            max_age=max_age,
            httponly=True,
            samesite=cookie_samesite,
            secure=cookie_secure,
            path="/",
        )
        response.set_cookie(
            "mgc_csrf",
            csrf,
            max_age=max_age,
            httponly=False,
            samesite=cookie_samesite,
            secure=cookie_secure,
            path="/",
        )
        return {"ok": True, "user": user_view(user), "csrf": csrf}

    create_login_session.__name__ = "create_login_session"
    create_login_session.__qualname__ = "create_login_session"

    return AuthCoreBindings(
        current_user=current_user,
        require_roles=require_roles,
        create_login_session=create_login_session,
    )


__all__ = ["AuthCoreBindings", "build_auth_core"]
