from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import (
    Document, ManufacturingLayout, ManufacturingLine, ProcessOperation, ProcessStation,
    StationLayoutPlacement, WorkInstruction,
)
from app.services.document_parser import parse_document
from app.services.engineering_translation import detect_language, translate_texts
from app.adapters.registry import get_ai_analysis_port, get_translation_provider_port
from app.ports.ai import AIAnalysisPort
from app.ports.translation import TranslationProviderPort



def instruction_translation_fingerprint(original_text: str | None, steps: list[dict] | None) -> str:
    """Stable fingerprint of the exact source content covered by translation.

    Reviewed translations are valid only while this fingerprint matches. This
    prevents a previously reviewed Russian translation from surviving edits to
    Chinese/English source steps.
    """
    payload = {
        "original_text": (original_text or "").strip(),
        "steps": [
            {
                "sequence": x.get("sequence"),
                "title": x.get("title"),
                "text": str(x.get("text") or "").strip(),
                "safety_note": x.get("safety_note"),
                "quality_note": x.get("quality_note"),
            }
            for x in (steps or [])
        ],
    }
    canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def current_translation_fingerprint(row: WorkInstruction) -> str:
    return instruction_translation_fingerprint(row.original_text, row.steps_json or [])


def translation_is_current(row: WorkInstruction) -> bool:
    stored = str((row.metadata_json or {}).get("translation_source_fingerprint") or "")
    return bool(stored and stored == current_translation_fingerprint(row))

def _dt(value):
    return value.isoformat() if value else None


def _visible_evidence(ids: list[str] | None, visible_document_ids: set[str]) -> list[str]:
    return [x for x in (ids or []) if x in visible_document_ids]


def deterministic_steps(text: str, limit: int = 60) -> list[dict]:
    raw = (text or "").replace("\r", "\n")
    lines = [re.sub(r"^\s*(?:[-•*]|\d+[.)]|[一二三四五六七八九十]+[、.])\s*", "", x).strip() for x in raw.split("\n")]
    lines = [x for x in lines if len(x) >= 4]
    if len(lines) < 2:
        lines = [x.strip() for x in re.split(r"(?<=[.!?。；;])\s+", raw) if len(x.strip()) >= 8]
    return [{"sequence": (i + 1) * 10, "title": None, "text": line[:8000], "media_document_ids": [], "safety_note": None, "quality_note": None, "expected_time_sec": None}
            for i, line in enumerate(lines[:limit])]


def instruction_completeness(row: WorkInstruction) -> dict:
    checks = {
        "station_linked": bool(row.station_id),
        "operation_or_work_content": bool(row.operation_id or (row.original_text or "").strip() or row.steps_json),
        "steps_present": bool(row.steps_json),
        "safety_defined": bool(row.safety_points_json or row.ppe_json),
        "quality_defined": bool(row.quality_points_json),
        "tools_defined": bool(row.tools_json),
        "operator_role_defined": bool(row.operator_role),
        "cycle_time_defined": row.cycle_time_sec is not None,
        "foreign_translation_reviewed": row.source_language in {"ru", "auto"} or row.translation_status == "reviewed",
    }
    weights = {
        "station_linked": 15, "operation_or_work_content": 15, "steps_present": 20,
        "safety_defined": 10, "quality_defined": 10, "tools_defined": 5,
        "operator_role_defined": 10, "cycle_time_defined": 5, "foreign_translation_reviewed": 10,
    }
    score = sum(weights[k] for k, ok in checks.items() if ok)
    gaps = [k for k, ok in checks.items() if not ok]
    return {"score": score, "checks": checks, "gaps": gaps, "advisory_only": True}


