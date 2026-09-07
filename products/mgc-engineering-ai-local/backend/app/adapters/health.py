from __future__ import annotations


def probe_qdrant() -> None:
    from qdrant_client import QdrantClient
    from app.core.config import get_settings
    cfg = get_settings()
    QdrantClient(url=cfg.qdrant_url, timeout=cfg.health_timeout_seconds).get_collections()


def probe_neo4j() -> None:
    from neo4j import GraphDatabase
    from app.core.config import get_settings
    cfg = get_settings()
    drv = GraphDatabase.driver(
        cfg.neo4j_uri,
        auth=(cfg.neo4j_user, cfg.neo4j_password),
        connection_timeout=cfg.health_timeout_seconds,
    )
    try:
        drv.verify_connectivity()
    finally:
        drv.close()


def probe_object_store() -> None:
    from minio import Minio
    from app.core.config import get_settings
    cfg = get_settings()
    client = Minio(
        cfg.minio_endpoint,
        access_key=cfg.minio_access_key,
        secret_key=cfg.minio_secret_key,
        secure=cfg.minio_secure,
    )
    client.list_buckets()
