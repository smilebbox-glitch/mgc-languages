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
    password_hash_needs_upgrade,
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
assert len(parts) == 3 and int(parts[0]) == PASSWORD_PBKDF2_ITERATIONS == 600_000
assert len(parts[1]) == 32, "16-byte salt must remain hex encoded"
assert len(parts[2]) == 64, "SHA-256 digest must remain hex encoded"
assert verify_password(password, first)
assert not verify_password(password + "x", first)
assert not verify_password(password, "broken")
assert not password_hash_needs_upgrade(first)

# Historical hashes remain valid and are explicitly detectable for upgrade.
legacy_salt = bytes.fromhex("00112233445566778899aabbccddeeff")
legacy_digest = hashlib.pbkdf2_hmac("sha256", password.encode(), legacy_salt, 260_000)
legacy = f"260000${legacy_salt.hex()}${legacy_digest.hex()}"
assert verify_password(password, legacy)
assert password_hash_needs_upgrade(legacy)

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
assert plain["X-Permitted-Cross-Domain-Policies"] == "none"
assert plain["Cross-Origin-Opener-Policy"] == "same-origin"
assert "payment=()" in plain["Permissions-Policy"]
assert "Strict-Transport-Security" not in plain
assert "Cache-Control" not in plain
assert secure_api["Strict-Transport-Security"] == "max-age=31536000; includeSubDomains"
assert secure_api["Cache-Control"] == "no-store, max-age=0"
assert secure_api["Pragma"] == "no-cache"
assert "frame-ancestors 'none'" in secure_api["Content-Security-Policy"]
assert "form-action 'self'" in secure_api["Content-Security-Policy"]

print("OK: security primitives enforce strong password, CSRF, role and browser-header contracts")