def serialize_instruction(row: WorkInstruction, visible_document_ids: set[str]) -> dict:
    return {
        "id": row.id, "row_version": row.row_version, "project_code": row.project_code, "manufacturing_area": row.manufacturing_area,
        "line_id": row.line_id, "station_id": row.station_id, "operation_id": row.operation_id,
        "code": row.code, "title": row.title, "revision": row.revision, "status": row.status,
        "instruction_type": row.instruction_type, "source_type": row.source_type,
        "source_language": row.source_language, "source_factory": row.source_factory,
        "source_document_id": row.source_document_id if not row.source_document_id or row.source_document_id in visible_document_ids else None,
        "original_text": row.original_text, "translated_text_ru": row.translated_text_ru,
        "translation_status": row.translation_status,
        "steps": row.steps_json or [], "translated_steps": row.translated_steps_json or [],
        "safety_points": row.safety_points_json or [], "quality_points": row.quality_points_json or [],
        "tools": row.tools_json or [], "ppe": row.ppe_json or [], "required_skill": row.required_skill,
        "operator_role": row.operator_role, "cycle_time_sec": row.cycle_time_sec, "owner": row.owner,
        "created_by": row.created_by, "approved_by": row.approved_by,
        "evidence_document_ids": _visible_evidence(row.evidence_document_ids, visible_document_ids),
        "metadata": row.metadata_json or {}, "completeness": instruction_completeness(row),
        "created_at": _dt(row.created_at), "updated_at": _dt(row.updated_at),
    }


def serialize_layout(row: ManufacturingLayout, visible_document_ids: set[str], placements: list[StationLayoutPlacement]) -> dict:
    return {
        "id": row.id, "row_version": row.row_version, "project_code": row.project_code, "manufacturing_area": row.manufacturing_area,
        "line_id": row.line_id, "code": row.code, "title": row.title, "revision": row.revision,
        "status": row.status, "source_document_id": row.source_document_id if not row.source_document_id or row.source_document_id in visible_document_ids else None,
        "owner": row.owner, "metadata": row.metadata_json or {},
        "placements": [{"id": x.id, "station_id": x.station_id, "x_pct": x.x_pct, "y_pct": x.y_pct,
                        "width_pct": x.width_pct, "height_pct": x.height_pct, "rotation_deg": x.rotation_deg,
                        "label_override": x.label_override, "metadata": x.metadata_json or {}} for x in placements],
        "created_at": _dt(row.created_at), "updated_at": _dt(row.updated_at),
    }


