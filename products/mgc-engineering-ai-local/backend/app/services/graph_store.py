from functools import lru_cache
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.models import BOMItem, Document, Relationship


@lru_cache
def driver():
    cfg = get_settings()
    if not cfg.graph_enabled:
        return None
    from neo4j import GraphDatabase
    return GraphDatabase.driver(cfg.neo4j_uri, auth=(cfg.neo4j_user, cfg.neo4j_password))


def sync_part(db: Session, part_number: str) -> dict:
    drv = driver()
    if drv is None:
        return {"enabled": False, "synced": 0}
    pn = part_number.upper()
    docs = db.scalars(select(Document).where(Document.part_number == pn)).all()
    bom = db.scalars(select(BOMItem).where(BOMItem.parent_part_number == pn)).all()
    rels = db.scalars(select(Relationship).where((Relationship.subject_id == pn) | (Relationship.object_id == pn))).all()
    with drv.session() as s:
        # Replacement projection: remove relationships owned by this projection before MERGE.
        # A retry therefore converges to the same graph instead of accumulating stale edges.
        s.run("MERGE (p:Part {part_number:$pn}) WITH p OPTIONAL MATCH (p)-[r:HAS_DOCUMENT|CONTAINS]->() DELETE r", pn=pn)
        for d in docs:
            s.run("MERGE (x:Document {id:$id}) SET x.filename=$filename, x.revision=$revision, x.doc_type=$doc_type MERGE (p:Part {part_number:$pn}) MERGE (p)-[:HAS_DOCUMENT]->(x)", id=d.id, filename=d.filename, revision=d.revision, doc_type=d.doc_type, pn=pn)
        for item in bom:
            s.run("MERGE (p:Part {part_number:$parent}) MERGE (c:Part {part_number:$child}) MERGE (p)-[r:CONTAINS]->(c) SET r.quantity=$qty", parent=pn, child=item.child_part_number, qty=item.quantity)
    return {"enabled": True, "documents": len(docs), "bom_edges": len(bom), "relationships_seen": len(rels)}


def neighborhood(part_number: str, depth: int = 3, allowed_document_ids: set[str] | None = None) -> dict:
    drv = driver()
    if drv is None:
        return {"enabled": False, "nodes": [], "edges": []}
    depth = max(1, min(int(depth), 5))
    query = f"MATCH p=(a:Part {{part_number:$pn}})-[*1..{depth}]-(b) RETURN p LIMIT 250"
    nodes, edges = {}, {}
    with drv.session() as s:
        for rec in s.run(query, pn=part_number.upper()):
            path = rec["p"]
            for n in path.nodes:
                nid = n.element_id
                nodes[nid] = {"id": nid, "labels": list(n.labels), "properties": dict(n)}
            for r in path.relationships:
                rid = r.element_id
                edges[rid] = {"id": rid, "type": r.type, "start": r.start_node.element_id, "end": r.end_node.element_id, "properties": dict(r)}
    node_rows = list(nodes.values())
    edge_rows = list(edges.values())
    if allowed_document_ids is not None:
        removed = {n["id"] for n in node_rows if "Document" in n.get("labels", []) and str((n.get("properties") or {}).get("id")) not in allowed_document_ids}
        node_rows = [n for n in node_rows if n["id"] not in removed]
        edge_rows = [e for e in edge_rows if e["start"] not in removed and e["end"] not in removed]
    return {"enabled": True, "nodes": node_rows, "edges": edge_rows}


def delete_document_projection(document_id: str) -> dict:
    """Delete only the rebuildable Neo4j Document projection; PostgreSQL evidence is untouched."""
    drv = driver()
    if drv is None:
        return {"enabled": False, "deleted": 0}
    with drv.session() as session:
        rec = session.run("MATCH (d:Document {id:$id}) DETACH DELETE d RETURN 1 AS deleted", id=document_id).single()
    return {"enabled": True, "deleted": 1 if rec else 0}
