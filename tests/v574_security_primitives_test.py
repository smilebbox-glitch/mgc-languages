from __future__ import annotations

import hashlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from mgc.security import (  # noqa: E402
    CSRF_EXEMPT_PATHS,
    PASSWORD_PBKDF2_ITERATIONS,
    client_fingerprint,
    csrf_required,
    csrf_tokens_valid,
    make_password_hash,
    manager_target_allowed,
    oidc_role,
    role_allowed,
    security_headers,
    token_digest,
    verify_password,
)

password = "MGC-v574-Compatibility!"
first = make_password_hash(password)
second = make_password_hash(password)
assert first != second, "password hashing must use a fresh salt"
parts = first.split("$")
assert len(parts) == 3 and int(parts[0]) == PASSWORD_PBKDF2_ITERATIONS == 260_000
assert len(parts[1]) == 32, "16-byte salt must remain hex encoded"
assert len(parts[2]) == 64, "SHA-256 digest must remain hex encoded"
assert verify_password(password, first)
assert not verify_password(password + "x", first)
assert not verify_password(password, "broken")

expected_digest = hashlib.sha256(b"session-token").hexdigest()
assert token_digest("session-token") == expected_digest
assert len(client_fingerprint("192.0.2.10")) == 20
assert client_fingerprint("192.0.2.10") == client_fingerprint("192.0.2.10")
assert client_fingerprint("192.0.2.10") != "192.0.2.10"

assert CSRF_EXEMPT_PATHS == frozenset({"/api/login", "/api/register", "/api/auth/oidc/callback"})
assert not csrf_required("GET", "/api/me", session_present=True)
assert not csrf_required("POST", "/api/login", session_present=True)
assert not csrf_required("POST", "/api/me/language", session_present=False)
assert csrf_required("POST", "/api/me/language", session_present=True)
assert csrf_tokens_valid("same", "same")
assert not csrf_tokens_valid("", "same")
assert not csrf_tokens_valid("same", "different")

assert role_allowed("admin", ("admin", "editor"))
assert not role_allowed("user", ("admin", "editor"))
assert oidc_role(["admins", "editors"], admin_group="admins", editor_group="editors") == "admin"
assert oidc_role(["editors"], admin_group="admins", editor_group="editors") == "editor"
assert oidc_role(["managers"], manager_group="managers") == "manager"
assert oidc_role([], admin_group="admins") == "user"
assert manager_target_allowed("admin", "A", "B")
assert manager_target_allowed("manager", "Welding", "Welding")
assert not manager_target_allowed("manager", "Welding", "Paint")
assert not manager_target_allowed("user", "Welding", "Welding")

plain = security_headers(cookie_secure=False, api_path=False)
secure_api = security_headers(cookie_secure=True, api_path=True)
assert plain["X-Frame-Options"] == "DENY"
assert plain["X-Content-Type-Options"] == "nosniff"
assert "Strict-Transport-Security" not in plain
assert "Cache-Control" not in plain
assert secure_api["Strict-Transport-Security"] == "max-age=31536000; includeSubDomains"
assert secure_api["Cache-Control"] == "no-store"
assert "frame-ancestors 'none'" in secure_api["Content-Security-Policy"]

print("OK: v5.7.4 dependency-light security primitives preserve password, CSRF, role and header contracts")
