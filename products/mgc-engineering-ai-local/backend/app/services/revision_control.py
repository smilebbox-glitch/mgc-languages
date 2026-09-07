from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models import (
    ChangeApproval,
    EditConflictEvent,
    EngineeringRevisionSnapshot,
    ManufacturingLayout,
    StationLayoutPlacement,
    WorkInstruction,
    WriteIdempotencyRecord,
)


def _jsonable(value: Any):
    if isinstance(value, datetime):
        return value.astimezone(timezone.utc).isoformat()
    if isinstance(value, dict):
        return {str(k): _jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(v) for v in value]
    return value


def row_snapshot(row) -> dict:
    """Serialize mapped columns only; relationships are deliberately excluded."""
    payload: dict[str, Any] = {}
    for column in row.__table__.columns:
        payload[column.name] = _jsonable(getattr(row, column.name))
    return payload


def snapshot_hash(payload: dict) -> str:
    canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def record_snapshot(db: Session, row, entity_type: str, *, user: str, reason: str | None = None) -> EngineeringRevisionSnapshot:
    payload = row_snapshot(row)
    version = int(getattr(row, "row_version", 1) or 1)
    existing = db.scalar(select(EngineeringRevisionSnapshot).where(
        EngineeringRevisionSnapshot.entity_type == entity_type,
        EngineeringRevisionSnapshot.entity_id == str(row.id),
        EngineeringRevisionSnapshot.row_version == version,
    ))
    if existing:
        return existing
    snap = EngineeringRevisionSnapshot(
        entity_type=entity_type,
        entity_id=str(row.id),
        project_code=getattr(row, "project_code", None),
        manufacturing_area=getattr(row, "manufacturing_area", None),
        business_code=getattr(row, "code", None),
        business_revision=getattr(row, "revision", None),
        row_version=version,
        snapshot_json=payload,
        snapshot_sha256=snapshot_hash(payload),
        reason=reason,
        created_by=user,
    )
    db.add(snap)
    return snap


def _flatten(value: Any, prefix: str = "") -> dict[str, Any]:
    if isinstance(value, dict):
        out: dict[str, Any] = {}
        for key, child in value.items():
            p = f"{prefix}.{key}" if prefix else str(key)
            out.update(_flatten(child, p))
        return out
    return {prefix: value}


def visual_diff(left: dict, right: dict, *, ignore: set[str] | None = None) -> dict:
    ignore = ignore or {"id", "created_at", "updated_at", "row_version"}
    lf, rf = _flatten(left), _flatten(right)
    changes = []
    for key in sorted(set(lf) | set(rf)):
        root = key.split(".", 1)[0]
        if root in ignore:
            continue
        a, b = lf.get(key), rf.get(key)
        if a != b:
            changes.append({"field": key, "from": a, "to": b})
    return {"changed": bool(changes), "change_count": len(changes), "changes": changes}


def work_instruction_diff(left: WorkInstruction, right: WorkInstruction) -> dict:
    diff = visual_diff(row_snapshot(left), row_snapshot(right))
    diff.update({
        "entity_type": "work_instruction",
        "left": {"id": left.id, "code": left.code, "revision": left.revision, "status": left.status, "row_version": left.row_version},
        "right": {"id": right.id, "code": right.code, "revision": right.revision, "status": right.status, "row_version": right.row_version},
        "human_review_required": True,
        "auto_merge": False,
    })
    return diff


def layout_diff(db: Session, left: ManufacturingLayout, right: ManufacturingLayout) -> dict:
    left_payload = row_snapshot(left)
    right_payload = row_snapshot(right)
    def placements(layout_id: str):
        rows = db.scalars(select(StationLayoutPlacement).where(StationLayoutPlacement.layout_id == layout_id).order_by(StationLayoutPlacement.station_id)).all()
        return [{"station_id": r.station_id, "x_pct": r.x_pct, "y_pct": r.y_pct, "width_pct": r.width_pct, "height_pct": r.height_pct, "rotation_deg": r.rotation_deg, "label_override": r.label_override} for r in rows]
    left_payload["placements"] = placements(left.id)
    right_payload["placements"] = placements(right.id)
    diff = visual_diff(left_payload, right_payload)
    diff.update({
        "entity_type": "manufacturing_layout",
        "left": {"id": left.id, "code": left.code, "revision": left.revision, "status": left.status, "row_version": left.row_version},
        "right": {"id": right.id, "code": right.code, "revision": right.revision, "status": right.status, "row_version": right.row_version},
        "human_review_required": True,
        "auto_merge": False,
    })
    return diff