def workspace(
    db: Session,
    project_code: str,
    manufacturing_area: str,
    visible_document_ids: set[str],
) -> dict:
    lines = db.scalars(select(ManufacturingLine).where(
        ManufacturingLine.project_code == project_code,
        ManufacturingLine.manufacturing_area == manufacturing_area,
    ).order_by(ManufacturingLine.code)).all()
    line_ids = {x.id for x in lines}
    stations = [x for x in db.scalars(select(ProcessStation).order_by(ProcessStation.sequence, ProcessStation.code)).all() if x.line_id in line_ids]
    station_ids = {x.id for x in stations}
    operations = [x for x in db.scalars(select(ProcessOperation).order_by(ProcessOperation.sequence, ProcessOperation.code)).all() if x.station_id in station_ids]
    instructions = db.scalars(select(WorkInstruction).where(
        WorkInstruction.project_code == project_code,
        WorkInstruction.manufacturing_area == manufacturing_area,
    ).order_by(WorkInstruction.updated_at.desc())).all()
    instructions = [x for x in instructions if not x.source_document_id or x.source_document_id in visible_document_ids]
    layouts = db.scalars(select(ManufacturingLayout).where(
        ManufacturingLayout.project_code == project_code,
        ManufacturingLayout.manufacturing_area == manufacturing_area,
    ).order_by(ManufacturingLayout.updated_at.desc())).all()
    layouts = [x for x in layouts if not x.source_document_id or x.source_document_id in visible_document_ids]
    layout_ids = {x.id for x in layouts}
    placements = [x for x in db.scalars(select(StationLayoutPlacement)).all() if x.layout_id in layout_ids and x.station_id in station_ids]
    placement_by_layout: dict[str, list[StationLayoutPlacement]] = {}
    for x in placements:
        placement_by_layout.setdefault(x.layout_id, []).append(x)

    inst_by_station: dict[str, list[WorkInstruction]] = {}
    inst_by_operation: dict[str, list[WorkInstruction]] = {}
    for item in instructions:
        if item.station_id:
            inst_by_station.setdefault(item.station_id, []).append(item)
        if item.operation_id:
            inst_by_operation.setdefault(item.operation_id, []).append(item)
    ops_by_station: dict[str, list[ProcessOperation]] = {}
    for op in operations:
        ops_by_station.setdefault(op.station_id, []).append(op)

    station_rows = []
    for station in stations:
        own = inst_by_station.get(station.id, [])
        inherited = [i for op in ops_by_station.get(station.id, []) for i in inst_by_operation.get(op.id, []) if i not in own]
        linked = own + inherited
        station_rows.append({
            "id": station.id, "row_version": station.row_version, "line_id": station.line_id, "code": station.code, "name": station.name,
            "sequence": station.sequence, "owner": station.owner, "operator_role": station.operator_role,
            "headcount": station.headcount, "work_content": station.work_content, "takt_time_sec": station.takt_time_sec,
            "status": station.status, "operation_count": len(ops_by_station.get(station.id, [])),
            "instruction_count": len(linked), "approved_instruction_count": sum(x.status == "approved" for x in linked),
            "foreign_instruction_count": sum(x.source_language not in {"ru", "auto"} for x in linked),
        })
    station_with_any = {x.station_id for x in instructions if x.station_id} | {op.station_id for op in operations if any(i.operation_id == op.id for i in instructions)}
    station_with_approved = {x.station_id for x in instructions if x.station_id and x.status == "approved"}
    station_with_approved |= {op.station_id for op in operations if any(i.operation_id == op.id and i.status == "approved" for i in instructions)}
    station_count = len(stations)
    return {
        "project_code": project_code, "manufacturing_area": manufacturing_area,
        "strict_area_scope": True, "operator_execution_authority": False,
        "counts": {
            "lines": len(lines), "stations": station_count, "operations": len(operations), "instructions": len(instructions),
            "approved_instructions": sum(x.status == "approved" for x in instructions), "foreign_instructions": sum(x.source_language not in {"ru", "auto"} for x in instructions),
            "translation_review_queue": sum(x.translation_status == "draft" for x in instructions), "layouts": len(layouts),
        },
        "coverage": {
            "stations_with_instruction_pct": round(100 * len(station_with_any) / station_count, 1) if station_count else 0.0,
            "stations_with_approved_instruction_pct": round(100 * len(station_with_approved) / station_count, 1) if station_count else 0.0,
        },
        "lines": [{"id": x.id, "code": x.code, "name": x.name, "plant": x.plant, "owner": x.owner, "status": x.status} for x in lines],
        "stations": station_rows,
        "operations": [{"id": x.id, "station_id": x.station_id, "code": x.code, "name": x.name, "operation_type": x.operation_type, "part_number": x.part_number, "cycle_time_sec": x.cycle_time_sec, "status": x.status} for x in operations],
        "instructions": [serialize_instruction(x, visible_document_ids) for x in instructions],
        "layouts": [serialize_layout(x, visible_document_ids, placement_by_layout.get(x.id, [])) for x in layouts],
    }


def import_document_text(db: Session, doc: Document) -> tuple[str, dict, list[dict]]:
    text, meta = parse_document(Path(doc.stored_path))
    steps = deterministic_steps(text)
    return text[:50000], meta, steps


async def translate_instruction(
    db: Session,
    row: WorkInstruction,
    *,
    user: str,
    force: bool = False,
    translation_port: TranslationProviderPort | None = None,
    commit: bool = True,
) -> dict:
    if row.source_language == "ru":
        row.translation_status = "not_required"
        if commit:
            db.commit()
        else:
            db.flush()
        return {"status": "not_required", "instruction": row}
    original = row.original_text or "\n".join(str(x.get("text", "")) for x in (row.steps_json or []))
    texts = [original] + [str(x.get("text", "")) for x in (row.steps_json or [])]
    translations = await translate_texts(
        db, texts, project_code=row.project_code, manufacturing_area=row.manufacturing_area,
        scope="work_instruction", target_language="ru", source_language=row.source_language or "auto",
        user=user, force=force, translation_port=translation_port or get_translation_provider_port(),
    )
    main = translations[0]
    if not main.get("translation"):
        return {"status": "unavailable", "warnings": main.get("warnings") or [], "instruction": row}
    row.translated_text_ru = main["translation"]
    translated_steps = []
    for step, tr in zip(row.steps_json or [], translations[1:]):
        translated_steps.append({**step, "text": tr.get("translation") or step.get("text", ""), "translation_status": tr.get("status"), "translation_warnings": tr.get("warnings") or []})
    row.translated_steps_json = translated_steps
    row.translation_status = "draft"
    row.metadata_json = {
        **(row.metadata_json or {}),
        "translation_warnings": sorted({w for tr in translations for w in (tr.get("warnings") or [])}),
        "translation_source_fingerprint": current_translation_fingerprint(row),
        "translation_stale": False,
    }
    if commit:
        db.commit(); db.refresh(row)
    else:
        db.flush()
    return {"status": "draft", "warnings": row.metadata_json.get("translation_warnings", []), "instruction": row}


