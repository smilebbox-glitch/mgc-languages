from __future__ import annotations

from typing import Protocol
from sqlalchemy.orm import Session


class GraphProjectionPort(Protocol):
    """Optional rebuildable graph projection contract."""

    mode: str

    def sync_part(self, db: Session, part_number: str) -> dict: ...
    def neighborhood(self, part_number: str, depth: int = 3, allowed_document_ids: set[str] | None = None) -> dict: ...
    def delete_document(self, document_id: str) -> dict: ...
