from functools import lru_cache
from pathlib import Path
import hashlib
import re
import uuid

from app.core.config import get_settings
from app.services.reranker import rerank
from app.core.resilience import circuit_allows, record_failure, record_success


def _local_model_path(value: str, role: str) -> str:
    cfg = get_settings()
    if not cfg.air_gapped_mode:
        return value
    path = Path(value)
    if not path.is_absolute() or not path.exists() or not path.is_dir():
        raise RuntimeError(
            f"AIR_GAPPED_MODE requires a local {role} directory; got {value!r}. "
            "Stage model weights under /models before starting indexing."
        )
    return str(path)


@lru_cache
def embedding_model():
    from sentence_transformers import SentenceTransformer
    cfg = get_settings()
    return SentenceTransformer(_local_model_path(cfg.embedding_model, "embedding model"))


@lru_cache
def qdrant():
    from qdrant_client import QdrantClient
    return QdrantClient(url=get_settings().qdrant_url, timeout=90)

def _qdrant_models():
    from qdrant_client import models
    return models


def _fallback_search(query: str, limit: int, acl_groups: list[str], part_number=None, revision=None, doc_type=None, project_code=None, manufacturing_area=None) -> list[dict]:
    """Deterministic PostgreSQL/SQLite metadata fallback for Core profile.

    It intentionally does not pretend to be semantic retrieval. It preserves useful exact/lexical
    discovery when Qdrant/embeddings are disabled or unavailable.
    """
    from sqlalchemy import or_, select
    from app.db.models import Document
    from app.db.session import SessionLocal

    q = (query or "").strip().lower()
    tokens = [x for x in re.findall(r"[a-zA-Z0-9_.\-/]{2,}", q) if x]
    with SessionLocal() as db:
        stmt = select(Document)
        if part_number: stmt = stmt.where(Document.part_number == part_number)
        if revision: stmt = stmt.where(Document.revision == revision)
        if doc_type: stmt = stmt.where(Document.doc_type == doc_type)
        if project_code: stmt = stmt.where(Document.project_code == project_code)
        if manufacturing_area: stmt = stmt.where(Document.manufacturing_area == manufacturing_area)
        if tokens:
            clauses=[]
            for token in tokens[:8]:
                pat=f"%{token}%"
                clauses.extend([Document.filename.ilike(pat), Document.part_number.ilike(pat), Document.revision.ilike(pat), Document.doc_type.ilike(pat)])
            stmt = stmt.where(or_(*clauses))
        docs = db.scalars(stmt.order_by(Document.updated_at.desc()).limit(max(limit*5, 50))).all()

    groups=set(acl_groups or []) | {"all"}
    hits=[]
    for d in docs:
        if not (set(d.acl_groups or ["all"]) & groups):
            continue
        hay=" ".join(str(x or "") for x in [d.filename,d.part_number,d.revision,d.doc_type]).lower()
        score=0.2 + min(sum(0.12 for t in tokens if t in hay), 0.6)
        meta=dict(d.extracted_metadata or {})
        text=f"Metadata evidence: file={d.filename}; part={d.part_number or '-'}; revision={d.revision or '-'}; type={d.doc_type or '-'}."
        hits.append({
            "score": round(score,4), "document_id": d.id, "filename": d.filename, "chunk_index": 0,
            "text": text, "page": None, "part_number": d.part_number, "revision": d.revision,
            "doc_type": d.doc_type, "project_code": d.project_code, "manufacturing_area": d.manufacturing_area,
            "metadata": {**meta, "retrieval_mode": "core_lexical_postgres", "semantic_search": False},
        })
    hits.sort(key=lambda x:(-x["score"],x["filename"]))
    return hits[:limit]


def _semantic_enabled() -> bool:
    return bool(get_settings().semantic_search_enabled)


def ensure_collection() -> None:
    cfg = get_settings()
    if not _semantic_enabled():
        return
    if not circuit_allows("qdrant"):
        raise RuntimeError("Qdrant circuit is open")
    models = _qdrant_models()
    client = qdrant()
    if client.collection_exists(cfg.qdrant_collection):
        record_success("qdrant")
        return
    client.create_collection(
        collection_name=cfg.qdrant_collection,
        vectors_config={"dense": models.VectorParams(size=cfg.embedding_dim, distance=models.Distance.COSINE)},
        sparse_vectors_config={"bm25": models.SparseVectorParams(modifier=models.Modifier.IDF)},
    )
    for field in ["document_id", "part_number", "revision", "doc_type", "project_code", "manufacturing_area", "acl_groups"]:
        try:
            client.create_payload_index(cfg.qdrant_collection, field, models.PayloadSchemaType.KEYWORD)
        except Exception:
            pass
    record_success("qdrant")


