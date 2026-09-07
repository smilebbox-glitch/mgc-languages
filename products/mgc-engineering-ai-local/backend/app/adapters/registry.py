from __future__ import annotations

from app.core.config import get_settings
from app.ports.ai import AIAnalysisPort
from app.ports.graph import GraphProjectionPort
from app.ports.object_storage import ObjectStoragePort
from app.ports.search import SearchPort
from app.ports.translation import TranslationProviderPort


def get_search_port(settings=None) -> SearchPort:
    cfg = settings or get_settings()
    if cfg.semantic_search_enabled:
        from app.adapters.search import QdrantSearchAdapter
        return QdrantSearchAdapter()
    from app.adapters.search import CoreMetadataSearchAdapter
    return CoreMetadataSearchAdapter()


def get_graph_projection_port(settings=None) -> GraphProjectionPort:
    cfg = settings or get_settings()
    if cfg.runtime_graph_enabled:
        from app.adapters.graph import Neo4jGraphProjectionAdapter
        return Neo4jGraphProjectionAdapter()
    from app.adapters.graph import NoOpGraphProjectionAdapter
    return NoOpGraphProjectionAdapter()


def get_object_storage_port(settings=None) -> ObjectStoragePort:
    cfg = settings or get_settings()
    if cfg.runtime_object_store_enabled:
        from app.adapters.object_storage import MinioObjectStorageAdapter
        return MinioObjectStorageAdapter()
    from app.adapters.object_storage import NoOpObjectStorageAdapter
    return NoOpObjectStorageAdapter()


def get_ai_analysis_port(settings=None) -> AIAnalysisPort:
    cfg = settings or get_settings()
    if "local_llm" in cfg.runtime_features and cfg.llm_base_url and cfg.llm_model:
        from app.adapters.ai import OpenAICompatibleAIAdapter
        return OpenAICompatibleAIAdapter()
    from app.adapters.ai import DisabledAIAnalysisAdapter
    return DisabledAIAnalysisAdapter()


def get_translation_provider_port(settings=None) -> TranslationProviderPort:
    cfg = settings or get_settings()
    if "local_llm" in cfg.runtime_features and cfg.llm_base_url and cfg.llm_model:
        from app.adapters.translation import OpenAICompatibleTranslationAdapter
        return OpenAICompatibleTranslationAdapter()
    from app.adapters.translation import DisabledTranslationProviderAdapter
    return DisabledTranslationProviderAdapter()


def adapter_contract(settings=None) -> dict:
    """Machine-readable dependency inversion diagnostics for /runtime."""
    cfg = settings or get_settings()
    search = get_search_port(cfg)
    graph = get_graph_projection_port(cfg)
    storage = get_object_storage_port(cfg)
    ai = get_ai_analysis_port(cfg)
    translation = get_translation_provider_port(cfg)
    return {
        "architecture": "ports_and_adapters",
        "search": {"adapter": search.mode, "authoritative": False},
        "graph": {"adapter": graph.mode, "authoritative": False},
        "object_storage": {"adapter": storage.mode, "authoritative": False},
        "ai_analysis": {"adapter": ai.mode, "available": ai.available, "authoritative": False},
        "translation": {"adapter": translation.mode, "available": translation.available, "human_review_required": True},
        "core_has_concrete_advanced_dependencies": False,
    }
