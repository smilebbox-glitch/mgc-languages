from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

security = (ROOT / "mgc/security.py").read_text(encoding="utf-8")
auth_router = (ROOT / "mgc/routers/auth.py").read_text(encoding="utf-8")
auth_bridge = (ROOT / "mgc_core/auth_router_bridge.py").read_text(encoding="utf-8")
nginx = (ROOT / "deploy/nginx/default.conf").read_text(encoding="utf-8")
gateway = (ROOT / "deploy/nginx/secure-gateway.conf").read_text(encoding="utf-8")
compose = (ROOT / "docker-compose.pilot.yml").read_text(encoding="utf-8")
server_edge = (ROOT / "docker-compose.server-edge.yml").read_text(encoding="utf-8")
env = (ROOT / ".env.company-pilot.example").read_text(encoding="utf-8")
entrypoint = (ROOT / "scripts/entrypoint.sh").read_text(encoding="utf-8")
server_preflight = (ROOT / "scripts/server_security_preflight.py").read_text(encoding="utf-8")
secure_start = (ROOT / "scripts/start-secure-server.sh").read_text(encoding="utf-8")
gitignore = (ROOT / ".gitignore").read_text(encoding="utf-8")
requirements = (ROOT / "requirements.txt").read_text(encoding="utf-8")

# Password/CSRF/browser hardening.
assert "PASSWORD_PBKDF2_ITERATIONS = 600_000" in security
assert "password_hash_needs_upgrade" in security
assert "hmac.compare_digest" in security
assert "form-action 'self'" in security
assert '"X-Permitted-Cross-Domain-Policies": "none"' in security
assert '"Cross-Origin-Opener-Policy": "same-origin"' in security
assert '"Cache-Control"] = "no-store, max-age=0"' in security

# Successful legacy local logins transparently migrate to the stronger password work factor.
assert "password_hash_needs_upgrade(user.password_hash)" in auth_router
assert "user.password_hash = make_password_hash(payload.password)" in auth_router
assert '"password_hash_needs_upgrade"' in auth_bridge

# Corporate OIDC access is not granted merely because the directory account exists.
assert "required_oidc_group and required_oidc_group not in groups" in auth_router
assert 'os.getenv("OIDC_ALLOWED_GROUP", "").strip()' in auth_bridge
assert "OIDC_ALLOWED_GROUP: ${OIDC_ALLOWED_GROUP:-}" in compose
assert "OIDC_ALLOWED_GROUP=mgc-language-users" in env
assert "OIDC_SCOPE=openid profile email groups" in env
assert "SESSION_TTL_HOURS=8" in env

# Vulnerable packages discovered by the security gate must stay on remediated branches.
assert "fastapi==0.141.1" in requirements
assert "starlette==1.3.1" in requirements
assert "python-multipart==0.0.31" in requirements
assert "authlib==1.6.12" in requirements

# Inner reverse proxy anti-abuse and information-disclosure controls.
assert "server_tokens off" in nginx
assert "limit_req_zone" in nginx
assert "limit_conn_zone" in nginx
assert "limit_req_status 429" in nginx
assert "proxy_hide_header X-Powered-By" in nginx
assert "location ~ /\\." in nginx
assert "X-Permitted-Cross-Domain-Policies" in nginx
assert "Permissions-Policy" in nginx
assert "map $http_x_forwarded_proto $mgc_forwarded_proto" in nginx
assert "https https;" in nginx
assert "proxy_set_header X-Forwarded-Proto $mgc_forwarded_proto" in nginx

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
assert "app-proxy:\n    internal: true" in compose
assert "networks: [backend, app-proxy]" in compose
assert "networks: [edge, app-proxy]" in compose

# The user-facing nginx is never attached to the database network. The app is the only bridge.
nginx_block = compose.split("\n  nginx:\n", 1)[1].split("\nnetworks:\n", 1)[0]
assert "networks: [edge, app-proxy]" in nginx_block
assert "backend" not in nginx_block
app_block = compose.split("\n  app:\n", 1)[1].split("\n  backup:\n", 1)[0]
assert "networks: [backend, app-proxy]" in app_block

