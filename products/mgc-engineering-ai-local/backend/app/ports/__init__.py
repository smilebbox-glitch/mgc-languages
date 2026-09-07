"""Technology-neutral application ports for MGC's modular monolith."""

from .ai import AIAnalysisPort, AICompletion
from .graph import GraphProjectionPort
from .object_storage import ObjectStoragePort
from .search import SearchPort
from .translation import TranslationBatch, TranslationProviderPort

__all__ = [
    "AIAnalysisPort", "AICompletion", "GraphProjectionPort", "ObjectStoragePort",
    "SearchPort", "TranslationBatch", "TranslationProviderPort",
]

# v6.3.6 future corporate PKI/e-sign boundary; disabled by default.

# v6.3.7 controlled outbound handover boundary.
from .handover import HandoverDeliveryResult, HandoverWritePort
