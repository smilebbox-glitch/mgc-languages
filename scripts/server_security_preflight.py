#!/usr/bin/env python3
from __future__ import annotations

import os
import re
import shutil
import stat
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLACEHOLDER_MARKERS = ("CHANGE_ME", "CHANGEME", "REPLACE_ME", "EXAMPLE_ONLY")


def parse_env(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
            value = value[1:-1]
        values[key] = value
    return values


def is_placeholder(value: str) -> bool:
    upper = value.upper()
    return any(marker in upper for marker in PLACEHOLDER_MARKERS)


def resolve_deploy_path(raw: str) -> Path:
    path = Path(raw).expanduser()
    return path if path.is_absolute() else (ROOT / path).resolve()


def openssl_bytes(*args: str, input_bytes: bytes | None = None) -> bytes:
    result = subprocess.run(
        ["openssl", *args],
        input=input_bytes,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if result.returncode != 0:
        message = result.stderr.decode("utf-8", "replace").strip() or "openssl command failed"
        raise RuntimeError(message)
    return result.stdout


def main() -> int:
    env_path = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / ".env.pilot"
    if not env_path.is_absolute():
        env_path = (Path.cwd() / env_path).resolve()

    errors: list[str] = []
    passed: list[str] = []

    def require(condition: bool, message: str, pass_message: str) -> None:
        if condition:
            passed.append(pass_message)
        else:
            errors.append(message)

    if not env_path.is_file():
        print(f"FAIL: deployment environment file not found: {env_path}", file=sys.stderr)
        return 1

    env = parse_env(env_path)

    require(env.get("APP_ENV", "").lower() in {"pilot", "production"}, "APP_ENV must be pilot or production", "server environment selected")
    require(env.get("AUTH_MODE", "").lower() == "oidc", "AUTH_MODE must be oidc for employee server access", "corporate OIDC required")
    require(env.get("REGISTRATION_ENABLED", "").lower() == "false", "REGISTRATION_ENABLED must be false", "self-registration disabled")
    require(env.get("COOKIE_SECURE", "").lower() == "true", "COOKIE_SECURE must be true", "secure cookies required")
    require(env.get("READY_REQUIRE_OIDC", "").lower() == "true", "READY_REQUIRE_OIDC must be true", "readiness fails closed on OIDC")
    require(env.get("READY_REQUIRE_SECURE_COOKIE", "").lower() == "true", "READY_REQUIRE_SECURE_COOKIE must be true", "readiness fails closed on secure cookies")

    server_name = env.get("MGC_SERVER_NAME", "").strip().lower()
    valid_hostname = bool(
        server_name
        and not server_name.startswith(("http://", "https://"))
        and "/" not in server_name
        and "*" not in server_name
        and re.fullmatch(r"(?=.{1,253}$)(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)*[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?", server_name)
    )
    require(valid_hostname, "MGC_SERVER_NAME must be one explicit DNS hostname", "explicit server DNS name configured")

    trusted_hosts = [item.strip().lower() for item in env.get("TRUSTED_HOSTS", "").split(",") if item.strip()]
    require(bool(trusted_hosts) and "*" not in trusted_hosts, "TRUSTED_HOSTS must be an explicit non-wildcard allow-list", "trusted-host allow-list is explicit")
    require(not server_name or server_name in trusted_hosts, "TRUSTED_HOSTS must contain MGC_SERVER_NAME", "server DNS name is trusted")

    cors = [item.strip() for item in env.get("CORS_ORIGINS", "").split(",") if item.strip()]
    require("*" not in cors and all(item.startswith("https://") for item in cors), "CORS_ORIGINS must be empty or contain only explicit https:// origins", "CORS is closed or HTTPS-only")

    oidc_url = env.get("OIDC_DISCOVERY_URL", "").strip()
    require(oidc_url.startswith("https://") and not is_placeholder(oidc_url), "OIDC_DISCOVERY_URL must be a real HTTPS URL", "OIDC discovery uses HTTPS")

    required_non_placeholder = {
        "OIDC_CLIENT_ID": 4,
        "OIDC_CLIENT_SECRET": 16,
        "OIDC_ALLOWED_GROUP": 3,
        "OIDC_STATE_SECRET": 32,
        "METRICS_TOKEN": 24,
        "POSTGRES_PASSWORD": 16,
    }
    for key, minimum in required_non_placeholder.items():
        value = env.get(key, "").strip()
        require(bool(value) and len(value) >= minimum and not is_placeholder(value), f"{key} must be set to a non-placeholder value of at least {minimum} characters", f"{key} configured")

    cert_raw = env.get("TLS_CERT_FILE", "").strip()
    key_raw = env.get("TLS_KEY_FILE", "").strip()
    require(bool(cert_raw) and not is_placeholder(cert_raw), "TLS_CERT_FILE must be set", "TLS certificate path configured")
    require(bool(key_raw) and not is_placeholder(key_raw), "TLS_KEY_FILE must be set", "TLS private-key path configured")

    cert_path = resolve_deploy_path(cert_raw) if cert_raw else None
    key_path = resolve_deploy_path(key_raw) if key_raw else None
    require(bool(cert_path and cert_path.is_file()), "TLS certificate file does not exist", "TLS certificate exists")
    require(bool(key_path and key_path.is_file()), "TLS private-key file does not exist", "TLS private key exists")

    if key_path and key_path.is_file() and os.name != "nt":
        mode = stat.S_IMODE(key_path.stat().st_mode)
        require((mode & 0o077) == 0, "TLS private key must not be accessible to group/other users (recommended mode 0600)", "TLS private-key filesystem permissions are restricted")

    if cert_path and cert_path.is_file() and key_path and key_path.is_file():
        if shutil.which("openssl") is None:
            errors.append("openssl is required to validate the server certificate and key")
        else:
            try:
                # Require at least seven days of validity so an already-expiring cert cannot enter service.
                check = subprocess.run(
                    ["openssl", "x509", "-in", str(cert_path), "-noout", "-checkend", str(7 * 24 * 3600)],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.PIPE,
                    check=False,
                )
                require(check.returncode == 0, "TLS certificate is invalid or expires in less than seven days", "TLS certificate validity window is acceptable")

                san = openssl_bytes("x509", "-in", str(cert_path), "-noout", "-ext", "subjectAltName").decode("utf-8", "replace").lower()
                require(not server_name or f"dns:{server_name}" in san, "TLS certificate SAN must contain MGC_SERVER_NAME", "TLS certificate matches server DNS name")

                cert_pub_pem = openssl_bytes("x509", "-in", str(cert_path), "-pubkey", "-noout")
                cert_pub_der = openssl_bytes("pkey", "-pubin", "-outform", "DER", input_bytes=cert_pub_pem)
                key_pub_der = openssl_bytes("pkey", "-in", str(key_path), "-pubout", "-outform", "DER")
                require(cert_pub_der == key_pub_der, "TLS certificate and private key do not match", "TLS certificate and private key match")
            except RuntimeError as exc:
                errors.append(f"TLS validation failed: {exc}")

    for item in passed:
        print(f"PASS: {item}")
    if errors:
        for item in errors:
            print(f"FAIL: {item}", file=sys.stderr)
        print(f"\nServer security preflight failed: {len(errors)} issue(s).", file=sys.stderr)
        return 1

    print("\nServer security preflight passed. Secure phone/server deployment may start.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
