from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.runtime_contract import OBJECT_TYPE_CAPABILITIES, available_object_types, context_for_capability, runtime_contract
from app.core.security import Identity, get_identity
from app.db.models import Document
from app.db.session import get_db
from app.platform.connectors import connector_contract
from app.services.object360 import SUPPORTED_OBJECT_TYPES, object360
from app.services.read_models import acl_fingerprint, cache_key, etag_for_payload, pending_read_model_invalidation, redis_cache_get, redis_cache_set

router = APIRouter(tags=["Simplified Platform"])


def _visible_document_ids(db: Session, identity: Identity) -> set[str]:
    groups = set(identity.groups or []) | {"all"}
    return {d.id for d in db.scalars(select(Document)).all() if set(d.acl_groups or ["all"]) & groups}


@router.get("/runtime")
def get_runtime(identity: Identity = Depends(get_identity)):
    # Identity is deliberate: capability posture may reveal installed modules/dependencies.
    return runtime_contract(get_settings())


@router.get("/connector-contract")
def get_connector_contract(identity: Identity = Depends(get_identity)):
    return connector_contract()


@router.get("/objects")
def object_types(identity: Identity = Depends(get_identity)):
    features = get_settings().runtime_features
    types = available_object_types(features)
    return {
        "schema": "mgc-object360-catalog-v1",
        "types": types,
        "primary_navigation": types,
        "items": [
            {"type": kind, "capability": OBJECT_TYPE_CAPABILITIES[kind], "context": context_for_capability(OBJECT_TYPE_CAPABILITIES[kind])}
            for kind in types
        ],
    }


@router.get("/objects/{object_type}/{object_id:path}")
def get_object360(object_type: str, object_id: str, request: Request, response: Response, identity: Identity = Depends(get_identity), db: Session = Depends(get_db)):
    visible = _visible_document_ids(db, identity)
    cfg = get_settings()
    identity_key = acl_fingerprint(visible, identity.groups)
    key = cache_key("object360", identity_key, cfg.runtime_profile, object_type.lower(), object_id)
    pending = pending_read_model_invalidation(db)
    payload = None if pending else redis_cache_get(key, surface="object360")
    cache_state = "redis_hit" if payload is not None else ("bypass_pending_invalidation" if pending else "miss")
    if payload is None:
        payload = object360(db, object_type, object_id, visible, identity.groups, cfg.runtime_features)
        if payload is None:
            raise HTTPException(404, "Object not found or not visible")
        if not pending:
            redis_cache_set(key, payload, ttl=cfg.object360_cache_ttl_seconds, surface="object360")
    etag = etag_for_payload(payload)
    headers = {"ETag": etag, "Cache-Control": "private, no-cache", "X-MGC-Cache": cache_state}
    if request.headers.get("if-none-match") == etag:
        return Response(status_code=304, headers=headers)
    response.headers.update(headers)
    return payload
