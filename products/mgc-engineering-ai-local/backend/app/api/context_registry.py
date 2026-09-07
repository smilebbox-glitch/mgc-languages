"""Bounded-context router composition for v6.2.2.

Context modules are imported only when the selected runtime profile activates them.
Public URLs are unchanged. Profile composition remains separate from authorization.
"""
from __future__ import annotations

from importlib import import_module
from fastapi import APIRouter

from app.core.runtime_contract import active_bounded_contexts

_CONTEXT_MODULES = {
    "engineering_core": "app.api.contexts.engineering_core",
    "configuration_change": "app.api.contexts.configuration_change",
    "manufacturing_quality": "app.api.contexts.manufacturing_quality",
    "supplier_field": "app.api.contexts.supplier_field",
    "intelligence_search": "app.api.contexts.intelligence_search",
    "platform_operations": "app.api.contexts.platform_operations",
}


def _router_for(context: str):
    return getattr(import_module(_CONTEXT_MODULES[context]), "router")


def build_context_router(features) -> APIRouter:
    """Compose and import only contexts backed by the selected capability envelope."""
    aggregate = APIRouter()
    for context in active_bounded_contexts(features):
        aggregate.include_router(_router_for(context))
    return aggregate


def route_counts(contexts=None) -> dict[str, int]:
    """Route ownership metrics; imports only the explicitly requested contexts."""
    names = tuple(contexts) if contexts is not None else tuple(_CONTEXT_MODULES)
    return {name: len(_router_for(name).routes) for name in names}
