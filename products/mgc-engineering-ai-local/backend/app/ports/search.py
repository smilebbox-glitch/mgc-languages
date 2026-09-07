from __future__ import annotations

from typing import Protocol


class SearchPort(Protocol):
    """Application-facing search/index contract.

    Implementations may be deterministic metadata/lexical search or semantic
    projections. Callers never depend on Qdrant/embedding packages directly.
    """

    mode: str

    def index_chunks(self, document: dict, chunks: list[str]) -> int: ...
    def delete_document(self, document_id: str) -> None: ...
    def search(
        self,
        query: str,
        limit: int,
        acl_groups: list[str],
        part_number: str | None = None,
        revision: str | None = None,
        doc_type: str | None = None,
        project_code: str | None = None,
        manufacturing_area: str | None = None,
    ) -> list[dict]: ...
