from __future__ import annotations

import re

from sqlalchemy import or_, select

from app.db.models import Document
from app.db.session import SessionLocal


class CoreMetadataSearchAdapter:
    """Deterministic Core lexical search over PostgreSQL-authoritative chunks + metadata."""

    mode = "core_lexical_postgres"

    def index_chunks(self, document: dict, chunks: list[str]) -> int:
        # Authoritative chunks are persisted by the application service, not this adapter.
        return len(chunks)

    def delete_document(self, document_id: str) -> None:
        return None

    def search(self, query: str, limit: int, acl_groups: list[str], part_number=None, revision=None,
               doc_type=None, project_code=None, manufacturing_area=None) -> list[dict]:
        from app.db.models import DocumentSearchChunk
        q = (query or "").strip().lower()
        tokens = [x for x in re.findall(r"[^\W_]{2,}|[A-Za-z0-9_.\-/]{2,}", q, flags=re.UNICODE) if x]
        with SessionLocal() as db:
            stmt = select(Document, DocumentSearchChunk).join(DocumentSearchChunk, DocumentSearchChunk.document_id == Document.id)
            if part_number: stmt = stmt.where(Document.part_number == part_number)
            if revision: stmt = stmt.where(Document.revision == revision)
            if doc_type: stmt = stmt.where(Document.doc_type == doc_type)
            if project_code: stmt = stmt.where(Document.project_code == project_code)
            if manufacturing_area: stmt = stmt.where(Document.manufacturing_area == manufacturing_area)
            if tokens:
                stmt = stmt.where(or_(*[DocumentSearchChunk.text.ilike(f"%{token}%") for token in tokens[:8]]))
            rows = db.execute(stmt.order_by(Document.updated_at.desc(), DocumentSearchChunk.chunk_index).limit(max(limit * 8, 80))).all()

        groups = set(acl_groups or []) | {"all"}
        hits = []
        for d, chunk in rows:
            if not (set(d.acl_groups or ["all"]) & groups):
                continue
            hay = f"{d.filename} {d.part_number or ''} {d.revision or ''} {d.doc_type or ''} {chunk.text}".lower()
            matches = sum(1 for token in tokens if token.lower() in hay)
            phrase_bonus = 0.25 if q and q in hay else 0.0
            score = min(0.25 + matches * 0.12 + phrase_bonus, 0.95)
            hits.append({
                "score": round(score, 4), "document_id": d.id, "filename": d.filename,
                "chunk_index": chunk.chunk_index, "text": chunk.text, "page": None,
                "part_number": d.part_number, "revision": d.revision, "doc_type": d.doc_type,
                "project_code": d.project_code, "manufacturing_area": d.manufacturing_area,
                "metadata": {**(d.extracted_metadata or {}), "retrieval_mode": self.mode, "semantic_search": False},
            })
        # Preserve metadata discovery for legacy documents that have not yet been backfilled.
        if len(hits) < limit:
            with SessionLocal() as db:
                stmt = select(Document)
                if part_number: stmt = stmt.where(Document.part_number == part_number)
                if revision: stmt = stmt.where(Document.revision == revision)
                if doc_type: stmt = stmt.where(Document.doc_type == doc_type)
                if project_code: stmt = stmt.where(Document.project_code == project_code)
                if manufacturing_area: stmt = stmt.where(Document.manufacturing_area == manufacturing_area)
                if tokens:
                    clauses = []
                    for token in tokens[:8]:
                        pat = f"%{token}%"
                        clauses.extend([Document.filename.ilike(pat), Document.part_number.ilike(pat), Document.revision.ilike(pat), Document.doc_type.ilike(pat)])
                    stmt = stmt.where(or_(*clauses))
                docs = db.scalars(stmt.order_by(Document.updated_at.desc()).limit(max(limit * 4, 40))).all()
            seen = {(x["document_id"], x["chunk_index"]) for x in hits}
            for d in docs:
                if not (set(d.acl_groups or ["all"]) & groups):
                    continue
                key = (d.id, -1)
                if key in seen:
                    continue
                hay = " ".join(str(x or "") for x in [d.filename, d.part_number, d.revision, d.doc_type]).lower()
                score = 0.2 + min(sum(0.1 for t in tokens if t.lower() in hay), 0.5)
                hits.append({
                    "score": round(score, 4), "document_id": d.id, "filename": d.filename,
                    "chunk_index": -1, "text": f"Metadata evidence: file={d.filename}; part={d.part_number or '-'}; revision={d.revision or '-'}; type={d.doc_type or '-'}.",
                    "page": None, "part_number": d.part_number, "revision": d.revision, "doc_type": d.doc_type,
                    "project_code": d.project_code, "manufacturing_area": d.manufacturing_area,
                    "metadata": {**(d.extracted_metadata or {}), "retrieval_mode": self.mode, "semantic_search": False, "legacy_metadata_fallback": True},
                })
        hits.sort(key=lambda x: (-x["score"], x["filename"], x["chunk_index"]))
        return hits[:limit]


class QdrantSearchAdapter:
    """Semantic projection adapter. Concrete Qdrant imports stay behind this boundary."""

    mode = "qdrant_semantic"

    def index_chunks(self, document: dict, chunks: list[str]) -> int:
        from app.services.vector_store import index_chunks
        return index_chunks(document, chunks)

    def delete_document(self, document_id: str) -> None:
        from app.services.vector_store import delete_document
        return delete_document(document_id)

    def search(self, query: str, limit: int, acl_groups: list[str], part_number=None, revision=None,
               doc_type=None, project_code=None, manufacturing_area=None) -> list[dict]:
        from app.services.vector_store import search
        return search(query, limit, acl_groups, part_number, revision, doc_type, project_code, manufacturing_area)
