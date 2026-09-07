from functools import lru_cache
from pathlib import Path

from app.core.config import get_settings

BUCKET = "engineering-evidence"


@lru_cache
def _client():
    cfg = get_settings()
    if not cfg.object_store_enabled:
        return None
    from minio import Minio
    return Minio(cfg.minio_endpoint, access_key=cfg.minio_access_key, secret_key=cfg.minio_secret_key, secure=cfg.minio_secure)


def mirror_file(path: Path, object_name: str) -> dict | None:
    client = _client()
    if client is None:
        return None
    if not client.bucket_exists(BUCKET):
        client.make_bucket(BUCKET)
    client.fput_object(BUCKET, object_name, str(path))
    stat = client.stat_object(BUCKET, object_name)
    return {"bucket": BUCKET, "object_name": object_name, "etag": stat.etag, "size": stat.size}
