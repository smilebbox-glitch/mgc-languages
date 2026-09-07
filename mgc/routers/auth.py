from __future__ import annotations

import re
from typing import Any, Callable

from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, Response
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, Field
from sqlalchemy import delete, select
from sqlalchemy.orm import Session


class AuthPayload(BaseModel):
    username: str = Field(min_length=3, max_length=80)
    password: str = Field(min_length=6, max_length=200)
    display_name: str | None = Field(default=None, max_length=120)


def build_auth_router(
    *,
    auth_mode: str,
    registration_enabled: bool,
    user_model: type[Any],
    login_session_model: type[Any],
    db_session: Callable[..., Any],
    current_user: Callable[..., Any],
    make_password_hash: Callable[[str], str],
    verify_password: Callable[[str, str], bool],
    token_digest: Callable[[str], str],
    rate_limit: Callable[..., Any],
    audit_event: Callable[..., Any],
    create_login_session: Callable[..., Any],
    user_view: Callable[[Any], dict[str, Any]],
    oidc_role: Callable[[list[str]], str],
    oidc_discovery_url: str,
    oidc_client_id: str,
    oidc_client_secret: str,
    oidc_scope: str,
    oidc_username_claim: str,
    oidc_display_name_claim: str,
    oidc_groups_claim: str,
    oidc_department_claim: str,
) -> APIRouter:
    """Build the authentication router without importing the historical app module."""
    router = APIRouter()

    @router.post("/api/register")
    def register(
        payload: AuthPayload,
        request: Request,
        response: Response,
        db: Session = Depends(db_session),
    ):
        if auth_mode != "local" or not registration_enabled:
            raise HTTPException(403, "Самостоятельная регистрация отключена")
        rate_limit(request, "register", 5, 600)
        username = payload.username.strip().lower()
        if not re.fullmatch(r"[a-zA-Z0-9_.-]{3,80}", username):
            raise HTTPException(400, "Логин: латинские буквы, цифры, точка, дефис или подчёркивание")
        if db.scalar(select(user_model).where(user_model.username == username)):
            raise HTTPException(409, "Такой логин уже зарегистрирован")
        user = user_model(
            username=username,
            display_name=(payload.display_name or username).strip() or username,
            password_hash=make_password_hash(payload.password),
        )
        db.add(user)
        db.flush()
        audit_event(
            db,
            "auth.register",
            actor_user_id=user.id,
            target_type="user",
            target_id=str(user.id),
            request=request,
        )
        db.commit()
        db.refresh(user)
        return create_login_session(db, user, response)

    @router.post("/api/login")
    def login(
        payload: AuthPayload,
        request: Request,
        response: Response,
        db: Session = Depends(db_session),
    ):
        if auth_mode != "local":
            raise HTTPException(403, "Local auth отключён; используйте корпоративный вход")
        rate_limit(request, "login", 10, 300)
        user = db.scalar(
            select(user_model).where(user_model.username == payload.username.strip().lower())
        )
        if not user or not verify_password(payload.password, user.password_hash):
            raise HTTPException(401, "Неверный логин или пароль")
        audit_event(
            db,
            "auth.login",
            actor_user_id=user.id,
            target_type="user",
            target_id=str(user.id),
            request=request,
        )
        db.commit()
        return create_login_session(db, user, response)

    @router.post("/api/logout")
    def logout(
        request: Request,
        response: Response,
        user: Any = Depends(current_user),
        mgc_session: str | None = Cookie(default=None),
        db: Session = Depends(db_session),
    ):
        if mgc_session:
            db.execute(
                delete(login_session_model).where(
                    login_session_model.token_hash == token_digest(mgc_session)
                )
            )
        audit_event(
            db,
            "auth.logout",
            actor_user_id=user.id,
            target_type="user",
            target_id=str(user.id),
            request=request,
        )
        db.commit()
        response.delete_cookie("mgc_session", path="/")
        response.delete_cookie("mgc_csrf", path="/")
        return {"ok": True}

    @router.get("/api/auth/oidc/login")
    async def oidc_login(request: Request):
        if auth_mode != "oidc":
            raise HTTPException(404, "OIDC не включён")
        try:
            from authlib.integrations.starlette_client import OAuth
        except ImportError:
            raise HTTPException(503, "OIDC dependency is not installed")
        oauth = OAuth()
        oauth.register(
            name="corporate",
            server_metadata_url=oidc_discovery_url,
            client_id=oidc_client_id,
            client_secret=oidc_client_secret,
            client_kwargs={"scope": oidc_scope},
        )
        redirect_uri = str(request.url_for("oidc_callback"))
        return await oauth.corporate.authorize_redirect(request, redirect_uri)

    @router.get("/api/auth/oidc/callback", name="oidc_callback")
    async def oidc_callback(request: Request, db: Session = Depends(db_session)):
        if auth_mode != "oidc":
            raise HTTPException(404, "OIDC не включён")
        from authlib.integrations.starlette_client import OAuth

        oauth = OAuth()
        oauth.register(
            name="corporate",
            server_metadata_url=oidc_discovery_url,
            client_id=oidc_client_id,
            client_secret=oidc_client_secret,
            client_kwargs={"scope": oidc_scope},
        )
        token = await oauth.corporate.authorize_access_token(request)
        claims = token.get("userinfo") or await oauth.corporate.userinfo(token=token)
        username = str(
            claims.get(oidc_username_claim)
            or claims.get("email")
            or claims.get("sub")
            or ""
        ).strip().lower()
        if not username:
            raise HTTPException(403, "OIDC не вернул идентификатор пользователя")
        display_name = str(claims.get(oidc_display_name_claim) or username).strip()[:120]
        groups_raw = claims.get(oidc_groups_claim) or []
        groups = (
            [str(item) for item in groups_raw]
            if isinstance(groups_raw, (list, tuple, set))
            else [str(groups_raw)]
        )
        role = oidc_role(groups)
        department = str(claims.get(oidc_department_claim) or "General").strip()[:160] or "General"
        user = db.scalar(select(user_model).where(user_model.username == username))
        if not user:
            user = user_model(
                username=username[:80],
                display_name=display_name or username[:120],
                password_hash="OIDC",
                role=role,
                department=department,
            )
            db.add(user)
            db.flush()
        else:
            user.display_name = display_name or user.display_name
            user.role = role
            user.department = department
        audit_event(
            db,
            "auth.oidc.login",
            actor_user_id=user.id,
            target_type="user",
            target_id=str(user.id),
            request=request,
            metadata={"role": role, "department": department},
        )
        db.commit()
        db.refresh(user)
        response = RedirectResponse(url="/")
        create_login_session(db, user, response)
        return response

    @router.get("/api/me")
    def me(user: Any = Depends(current_user)):
        return user_view(user)

    return router


__all__ = ["AuthPayload", "build_auth_router"]
