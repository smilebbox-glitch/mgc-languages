from __future__ import annotations

import hmac
from datetime import datetime, timezone
from dataclasses import dataclass
from functools import lru_cache
from urllib.parse import urlparse

import httpx
from fastapi import Header, HTTPException

from app.core.config import get_settings


@dataclass
class Identity:
    user: str
    groups: list[str]
    subject: str = ""
    auth_mode: str = "unknown"
    issuer: str = ""
    acr: str = ""
    auth_time: int | None = None
    issued_at: int | None = None
    expires_at: int | None = None
    client_id: str = ""
    is_service_account: bool = False


def _is_prod() -> bool:
    return get_settings().app_env.lower() in {"prod", "production"}


def _validate_oidc_endpoint(url: str, *, label: str) -> None:
    cfg = get_settings()
    parsed = urlparse(url)
    if _is_prod() and not cfg.allow_insecure_oidc_in_prod and parsed.scheme.lower() != "https":
        raise RuntimeError(f"{label} must use HTTPS in production")
    if not parsed.hostname:
        raise RuntimeError(f"{label} has no hostname")


@lru_cache(maxsize=1)
def _discover_jwks_url() -> str:
    cfg = get_settings()
    if cfg.oidc_jwks_url:
        _validate_oidc_endpoint(cfg.oidc_jwks_url, label="OIDC JWKS URL")
        if cfg.oidc_allowed_jwks_host_set:
            host = (urlparse(cfg.oidc_jwks_url).hostname or "").lower()
            if host not in cfg.oidc_allowed_jwks_host_set:
                raise RuntimeError("OIDC JWKS host is not in the configured allowlist")
        return cfg.oidc_jwks_url
    if not cfg.oidc_issuer:
        raise RuntimeError("OIDC issuer or JWKS URL is not configured")
    _validate_oidc_endpoint(cfg.oidc_issuer, label="OIDC issuer")
    discovery_url = cfg.oidc_issuer.rstrip("/") + "/.well-known/openid-configuration"
    response = httpx.get(discovery_url, timeout=10, follow_redirects=False)
    response.raise_for_status()
    jwks_uri = str(response.json().get("jwks_uri") or "")
    if not jwks_uri:
        raise RuntimeError("OIDC discovery document has no jwks_uri")
    _validate_oidc_endpoint(jwks_uri, label="OIDC discovered JWKS URL")
    issuer_host = (urlparse(cfg.oidc_issuer).hostname or "").lower()
    jwks_host = (urlparse(jwks_uri).hostname or "").lower()
    allowed = cfg.oidc_allowed_jwks_host_set or {issuer_host}
    if jwks_host not in allowed:
        raise RuntimeError("OIDC discovered JWKS host is not allowed")
    return jwks_uri


def _oidc_identity(token: str) -> Identity:
    cfg = get_settings()
    if _is_prod() and not cfg.oidc_audience:
        raise HTTPException(503, "OIDC audience is required in production")
    try:
        import jwt  # lazy import keeps non-OIDC dev/test paths lightweight

        algorithms = sorted(cfg.oidc_allowed_algorithm_set)
        if not algorithms or any(a.lower() == "none" or a.upper().startswith("HS") for a in algorithms):
            raise RuntimeError("OIDC algorithm allowlist contains an unsafe algorithm")
        key = jwt.PyJWKClient(_discover_jwks_url(), cache_keys=True).get_signing_key_from_jwt(token).key
        required = sorted(cfg.oidc_required_claim_set | {"exp", "iat", "sub"})
        options = {"verify_aud": bool(cfg.oidc_audience), "require": required}
        payload = jwt.decode(
            token,
            key=key,
            algorithms=algorithms,
            audience=cfg.oidc_audience or None,
            issuer=cfg.oidc_issuer or None,
            leeway=max(0, min(int(cfg.oidc_clock_skew_seconds), 300)),
            options=options,
        )
        if cfg.oidc_required_acr_set and str(payload.get("acr") or "") not in cfg.oidc_required_acr_set:
            raise RuntimeError("OIDC acr does not satisfy the configured assurance policy")
    except HTTPException:
        raise
    except Exception:
        # Do not disclose token/JWKS/parser internals to callers. Operators get request-id-correlated logs.
        raise HTTPException(401, "Invalid OIDC token")
    subject = str(payload.get("sub") or "")
    user = str(payload.get(cfg.oidc_user_claim) or payload.get("email") or subject or "")
    raw_groups = payload.get(cfg.oidc_groups_claim, [])
    if isinstance(raw_groups, str):
        raw_groups = [raw_groups]
    groups = sorted({str(x) for x in raw_groups if str(x).strip()})
    if not user:
        raise HTTPException(401, "OIDC token has no user claim")
    actor_value = str(payload.get(cfg.oidc_actor_type_claim) or "").strip().lower()
    client_id = str(payload.get(cfg.oidc_client_id_claim) or payload.get("client_id") or "")
    service_values = cfg.oidc_service_account_value_set
    is_service = actor_value in service_values if actor_value else False
    # Client-credentials deployments should set the configured actor-type claim explicitly.
    # We never infer service-account status from a username prefix.
    return Identity(
        user=user, groups=groups, subject=subject, auth_mode="oidc",
        issuer=str(payload.get("iss") or cfg.oidc_issuer or ""), acr=str(payload.get("acr") or ""),
        auth_time=int(payload["auth_time"]) if payload.get("auth_time") is not None else None,
        issued_at=int(payload["iat"]) if payload.get("iat") is not None else None,
        expires_at=int(payload["exp"]) if payload.get("exp") is not None else None,
        client_id=client_id, is_service_account=is_service,
    )