# Plain HTTP is diagnostic-only and cannot be reached from employee phones/LAN.
assert '"127.0.0.1:${MGC_PORT:-8080}:8080"' in compose

# The external phone/server edge terminates TLS and only forwards HTTPS semantics inward.
assert "return 308 https://$host$request_uri" in gateway
assert "ssl_protocols TLSv1.2 TLSv1.3" in gateway
assert "ssl_session_tickets off" in gateway
assert 'Strict-Transport-Security "max-age=31536000"' in gateway
assert "server_tokens off" in gateway
assert "limit_req_zone" in gateway
assert "limit_conn_zone" in gateway
assert "proxy_pass http://mgc_inner_gateway" in gateway
assert "proxy_set_header X-Forwarded-Proto https" in gateway
assert "proxy_set_header Proxy \"\"" in gateway
assert "location ~ /\\." in gateway

# Only the HTTPS gateway publishes server-facing 80/443; TLS material is mounted read-only.
assert '"${MGC_BIND_ADDRESS:-0.0.0.0}:${MGC_HTTP_PORT:-80}:8080"' in server_edge
assert '"${MGC_BIND_ADDRESS:-0.0.0.0}:${MGC_HTTPS_PORT:-443}:8443"' in server_edge
assert "TLS_CERT_FILE:?Set TLS_CERT_FILE" in server_edge
assert "TLS_KEY_FILE:?Set TLS_KEY_FILE" in server_edge
assert "/etc/nginx/tls/tls.crt:ro" in server_edge
assert "/etc/nginx/tls/tls.key:ro" in server_edge
assert "read_only: true" in server_edge
assert "no-new-privileges:true" in server_edge
assert "cap_drop:" in server_edge and "- ALL" in server_edge
assert "networks: [edge]" in server_edge

# The approved company-pilot template forces corporate auth, secure cookies and trusted HTTPS.
assert "AUTH_MODE=oidc" in env
assert "REGISTRATION_ENABLED=false" in env
assert "COOKIE_SECURE=true" in env
assert "READY_REQUIRE_OIDC=true" in env
assert "READY_REQUIRE_SECURE_COOKIE=true" in env
assert "TRUSTED_HOSTS=mgc-language-pilot.company.local" in env
assert "CORS_ORIGINS=\n" in env
assert "MGC_SERVER_NAME=mgc-language-pilot.company.local" in env
assert "MGC_HTTP_PORT=80" in env
assert "MGC_HTTPS_PORT=443" in env
assert "TLS_CERT_FILE=./deploy/tls/tls.crt" in env
assert "TLS_KEY_FILE=./deploy/tls/tls.key" in env

# Secure startup fails closed on weak identity/TLS configuration before Docker is started.
for required_contract in (
    'AUTH_MODE", "").lower() == "oidc"',
    'REGISTRATION_ENABLED", "").lower() == "false"',
    'COOKIE_SECURE", "").lower() == "true"',
    'READY_REQUIRE_OIDC", "").lower() == "true"',
    'READY_REQUIRE_SECURE_COOKIE", "").lower() == "true"',
    'OIDC_ALLOWED_GROUP',
    'OIDC_DISCOVERY_URL',
    'TLS_CERT_FILE',
    'TLS_KEY_FILE',
    'openssl", "x509"',
    'TLS certificate and private key do not match',
):
    assert required_contract in server_preflight
assert 'python3 scripts/server_security_preflight.py "$ENV_FILE"' in secure_start
assert "docker-compose.server-edge.yml" in secure_start
assert "config --quiet" in secure_start

# TLS private material must never be accidentally committed with normal Git usage.
assert "deploy/tls/*" in gitignore
assert "!deploy/tls/README.md" in gitignore

# Uvicorn proxy trust is configurable; production exposure is shielded behind isolated reverse proxies.
assert 'FORWARDED_ALLOW_IPS:-*' in entrypoint

print("OK: server/mobile security baseline is protected")