def index_chunks(document: dict, chunks: list[str]) -> int:
    if not _semantic_enabled() or not circuit_allows("qdrant"):
        return 0
    if not chunks:
        return 0
    try:
        ensure_collection()
        models = _qdrant_models()
        cfg = get_settings()
        vectors = embedding_model().encode(chunks, normalize_embeddings=True, show_progress_bar=False)
    except Exception as exc:
        record_failure("qdrant", exc)
        return 0
    points = []
    for index, (chunk, vector) in enumerate(zip(chunks, vectors)):
        payload = {
            "document_id": document["id"], "filename": document["filename"], "chunk_index": index,
            "text": chunk, "page": None, "part_number": document.get("part_number"),
            "revision": document.get("revision"), "doc_type": document.get("doc_type"),
            "project_code": document.get("project_code"), "manufacturing_area": document.get("manufacturing_area"), "acl_groups": document.get("acl_groups") or ["all"],
            "metadata": document.get("metadata") or {},
        }
        points.append(models.PointStruct(
            id=str(uuid.uuid5(uuid.NAMESPACE_URL, f"mgc:{document['id']}:{index}:{hashlib.sha256(chunk.encode('utf-8')).hexdigest()}")),
            vector={"dense": vector.tolist(), "bm25": models.Document(text=chunk, model="Qdrant/bm25")},
            payload=payload,
        ))
    try:
        qdrant().upsert(cfg.qdrant_collection, points=points, wait=True)
    except Exception as exc:
        record_failure("qdrant", exc)
        return 0
    record_success("qdrant")
    return len(points)


def delete_document(document_id: str) -> None:
    if not _semantic_enabled() or not circuit_allows("qdrant"):
        return
    try:
        ensure_collection()
        models = _qdrant_models()
        qdrant().delete(
            collection_name=get_settings().qdrant_collection,
            points_selector=models.FilterSelector(filter=models.Filter(must=[
                models.FieldCondition(key="document_id", match=models.MatchValue(value=document_id))
            ])), wait=True,
        )
    except Exception as exc:
        record_failure("qdrant", exc)
        return
    record_success("qdrant")


def _filter(groups: list[str], part_number=None, revision=None, doc_type=None, project_code=None, manufacturing_area=None):
    models = _qdrant_models()
    must = [models.FieldCondition(key="acl_groups", match=models.MatchAny(any=sorted(set(groups + ["all"]))))]
    for key, value in [("part_number", part_number), ("revision", revision), ("doc_type", doc_type), ("project_code", project_code)]:
        if value:
            must.append(models.FieldCondition(key=key, match=models.MatchValue(value=value)))
    if manufacturing_area:
        # Area-scoped AI is intentionally strict. Use "All areas" to search unclassified legacy evidence.
        must.append(models.FieldCondition(key="manufacturing_area", match=models.MatchValue(value=manufacturing_area)))
    return models.Filter(must=must)


def search(query: str, limit: int, acl_groups: list[str], part_number=None, revision=None, doc_type=None, project_code=None, manufacturing_area=None) -> list[dict]:
    if not _semantic_enabled() or not circuit_allows("qdrant"):
        return _fallback_search(query, limit, acl_groups, part_number, revision, doc_type, project_code, manufacturing_area)
    try:
        ensure_collection()
        models = _qdrant_models()
    except Exception as exc:
        record_failure("qdrant", exc)
        # Search enrichment is rebuildable/optional. Core engineering discovery must remain usable.
        return _fallback_search(query, limit, acl_groups, part_number, revision, doc_type, project_code, manufacturing_area)
    cfg = get_settings()
    dense = embedding_model().encode([query], normalize_embeddings=True, show_progress_bar=False)[0].tolist()
    filt = _filter(acl_groups, part_number, revision, doc_type, project_code, manufacturing_area)
    try:
        result = qdrant().query_points(
            collection_name=cfg.qdrant_collection,
            prefetch=[
                models.Prefetch(query=dense, using="dense", limit=max(limit * 4, 30), filter=filt),
                models.Prefetch(query=models.Document(text=query, model="Qdrant/bm25"), using="bm25", limit=max(limit * 4, 30), filter=filt),
            ],
            query=models.FusionQuery(fusion=models.Fusion.RRF), limit=max(limit * 2, 20), with_payload=True,
        )
    except Exception as exc:
        record_failure("qdrant", exc)
        return _fallback_search(query, limit, acl_groups, part_number, revision, doc_type, project_code, manufacturing_area)
    record_success("qdrant")
    qlow = query.lower()
    part_tokens = set(re.findall(r"[A-Z0-9][A-Z0-9_.\-/]{4,}", query.upper()))
    hits = []
    for p in result.points:
        payload = p.payload or {}
        score = float(p.score)
        pn = str(payload.get("part_number") or "")
        rev = str(payload.get("revision") or "")
        filename = str(payload.get("filename", ""))
        if pn and pn.upper() in part_tokens:
            score += 0.35
        if rev and re.search(rf"(?i)\b(?:rev(?:ision)?\s*)?{re.escape(rev)}\b", query):
            score += 0.08
        if filename.lower() in qlow:
            score += 0.08
        hits.append({
            "score": score, "document_id": str(payload.get("document_id", "")), "filename": filename,
            "chunk_index": int(payload.get("chunk_index", 0)), "text": str(payload.get("text", "")),
            "page": payload.get("page"), "part_number": payload.get("part_number"), "revision": payload.get("revision"),
            "doc_type": payload.get("doc_type"), "project_code": payload.get("project_code"), "manufacturing_area": payload.get("manufacturing_area"), "metadata": payload.get("metadata") or {},
        })
    hits.sort(key=lambda x: x["score"], reverse=True)
    return rerank(query, hits, limit)
