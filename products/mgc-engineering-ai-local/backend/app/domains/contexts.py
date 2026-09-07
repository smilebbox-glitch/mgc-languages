"""Stable bounded-context facade for v6.2.

Existing service modules remain import-compatible. New code should import context-level
facades instead of coupling directly to dozens of feature modules.
"""
from app.core.runtime_contract import BOUNDED_CONTEXTS

__all__ = ["BOUNDED_CONTEXTS"]
