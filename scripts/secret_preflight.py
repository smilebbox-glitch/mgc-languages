#!/usr/bin/env python3
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SELF = "scripts/secret_preflight.py"
PRIVATE_SUFFIXES = {".key", ".pem", ".p12", ".pfx", ".jks", ".keystore"}
FORBIDDEN_NAMES = {".env", ".env.pilot", ".env.production"}

TOKEN_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("PEM private key", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |ENCRYPTED )?PRIVATE KEY-----")),
    ("GitHub token", re.compile(r"(?:ghp|gho|ghs|ghr)_[A-Za-z0-9]{30,}")),
    ("GitHub fine-grained token", re.compile(r"github_pat_[A-Za-z0-9_]{40,}")),
    ("OpenAI-style API key", re.compile(r"sk-(?:proj-)?[A-Za-z0-9_-]{20,}")),
    ("AWS access key", re.compile(r"AKIA[0-9A-Z]{16}")),
    ("Google API key", re.compile(r"AIza[0-9A-Za-z_-]{35}")),
    ("Slack token", re.compile(r"xox[baprs]-[0-9A-Za-z-]{20,}")),
    ("npm access token", re.compile(r"npm_[A-Za-z0-9]{30,}")),
)

SENSITIVE_KEYS = {
    "POSTGRES_PASSWORD",
    "OIDC_STATE_SECRET",
    "OIDC_CLIENT_SECRET",
    "METRICS_TOKEN",
    "MGC_ADMIN_PASSWORD",
}


def safe_value(raw: str) -> bool:
    value = raw.strip().strip("'\"")
    if not value:
        return True
    upper = value.upper()

    # Runtime references and expressions are not embedded secret values. The
    # scanner still inspects the surrounding file for actual token/private-key
    # signatures, so this exemption does not hide literal credentials.
    runtime_expression = (
        value.startswith("$")
        or value.startswith("${")
        or value.startswith("os.getenv(")
        or value.startswith("os.environ")
    )
    explicit_placeholder = (
        (value.startswith("<") and value.endswith(">"))
        or "CHANGE_ME" in upper
        or "CHANGE-ME" in upper
        or "GENERATE_" in upper
        or "EXAMPLE" in upper
        or "PLACEHOLDER" in upper
        or value.startswith("ci-")
        or value.startswith("test-")
        or value.startswith("dev-only-")
    )
    return runtime_expression or explicit_placeholder


def main() -> int:
    output = subprocess.check_output(["git", "ls-files", "-z"], cwd=ROOT)
    tracked = [item for item in output.decode("utf-8").split("\0") if item]
    findings: list[str] = []

    for relative in tracked:
        normalized = relative.replace("\\", "/")
        file_path = ROOT / relative
        name = file_path.name
        suffix = file_path.suffix.lower()

        if suffix in PRIVATE_SUFFIXES:
            findings.append(f"{normalized}: tracked private-key/keystore file type ({suffix})")
        if name in FORBIDDEN_NAMES:
            findings.append(f"{normalized}: runtime secret environment file must not be tracked")

        if normalized == SELF or not file_path.is_file():
            continue
        try:
            if file_path.stat().st_size > 2 * 1024 * 1024:
                continue
            text = file_path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue

        for label, pattern in TOKEN_PATTERNS:
            if pattern.search(text):
                findings.append(f"{normalized}: possible {label}")

        for line_no, line in enumerate(text.splitlines(), 1):
            match = re.match(r"^\s*([A-Z][A-Z0-9_]+)\s*=\s*(.+?)\s*$", line)
            if not match or match.group(1) not in SENSITIVE_KEYS:
                continue
            if not safe_value(match.group(2)):
                findings.append(
                    f"{normalized}:{line_no}: {match.group(1)} appears to contain a literal secret"
                )

    if findings:
        print("Tracked secret preflight failed. Remove and rotate any real secret before continuing.", file=sys.stderr)
        for finding in findings:
            print(f"- {finding}", file=sys.stderr)
        return 1

    print(f"OK: scanned {len(tracked)} tracked files; no forbidden secret material detected.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
