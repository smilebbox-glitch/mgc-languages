from __future__ import annotations

from sqlalchemy.orm import Session

from app.adapters.registry import get_graph_projection_port, get_search_port


def search(query: str, limit: int, acl_groups: list[str], part_number=None, revision=None,
           doc_type=None, project_code=None, manufacturing_area=None) -> list[dict]:
    return get_search_port().search(
        query, limit, acl_groups, part_number, revision, doc_type, project_code, manufacturing_area
    )


def graph_sync_part(db: Session, part_number: str) -> dict:
    return get_graph_projection_port().sync_part(db, part_number)


def graph_neighborhood(part_number: str, depth: int = 3, allowed_document_ids: set[str] | None = None) -> dict:
    return get_graph_projection_port().neighborhood(part_number, depth, allowed_document_ids)
