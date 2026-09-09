from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

security = (ROOT / "mgc/security.py").read_text(encoding="utf-8")
nginx = (ROOT / "deploy/nginx/default.conf").read_text(encoding="utf-8")
compose = (ROOT / "docker-compose.pilot.yml").read_text(encoding="utf-8")
env = (ROOT / ".env.company-pilot.example").read_text(encoding="utf-8")
entrypoint = (ROOT / "scripts/entrypoint.sh").read_text(encoding="utf-8")

# Password/CSRF/browser hardening.
assert "PASSWORD_PBKDF2_ITERATIONS = 600_000" in security
assert "password_hash_needs_upgrade" in security
assert "hmac.compare_digest" in security
assert "form-action 'self'" in security
assert '"X-Permitted-Cross-Domain-Policies": "none"' in security
assert '"Cross-Origin-Opener-Policy": "same-origin"' in security
assert '"Cache-Control"] = "no-store, max-age=0"' in security

# Reverse proxy anti-abuse and information-disclosure controls.
assert "server_tokens off" in nginx
assert "limit_req_zone" in nginx
assert "limit_conn_zone" in nginx
assert "limit_req_status 429" in nginx
assert "proxy_hide_header X-Powered-By" in nginx
assert "location ~ /\\." in nginx
assert "X-Permitted-Cross-Domain-Policies" in nginx
assert "Permissions-Policy" in nginx

# Company server profile remains fail-closed around identity, cookies and DB exposure.
assert "AUTH_MODE: ${AUTH_MODE:-local}" in compose
assert "REGISTRATION_ENABLED: ${REGISTRATION_ENABLED:-false}" in compose
assert "READY_REQUIRE_REGISTRATION_DISABLED: \"true\"" in compose
assert "READY_REQUIRE_OIDC: ${READY_REQUIRE_OIDC:-false}" in compose
assert "READY_REQUIRE_SECURE_COOKIE: ${READY_REQUIRE_SECURE_COOKIE:-false}" in compose
assert "read_only: true" in compose
assert "no-new-privileges:true" in compose
assert "cap_drop:" in compose and "- ALL" in compose
assert "backend:\n    internal: true" in compose

# The approved company-pilot template forces corporate auth and secure cookies.
assert "AUTH_MODE=oidc" in env
assert "REGISTRATION_ENABLED=false" in env
assert "COOKIE_SECURE=true" in env
assert "READY_REQUIRE_OIDC=true" in env
assert "READY_REQUIRE_SECURE_COOKIE=true" in env
assert "TRUSTED_HOSTS=mgc-language-pilot.company.local" in env
assert "CORS_ORIGINS=\n" in env

# Uvicorn proxy trust is configurable; production must narrow this to the actual proxy.
assert 'FORWARDED_ALLOW_IPS:-*' in entrypoint

print("OK: server/mobile security baseline is protected")
