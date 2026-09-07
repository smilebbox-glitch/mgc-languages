from __future__ import annotations

from sqlalchemy.orm import Session


class NoOpGraphProjectionAdapter:
    mode = "disabled"

    def sync_part(self, db: Session, part_number: str) -> dict:
        return {"enabled": False, "synced": 0, "adapter": self.mode}

    def neighborhood(self, part_number: str, depth: int = 3, allowed_document_ids: set[str] | None = None) -> dict:
        return {"enabled": False, "nodes": [], "edges": [], "adapter": self.mode}

    def delete_document(self, document_id: str) -> dict:
        return {"enabled": False, "deleted": 0, "adapter": self.mode}


class Neo4jGraphProjectionAdapter:
    mode = "neo4j_projection"

    def sync_part(self, db: Session, part_number: str) -> dict:
        from app.services.graph_store import sync_part
        return sync_part(db, part_number)

    def neighborhood(self, part_number: str, depth: int = 3, allowed_document_ids: set[str] | None = None) -> dict:
        from app.services.graph_store import neighborhood
        return neighborhood(part_number, depth, allowed_document_ids)

    def delete_document(self, document_id: str) -> dict:
        from app.services.graph_store import delete_document_projection
        return delete_document_projection(document_id)
