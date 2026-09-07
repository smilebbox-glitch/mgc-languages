from __future__ import annotations

import hashlib
import hmac
import secrets
from collections.abc import Iterable


PASSWORD_PBKDF2_ITERATIONS = 260_000
PASSWORD_SALT_BYTES = 16
CSRF_EXEMPT_PATHS = frozenset({"/api/login", "/api/register", "/api/auth/oidc/callback"})
STATE_CHANGING_METHODS = frozenset({"POST", "PUT", "PATCH", "DELETE"})
CONTENT_SECURITY_POLICY = (
    "default-src 'self'; img-src 'self' data:; style-src 'self' 'unsafe-inline'; "
    "script-src 'self'; connect-src 'self'; media-src 'self' blob:; object-src 'none'; "
    "base-uri 'self'; frame-ancestors 'none'"
)


def make_password_hash(password: str) -> str:
    """Create the historical MGC PBKDF2-SHA256 password representation."""
    salt = secrets.token_bytes(PASSWORD_SALT_BYTES)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, PASSWORD_PBKDF2_ITERATIONS)
    return "$".join([str(PASSWORD_PBKDF2_ITERATIONS), salt.hex(), digest.hex()])


def verify_password(password: str, stored: str) -> bool:
    """Verify an existing MGC password hash without changing its storage contract."""
    try:
        iterations_s, salt_s, digest_s = stored.split("$", 2)
        digest = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt_s), int(iterations_s))
        return hmac.compare_digest(digest.hex(), digest_s)
    except (ValueError, TypeError):
        return False


def token_digest(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def client_fingerprint(raw_client: str) -> str:
    """Return the existing short privacy-preserving client fingerprint."""
    return hashlib.sha256((raw_client or "unknown").encode()).hexdigest()[:20]


def csrf_required(method: str, path: str, *, session_present: bool) -> bool:
    return (
        method.upper() in STATE_CHANGING_METHODS
        and path.startswith("/api/")
        and path not in CSRF_EXEMPT_PATHS
        and session_present
    )


def csrf_tokens_valid(cookie_token: str, header_token: str) -> bool:
    return bool(cookie_token and header_token and hmac.compare_digest(cookie_token, header_token))


def role_allowed(role: str, allowed_roles: Iterable[str]) -> bool:
    return role in set(allowed_roles)


def oidc_role(
    groups: Iterable[str],
    *,
    admin_group: str = "",
    editor_group: str = "",
    manager_group: str = "",
) -> str:
    group_set = {str(group) for group in groups}
    if admin_group and admin_group in group_set:
        return "admin"
    if editor_group and editor_group in group_set:
        return "editor"
    if manager_group and manager_group in group_set:
        return "manager"
    return "user"


def manager_target_allowed(manager_role: str, manager_department: str, target_department: str) -> bool:
    return manager_role == "admin" or (manager_role == "manager" and manager_department == target_department)


def security_headers(*, cookie_secure: bool, api_path: bool) -> dict[str, str]:
    headers = {
        "X-Content-Type-Options": "nosniff",
        "X-Frame-Options": "DENY",
        "Referrer-Policy": "no-referrer",
        "Permissions-Policy": "camera=(), geolocation=(), microphone=()",
        "Content-Security-Policy": CONTENT_SECURITY_POLICY,
    }
    if cookie_secure:
        headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    if api_path:
        headers["Cache-Control"] = "no-store"
    return headers


__all__ = [
    "PASSWORD_PBKDF2_ITERATIONS",
    "PASSWORD_SALT_BYTES",
    "CSRF_EXEMPT_PATHS",
    "STATE_CHANGING_METHODS",
    "CONTENT_SECURITY_POLICY",
    "make_password_hash",
    "verify_password",
    "token_digest",
    "client_fingerprint",
    "csrf_required",
    "csrf_tokens_valid",
    "role_allowed",
    "oidc_role",
    "manager_target_allowed",
    "security_headers",
]