def _require_engineer(identity: Identity) -> Identity:
    cfg = get_settings()
    if not cfg.engineer_only_access:
        return identity
    allowed = cfg.engineer_access_group_set | cfg.engineering_admin_group_set
    if not allowed:
        raise HTTPException(503, "Engineer-only access is enabled but no engineering groups are configured")
    if not (set(identity.groups) & allowed):
        raise HTTPException(403, "Access is restricted to the Engineering AI user group")
    return identity


def is_engineering_admin(identity: Identity) -> bool:
    cfg = get_settings()
    return bool(set(identity.groups) & cfg.engineering_admin_group_set)


def get_identity(
    authorization: str | None = Header(default=None, alias="Authorization"),
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
    x_forwarded_user: str | None = Header(default=None, alias="X-Forwarded-User"),
    x_forwarded_groups: str | None = Header(default=None, alias="X-Forwarded-Groups"),
    x_mgc_proxy_secret: str | None = Header(default=None, alias="X-MGC-Proxy-Secret"),
) -> Identity:
    cfg = get_settings()
    if cfg.auth_mode == "oidc":
        if not authorization or not authorization.lower().startswith("bearer "):
            raise HTTPException(401, "Missing Bearer token")
        identity = _oidc_identity(authorization.split(" ", 1)[1].strip())
    elif cfg.auth_mode == "trusted_headers":
        if _is_prod():
            if not cfg.allow_trusted_headers_in_prod:
                raise HTTPException(503, "Trusted-header human access is disabled in production; use OIDC")
            if not cfg.trusted_proxy_secret or not x_mgc_proxy_secret or not hmac.compare_digest(x_mgc_proxy_secret, cfg.trusted_proxy_secret):
                raise HTTPException(401, "Trusted proxy authentication failed")
        if not x_forwarded_user:
            raise HTTPException(401, "Missing trusted identity header")
        groups = [g.strip() for g in (x_forwarded_groups or "").split(",") if g.strip()]
        identity = Identity(x_forwarded_user, sorted(set(groups)), subject=x_forwarded_user, auth_mode="trusted_headers")
    elif cfg.auth_mode == "api_key":
        if _is_prod() and cfg.engineer_only_access and not cfg.allow_api_key_auth_in_prod:
            raise HTTPException(503, "API-key human access is disabled in production; use corporate OIDC/SSO")
        if not cfg.api_key or cfg.api_key == "change-me" or x_api_key != cfg.api_key:
            raise HTTPException(401, "Invalid API key")
        identity = Identity("api-key-user", sorted(cfg.api_key_group_set), subject="api-key-user", auth_mode="api_key")
    else:
        raise HTTPException(503, f"Unsupported AUTH_MODE: {cfg.auth_mode}")

    identity = _require_engineer(identity)
    identity.groups = sorted(set(identity.groups + ["all"]))
    return identity


def identity_snapshot(identity: Identity) -> dict:
    """Return a minimal, non-secret identity/assurance snapshot for approval evidence."""
    return {
        "user": identity.user,
        "subject": identity.subject or identity.user,
        "groups": sorted(g for g in set(identity.groups) if g != "all"),
        "auth_mode": identity.auth_mode,
        "issuer": identity.issuer,
        "acr": identity.acr,
        "auth_time": identity.auth_time,
        "issued_at": identity.issued_at,
        "expires_at": identity.expires_at,
        "client_id": identity.client_id,
        "is_service_account": bool(identity.is_service_account),
    }


def authentication_age_seconds(identity: Identity, now: datetime | None = None) -> int | None:
    if identity.auth_time is None:
        return None
    now = now or datetime.now(timezone.utc)
    return max(0, int(now.timestamp()) - int(identity.auth_time))
