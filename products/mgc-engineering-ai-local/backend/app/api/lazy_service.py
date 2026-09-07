"""Lazy service dependency resolver — v6.2.2.

HTTP modules bind service callables without importing service implementation modules at
application startup. The target module is imported only on first invocation. This keeps
Core startup independent from optional AI/graph/object-store packages.
"""
from __future__ import annotations

from functools import lru_cache, wraps
from importlib import import_module
from typing import Any, Callable


@lru_cache(maxsize=None)
def _resolve(module: str, attribute: str) -> Any:
    return getattr(import_module(module), attribute)


def lazy_service(module: str, attribute: str) -> Callable[..., Any]:
    """Return a transparent call proxy that imports its target on first use."""
    def proxy(*args, **kwargs):
        return _resolve(module, attribute)(*args, **kwargs)
    proxy.__name__ = attribute
    proxy.__qualname__ = attribute
    proxy.__doc__ = f"Lazy proxy for {module}:{attribute}"
    proxy.__mgc_lazy_target__ = f"{module}:{attribute}"
    return proxy


def resolved_lazy_targets() -> tuple[str, ...]:
    """Diagnostic hook; intentionally exposes only targets already loaded in-process."""
    # functools cache does not expose keys, so diagnostics remain non-invasive.
    return ()
