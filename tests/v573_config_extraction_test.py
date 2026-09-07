from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "mgc" / "config.py"
APP_PATH = ROOT / "app.py"

assert CONFIG_PATH.is_file(), "v5.7.3 config module is missing"
assert (ROOT / "mgc" / "__init__.py").is_file(), "mgc package marker is missing"

config_source = CONFIG_PATH.read_text(encoding="utf-8")
app_source = APP_PATH.read_text(encoding="utf-8")

# Configuration must remain dependency-light: importing settings must not create the API or DB engine.
for forbidden in ("fastapi", "sqlalchemy", "uvicorn", "alembic"):
    assert forbidden not in config_source.lower(), f"mgc.config unexpectedly depends on {forbidden}"
assert "from mgc.config import *" in app_source, "app.py no longer re-exports extracted settings"
assert "ROOT = Path(__file__).resolve().parent" not in app_source, "legacy inline config block returned to app.py"


def run_probe(env_overrides: dict[str, str], code: str) -> dict:
    env = os.environ.copy()
    env.update(env_overrides)
    proc = subprocess.run(
        [sys.executable, "-c", code],
        cwd=ROOT,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=60,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    lines = [line for line in proc.stdout.splitlines() if line.strip()]
    assert lines, proc.stdout
    return json.loads(lines[-1])


pilot = run_probe(
    {
        "APP_ENV": "pilot",
        "SESSION_TTL_HOURS": "0",
        "TTS_CONCURRENCY": "999",
        "DB_POOL_SIZE": "999",
        "TTS_CACHE_PERSISTENCE": "",
    },
    """
import json
import mgc.config as c
print(json.dumps({
    'root': str(c.ROOT),
    'data': str(c.DATA_DIR),
    'static': str(c.STATIC_DIR),
    'env': c.APP_ENV,
    'ready_schema': c.READY_REQUIRE_SCHEMA_HEAD,
    'ready_rls': c.READY_REQUIRE_RLS,
    'rls': c.RLS_ENABLED,
    'term_approval': c.TERM_APPROVAL_REQUIRED,
    'session_ttl': c.SESSION_TTL_HOURS,
    'tts_concurrency': c.TTS_CONCURRENCY,
    'db_pool_size': c.DB_POOL_SIZE,
    'tts_cache_persistence': c.TTS_CACHE_PERSISTENCE,
}, ensure_ascii=False))
""",
)

assert Path(pilot["root"]) == ROOT
assert Path(pilot["data"]) == ROOT / "data"
assert Path(pilot["static"]) == ROOT / "static"
assert pilot["env"] == "pilot"
assert pilot["ready_schema"] is True
assert pilot["ready_rls"] is True
assert pilot["rls"] is True
assert pilot["term_approval"] is True
assert pilot["session_ttl"] == 1
assert pilot["tts_concurrency"] == 8
assert pilot["db_pool_size"] == 100
assert pilot["tts_cache_persistence"] == "ephemeral"

compat = run_probe(
    {
        "APP_ENV": "development",
        "DATABASE_URL": "sqlite:///:memory:",
        "AUTO_CREATE_SCHEMA": "true",
        "AUTH_MODE": "local",
        "OIDC_STATE_SECRET": "v573-config-contract-secret-32-bytes",
    },
    """
import json
import app
import mgc.config as c
print(json.dumps({
    'same_root': app.ROOT == c.ROOT,
    'same_data': app.DATA_DIR == c.DATA_DIR,
    'same_static': app.STATIC_DIR == c.STATIC_DIR,
    'same_env': app.APP_ENV == c.APP_ENV,
    'same_version': app.APP_VERSION == c.APP_VERSION,
    'same_flags': app.BUILTIN_FEATURE_FLAGS == c.BUILTIN_FEATURE_FLAGS,
    'app_has_ready': hasattr(app, 'READY_REQUIRE_SCHEMA_HEAD'),
    'app_has_tts': hasattr(app, 'TTS_CONCURRENCY'),
}, ensure_ascii=False))
""",
)

assert all(compat.values()), compat
print("OK: v5.7.3 config extraction preserves environment defaults, bounds and app compatibility")