def _instruction_text(row: WorkInstruction) -> str:
    translated = row.translated_text_ru if row.translation_status in {"draft", "reviewed"} else None
    step_text = "\n".join(str(x.get("text", "")) for x in (row.translated_steps_json or row.steps_json or []))
    return "\n".join(x for x in [row.title, translated or row.original_text or "", step_text, " ".join(row.safety_points_json or []), " ".join(row.quality_points_json or [])] if x)


def _lexical_score(query: str, text: str) -> float:
    terms = {x for x in re.findall(r"[\w\-]{2,}", query.lower(), flags=re.UNICODE)}
    hay = text.lower()
    if not terms:
        return 0.0
    matched = sum(term in hay for term in terms)
    return matched / len(terms)


async def ask_instructions(
    db: Session,
    *, project_code: str, manufacturing_area: str, visible_document_ids: set[str], query: str,
    station_id: str | None = None, operation_id: str | None = None, limit: int = 6,
    ai_port: AIAnalysisPort | None = None,
) -> dict:
    rows = db.scalars(select(WorkInstruction).where(
        WorkInstruction.project_code == project_code,
        WorkInstruction.manufacturing_area == manufacturing_area,
        WorkInstruction.status != "obsolete",
    )).all()
    rows = [x for x in rows if (not x.source_document_id or x.source_document_id in visible_document_ids)]
    if station_id:
        rows = [x for x in rows if x.station_id == station_id]
    if operation_id:
        rows = [x for x in rows if x.operation_id == operation_id]
    scored = sorted((( _lexical_score(query, _instruction_text(x)), x) for x in rows), key=lambda z: z[0], reverse=True)
    hits = [(score, row) for score, row in scored if score > 0][:limit]
    sources = [{"id": row.id, "code": row.code, "revision": row.revision, "title": row.title, "station_id": row.station_id, "status": row.status, "translation_status": row.translation_status, "score": round(score, 4), "excerpt": _instruction_text(row)[:1200]} for score, row in hits]
    if not hits:
        return {"answer": "В выбранном цехе и текущем фильтре подтверждающих рабочих инструкций не найдено.", "sources": [], "generated": False, "manufacturing_area": manufacturing_area}
    ai_port = ai_port or get_ai_analysis_port()
    if not ai_port.available:
        return {"answer": "Core-профиль: AI-синтез отключён. Найдены релевантные рабочие инструкции; откройте источники ниже.", "sources": sources, "generated": False, "manufacturing_area": manufacturing_area}
    evidence = "\n\n".join(f"[WI{i}] {row.code} Rev {row.revision} status={row.status} translation={row.translation_status}\n{_instruction_text(row)[:5000]}" for i, (_, row) in enumerate(hits, 1))
    system = """You are an internal automotive work-instruction evidence assistant. Answer only from supplied work-instruction evidence. Cite every factual statement as [WI1], [WI2], etc. Never invent torque, dimensions, PPE, tools, safety requirements, quality limits, approvals or station responsibilities. If a translation is draft, explicitly say so. You do not control equipment and do not approve an instruction."""
    messages = [{"role":"system","content":system},{"role":"user","content":f"Question: {query}\nWorkshop: {manufacturing_area}\n\nEvidence:\n{evidence}"}]
    try:
        completion = await ai_port.complete(messages, temperature=0.05)
        return {"answer": completion.content, "sources": sources, "generated": True, "manufacturing_area": manufacturing_area}
    except Exception as exc:
        return {"answer": f"AI-синтез недоступен ({type(exc).__name__}). Используйте найденные подтверждающие инструкции.", "sources": sources, "generated": False, "manufacturing_area": manufacturing_area}
