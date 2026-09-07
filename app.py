"""Compatibility facade for historical ``import app`` consumers.

The deployable runtime now loads ``mgc.legacy_app`` behind ``mgc_core``.  Keep
this module intentionally small: existing tests, scripts and integrations may
continue to access models/helpers through module-level ``__getattr__`` while
new endpoint ownership moves into APIRouter modules.
"""
from __future__ import annotations

from typing import Any

# Preserve the v5.7.3 public compatibility contract for settings/DB symbols.
from mgc.config import *  # noqa: F401,F403,E402
from mgc.database import DATABASE_URL, SessionLocal, engine  # noqa: E402
from mgc import legacy_app as _legacy

app = _legacy.app


def __getattr__(name: str) -> Any:
    return getattr(_legacy, name)


def __dir__() -> list[str]:
    return sorted(set(globals()) | set(dir(_legacy)))


__all__ = [name for name in dir(_legacy) if not name.startswith("__")]
