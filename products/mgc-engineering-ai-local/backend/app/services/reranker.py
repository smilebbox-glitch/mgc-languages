from functools import lru_cache
from pathlib import Path

from app.core.config import get_settings


@lru_cache
def _model():
    cfg = get_settings()
    if not cfg.reranker_enabled or not cfg.reranker_model:
        return None
    model_path = cfg.reranker_model
    if cfg.air_gapped_mode:
        path = Path(model_path)
        if not path.is_absolute() or not path.exists() or not path.is_dir():
            raise RuntimeError(
                f"AIR_GAPPED_MODE requires a local reranker directory; got {model_path!r}."
            )
        model_path = str(path)
    from sentence_transformers import CrossEncoder
    return CrossEncoder(model_path)


def rerank(query: str, hits: list[dict], limit: int) -> list[dict]:
    model = _model()
    if model is None or not hits:
        return hits[:limit]
    pairs = [(query, h.get("text", "")) for h in hits]
    scores = model.predict(pairs)
    out = []
    for hit, score in zip(hits, scores):
        row = dict(hit)
        row["retrieval_score"] = float(row.get("score", 0.0))
        row["rerank_score"] = float(score)
        row["score"] = float(score)
        out.append(row)
    out.sort(key=lambda x: x["score"], reverse=True)
    return out[:limit]