def clone_work_instruction(db: Session, source: WorkInstruction, *, new_revision: str, user: str, reason: str) -> WorkInstruction:
    record_snapshot(db, source, "work_instruction", user=user, reason="source_before_revision")
    foreign = source.source_language not in {"ru", "auto"}
    meta = dict(source.metadata_json or {})
    meta["revision_lineage"] = {"source_instruction_id": source.id, "source_revision": source.revision, "reason": reason, "created_by": user}
    for key in ("translation_review", "translation_source_fingerprint", "translation_stale", "translation_stale_reason"):
        meta.pop(key, None)
    row = WorkInstruction(
        project_code=source.project_code, manufacturing_area=source.manufacturing_area,
        line_id=source.line_id, station_id=source.station_id, operation_id=source.operation_id,
        code=source.code, title=source.title, revision=new_revision.upper(), status="draft",
        instruction_type=source.instruction_type, source_type=source.source_type,
        source_language=source.source_language, source_factory=source.source_factory,
        source_document_id=source.source_document_id, original_text=source.original_text,
        translated_text_ru=None if foreign else source.translated_text_ru,
        translation_status="stale" if foreign else "not_required",
        steps_json=list(source.steps_json or []), translated_steps_json=[] if foreign else list(source.translated_steps_json or []),
        safety_points_json=list(source.safety_points_json or []), quality_points_json=list(source.quality_points_json or []),
        tools_json=list(source.tools_json or []), ppe_json=list(source.ppe_json or []), required_skill=source.required_skill,
        operator_role=source.operator_role, cycle_time_sec=source.cycle_time_sec, owner=user, created_by=user,
        approved_by=None, evidence_document_ids=list(source.evidence_document_ids or []), metadata_json=meta,
    )
    db.add(row); db.flush()
    record_snapshot(db, row, "work_instruction", user=user, reason="new_revision_created")
    return row


def clone_layout(db: Session, source: ManufacturingLayout, *, new_revision: str, user: str, reason: str) -> tuple[ManufacturingLayout, list[StationLayoutPlacement]]:
    record_snapshot(db, source, "manufacturing_layout", user=user, reason="source_before_revision")
    meta = dict(source.metadata_json or {})
    meta["revision_lineage"] = {"source_layout_id": source.id, "source_revision": source.revision, "reason": reason, "created_by": user}
    row = ManufacturingLayout(
        project_code=source.project_code, manufacturing_area=source.manufacturing_area, line_id=source.line_id,
        code=source.code, title=source.title, revision=new_revision.upper(), status="draft",
        source_document_id=source.source_document_id, owner=user, created_by=user, metadata_json=meta,
    )
    db.add(row); db.flush()
    copied=[]
    for old in db.scalars(select(StationLayoutPlacement).where(StationLayoutPlacement.layout_id == source.id)).all():
        new = StationLayoutPlacement(layout_id=row.id, station_id=old.station_id, x_pct=old.x_pct, y_pct=old.y_pct,
                                     width_pct=old.width_pct, height_pct=old.height_pct, rotation_deg=old.rotation_deg,
                                     label_override=old.label_override, metadata_json=dict(old.metadata_json or {}))
        db.add(new); copied.append(new)
    db.flush()
    record_snapshot(db, row, "manufacturing_layout", user=user, reason="new_revision_created")
    return row, copied


def _request_hash(payload: dict) -> str:
    return snapshot_hash(_jsonable(payload))


def idempotency_lookup(db: Session, *, user: str, route_key: str, key: str | None, request_payload: dict) -> dict | None:
    if not isinstance(key, str) or not key:
        return None
    normalized = key.strip()
    if not normalized or len(normalized) > 128:
        raise ValueError("Idempotency-Key must be 1..128 characters")
    row = db.scalar(select(WriteIdempotencyRecord).where(
        WriteIdempotencyRecord.user == user,
        WriteIdempotencyRecord.route_key == route_key,
        WriteIdempotencyRecord.idempotency_key == normalized,
    ))
    if not row:
        return None
    digest = _request_hash(request_payload)
    if row.request_sha256 != digest:
        raise ValueError("Idempotency-Key was already used with a different request")
    return row.response_json or {}


def store_idempotency(db: Session, *, user: str, route_key: str, key: str | None, request_payload: dict, response: dict, entity_type: str | None = None, entity_id: str | None = None) -> None:
    if not isinstance(key, str) or not key:
        return
    db.add(WriteIdempotencyRecord(
        user=user, route_key=route_key, idempotency_key=key.strip(), request_sha256=_request_hash(request_payload),
        response_json=_jsonable(response), entity_type=entity_type, entity_id=entity_id,
    ))


def integrity_dashboard(db: Session) -> dict:
    conflicts = int(db.scalar(select(func.count()).select_from(EditConflictEvent)) or 0)
    idempotent = int(db.scalar(select(func.count()).select_from(WriteIdempotencyRecord)) or 0)
    snapshots = int(db.scalar(select(func.count()).select_from(EngineeringRevisionSnapshot)) or 0)
    duplicate_approval_groups = db.execute(select(
        func.count().label("n")
    ).select_from(ChangeApproval).group_by(
        ChangeApproval.change_id, ChangeApproval.stage,
    ).having(func.count() > 1)).all()
    stale_translation = int(db.scalar(select(func.count()).select_from(WorkInstruction).where(WorkInstruction.translation_status == "stale")) or 0)
    return {
        "status": "AMBER" if duplicate_approval_groups else "GREEN",
        "edit_conflicts_total": conflicts,
        "idempotent_write_receipts": idempotent,
        "revision_snapshots": snapshots,
        "duplicate_change_approval_groups": len(duplicate_approval_groups),
        "stale_work_instruction_translations": stale_translation,
        "auto_merge_enabled": False,
        "human_conflict_resolution_required": True,
    }
