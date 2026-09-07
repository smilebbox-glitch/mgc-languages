from __future__ import annotations

import hashlib
import uuid
from sqlalchemy import event
from sqlalchemy.orm import Session as SASession

from app.core.config import get_settings
from app.db.models import (
    BOMItem, ChangeRequest, Document, ManufacturingLayout, ManufacturingLine,
    ProcessOperation, ProcessStation, Project, ProjectArea, ProjectionOutboxEvent,
    StationLayoutPlacement, WorkInstruction,
)

_TRACKED = (Project, ProjectArea, Document, BOMItem, ChangeRequest, ManufacturingLine, ProcessStation, ProcessOperation, WorkInstruction, ManufacturingLayout, StationLayoutPlacement)
_INSTALLED = False


def _scope(obj) -> tuple[str | None, str | None]:
    return (getattr(obj, "project_code", None), getattr(obj, "manufacturing_area", None))


def install_read_model_invalidation_hooks() -> None:
    global _INSTALLED
    if _INSTALLED:
        return
    _INSTALLED = True

    @event.listens_for(SASession, "before_flush")
    def _collect(session, flush_context, instances):
        if not get_settings().read_model_enabled or not session.info.get("mgc_read_model_invalidation_enabled"):
            return
        changed = [x for x in list(session.new) + list(session.dirty) + list(session.deleted) if isinstance(x, _TRACKED)]
        if not changed:
            return
        scopes = session.info.setdefault("mgc_read_model_invalidation_scopes", set())
        for obj in changed:
            scopes.add(_scope(obj))

    @event.listens_for(SASession, "after_flush_postexec")
    def _enqueue(session, flush_context):
        scopes = session.info.pop("mgc_read_model_invalidation_scopes", set())
        if not scopes:
            return
        for project_code, area in sorted(scopes, key=lambda x: (str(x[0]), str(x[1]))):
            nonce = uuid.uuid4().hex
            raw = f"read_model|{project_code or '*'}|{area or '*'}|{nonce}"
            session.add(ProjectionOutboxEvent(
                idempotency_key=hashlib.sha256(raw.encode()).hexdigest(),
                target="read_model",
                event_type="read_model_invalidate",
                aggregate_type="read_model",
                aggregate_id=f"{project_code or '*'}:{area or '*'}",
                source_version=nonce,
                payload_json={"project_code": project_code, "manufacturing_area": area, "cache_prefix": "mgc:v6310:"},
                status="pending",
                max_attempts=max(1, int(get_settings().projection_max_attempts)),
            ))
