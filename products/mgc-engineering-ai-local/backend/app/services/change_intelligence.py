from __future__ import annotations

from collections import defaultdict
from typing import Iterable

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import (
    ArchitectureNode,
    ChangeRequest,
    ConfigurationApplicability,
    CostBaseline,
    CostLine,
    Document,
    EngineeringRequirement,
    LocalizationItem,
    ManufacturingLine,
    Part,
    PPAPSubmission,
    ProcessOperation,
    ProcessStation,
    ReleaseBaseline,
    RequirementVerification,
    ValidationIssue,
    VehicleVariant,
)
from app.services.engineering_digital_thread import engineering_digital_thread
from app.services.release_baseline import compare_bom_rows, compare_release_baselines
from app.services.requirements_matrix import requirements_matrix


TERMINAL_CHANGE = {"implemented", "rejected", "cancelled"}
CRITICAL = {"critical", "safety", "regulatory"}
AREA_LABELS = {
    "product_engineering": "R&D",
    "stamping": "Штамповка",
    "body_welding": "Сварка",
    "paint": "Окраска",
    "assembly": "Сборка",
    "components": "Компоненты",
    "logistics": "Логистика",
    "quality": "Качество",
    "manufacturing_engineering": "Технология",
    "testing": "Испытания",
}


def _status(value) -> str | None:
    if value is None:
        return None
    return value.value if hasattr(value, "value") else str(value)


def _area_ok(area: str | None, requested: str | None, allowed: set[str]) -> bool:
    if area and area not in allowed:
        return False
    if requested:
        return area in {None, requested}
    return True


def _doc_ok(ids: Iterable[str] | None, visible_document_ids: set[str]) -> bool:
    values = set(ids or [])
    return not values or values.issubset(visible_document_ids)


def _pct(n: int, d: int) -> float:
    return round(100.0 * n / d, 1) if d else 0.0


def _latest_parts(db: Session, project_code: str, visible_parts: set[str]) -> dict[str, Part]:
    if not visible_parts:
        return {}
    return {
        p.part_number: p
        for p in db.scalars(select(Part).where(Part.project_code == project_code, Part.part_number.in_(visible_parts))).all()
    }


def stale_evidence_register(
    db: Session,
    project_code: str,
    visible_document_ids: set[str],
    visible_part_numbers: set[str],
    manufacturing_area: str | None = None,
    allowed_area_codes: set[str] | None = None,
) -> list[dict]:
    """Deterministic evidence freshness register.

    Historical evidence is never deleted or silently invalidated. The engine marks records
    CURRENT / REVIEW_REQUIRED / STALE / MISSING / UNKNOWN and explains the deterministic reason.
    """
    allowed = set(allowed_area_codes or [])
    parts = _latest_parts(db, project_code, visible_part_numbers)
    docs = [
        d for d in db.scalars(select(Document).where(Document.project_code == project_code)).all()
        if d.id in visible_document_ids and _area_ok(d.manufacturing_area, manufacturing_area, allowed)
    ]
    docs_by_part: dict[str, list[Document]] = defaultdict(list)
    for d in docs:
        if d.part_number in visible_part_numbers:
            docs_by_part[d.part_number].append(d)

    rows: list[dict] = []
    for pn in sorted(visible_part_numbers):
        part = parts.get(pn)
        current_rev = part.latest_revision if part else None
        pdocs = docs_by_part.get(pn, [])
        for doc_type, label in (("drawing", "Чертёж"), ("cad", "3D/CAD")):
            candidates = [d for d in pdocs if d.doc_type in ({"cad", "cad_native"} if doc_type == "cad" else {doc_type})]
            if not candidates:
                rows.append({
                    "state": "MISSING", "severity": "warning", "entity_type": "document", "part_number": pn,
                    "title": f"{pn}: отсутствует {label}", "reason": "Нет доступного evidence этого типа.",
                    "manufacturing_area": manufacturing_area,
                })
                continue
            if current_rev:
                current = [d for d in candidates if d.revision == current_rev]
                if not current:
                    latest = sorted(candidates, key=lambda x: x.updated_at, reverse=True)[0]
                    rows.append({
                        "state": "REVIEW_REQUIRED", "severity": "warning", "entity_type": "document", "entity_id": latest.id,
                        "part_number": pn, "title": f"{label} не подтверждает текущую Rev {current_rev}",
                        "reason": f"Последний доступный {label.lower()} имеет Rev {latest.revision or 'UNKNOWN'}.",
                        "manufacturing_area": latest.manufacturing_area,
                    })
                else:
                    d = sorted(current, key=lambda x: x.updated_at, reverse=True)[0]
                    rows.append({
                        "state": "CURRENT", "severity": "info", "entity_type": "document", "entity_id": d.id,
                        "part_number": pn, "title": f"{label} соответствует Rev {current_rev}",
                        "reason": "Ревизия evidence совпадает с текущей ревизией детали.",
                        "manufacturing_area": d.manufacturing_area,
                    })
            else:
                rows.append({
                    "state": "UNKNOWN", "severity": "warning", "entity_type": "part", "part_number": pn,
                    "title": f"{pn}: текущая ревизия не определена", "reason": "Нельзя детерминированно оценить freshness документа без current revision.",
                    "manufacturing_area": manufacturing_area,
                })

    matrix = requirements_matrix(db, project_code, visible_document_ids, visible_part_numbers, manufacturing_area, allowed)
    for req in matrix.get("requirements", []):
        linked_parts = [p for p in req.get("part_numbers", []) if p in visible_part_numbers]
        for v in req.get("verifications", []):
            state = "CURRENT" if v.get("effective_pass") else ("STALE" if v.get("stale") else "REVIEW_REQUIRED")
            severity = "critical" if req.get("criticality") in CRITICAL and state != "CURRENT" else ("warning" if state != "CURRENT" else "info")
            rows.append({
                "state": state, "severity": severity, "entity_type": "verification", "entity_id": v.get("id"),
                "part_number": linked_parts[0] if len(linked_parts) == 1 else None,
                "part_numbers": linked_parts,
                "title": f"{v.get('code')} · {v.get('title')}",
                "reason": "Verification snapshot устарел относительно требования/источника." if state == "STALE" else (
                    "PASSED подтверждён доступным актуальным evidence." if state == "CURRENT" else "Verification требует подтверждения/завершения."
                ),
                "manufacturing_area": v.get("manufacturing_area"),
            })

    ppaps = db.scalars(select(PPAPSubmission).where(PPAPSubmission.project_code == project_code)).all()
    for p in ppaps:
        if p.part_number not in visible_part_numbers or not _area_ok(p.manufacturing_area, manufacturing_area, allowed):
            continue
        if not _doc_ok(p.evidence_document_ids, visible_document_ids):
            continue
        current_rev = parts.get(p.part_number).latest_revision if parts.get(p.part_number) else None
        state = "CURRENT" if p.status == "approved" and (not current_rev or not p.revision or p.revision == current_rev) and bool(p.evidence_document_ids) else "REVIEW_REQUIRED"
        reason = "Approved PPAP с доступным evidence для текущей ревизии." if state == "CURRENT" else "PPAP не approved, без evidence или относится к другой ревизии."
        rows.append({
            "state": state, "severity": "warning" if state != "CURRENT" else "info", "entity_type": "ppap", "entity_id": p.id,
            "part_number": p.part_number, "title": f"PPAP · {p.supplier_code or p.supplier_name or p.part_number}", "reason": reason,
            "manufacturing_area": p.manufacturing_area,
        })

    active_changes = db.scalars(select(ChangeRequest).order_by(ChangeRequest.updated_at.desc())).all()
    for c in active_changes:
        if not c.part_number or c.part_number not in visible_part_numbers or c.status in TERMINAL_CHANGE:
            continue
        if not _doc_ok(c.affected_document_ids, visible_document_ids):
            continue
        rows.append({
            "state": "REVIEW_REQUIRED", "severity": "critical" if c.risk_level == "critical" else "warning",
            "entity_type": "change", "entity_id": c.id, "part_number": c.part_number,
            "title": f"{c.eco_code or c.code} · downstream evidence review",
            "reason": f"Открытое изменение {c.from_revision or '—'} → {c.to_revision or '—'} ещё не замкнуто.",
            "manufacturing_area": manufacturing_area,
        })

    baselines = db.scalars(select(ReleaseBaseline).where(ReleaseBaseline.project_code == project_code)).all()
    for b in baselines:
        if not _area_ok(b.manufacturing_area, manufacturing_area, allowed) or not set(b.source_document_ids or []).issubset(visible_document_ids):
            continue
        snap = b.snapshot_json or {}
        old_revs = {x.get("part_number"): x.get("revision") for x in snap.get("part_revisions", [])}
        drift = [pn for pn, p in parts.items() if p.latest_revision and old_revs.get(pn) and old_revs.get(pn) != p.latest_revision]
        if drift:
            rows.append({
                "state": "REVIEW_REQUIRED", "severity": "warning", "entity_type": "release", "entity_id": b.id,
                "part_numbers": drift, "title": f"{b.code}: baseline drift обнаружен",
                "reason": "Immutable baseline остаётся корректным историческим snapshot, но текущие ревизии ушли вперёд; для нового gate нужен новый baseline.",
                "manufacturing_area": b.manufacturing_area,
            })

    order = {"STALE": 0, "MISSING": 1, "REVIEW_REQUIRED": 2, "UNKNOWN": 3, "CURRENT": 4}
    return sorted(rows, key=lambda x: (order.get(x["state"], 9), 0 if x.get("severity") == "critical" else 1, x.get("title", "")))


def traceability_coverage(
    db: Session,
    project_code: str,
    visible_document_ids: set[str],
    visible_part_numbers: set[str],
    manufacturing_area: str | None,
    allowed_area_codes: set[str],
) -> dict:
    parts = sorted(visible_part_numbers)
    n = len(parts)
    docs = [
        d for d in db.scalars(select(Document).where(Document.project_code == project_code)).all()
        if d.id in visible_document_ids and _area_ok(d.manufacturing_area, manufacturing_area, allowed_area_codes)
    ]
    drawing_parts = {d.part_number for d in docs if d.part_number in visible_part_numbers and d.doc_type == "drawing"}
    cad_parts = {d.part_number for d in docs if d.part_number in visible_part_numbers and d.doc_type in {"cad", "cad_native"}}

    lines = [x for x in db.scalars(select(ManufacturingLine).where(ManufacturingLine.project_code == project_code)).all() if _area_ok(x.manufacturing_area, manufacturing_area, allowed_area_codes)]
    line_ids = {x.id for x in lines}
    stations = db.scalars(select(ProcessStation).where(ProcessStation.line_id.in_(line_ids))).all() if line_ids else []
    station_ids = {x.id for x in stations}
    process_parts = {x.part_number for x in db.scalars(select(ProcessOperation).where(ProcessOperation.station_id.in_(station_ids))).all() if x.part_number in visible_part_numbers} if station_ids else set()

    req_parts = set()
    for r in db.scalars(select(EngineeringRequirement).where(EngineeringRequirement.project_code == project_code)).all():
        if not _area_ok(r.manufacturing_area, manufacturing_area, allowed_area_codes):
            continue
        if r.source_document_id and r.source_document_id not in visible_document_ids:
            continue
        req_parts.update(p for p in (r.part_numbers or []) if p in visible_part_numbers)

    supplier_parts = {
        s.part_number for s in db.scalars(select(LocalizationItem).where(LocalizationItem.project_code == project_code)).all()
        if s.part_number in visible_part_numbers and _area_ok(s.manufacturing_area, manufacturing_area, allowed_area_codes) and _doc_ok(s.evidence_document_ids, visible_document_ids)
    }
    ppap_parts = {
        p.part_number for p in db.scalars(select(PPAPSubmission).where(PPAPSubmission.project_code == project_code)).all()
        if p.part_number in visible_part_numbers and p.status == "approved" and _area_ok(p.manufacturing_area, manufacturing_area, allowed_area_codes) and _doc_ok(p.evidence_document_ids, visible_document_ids)
    }
    release_parts = set()
    for b in db.scalars(select(ReleaseBaseline).where(ReleaseBaseline.project_code == project_code)).all():
        if not _area_ok(b.manufacturing_area, manufacturing_area, allowed_area_codes) or not set(b.source_document_ids or []).issubset(visible_document_ids):
            continue
        release_parts.update(x.get("part_number") for x in (b.snapshot_json or {}).get("part_revisions", []) if x.get("part_number") in visible_part_numbers)

    metrics = [
        ("drawing", "Детали с чертежом", drawing_parts),
        ("cad", "Детали с 3D/CAD", cad_parts),
        ("requirements", "Детали с требованиями", req_parts),
        ("process", "Детали, связанные с процессом", process_parts),
        ("supplier", "Детали с supplier record", supplier_parts),
        ("ppap", "Детали с approved PPAP", ppap_parts),
        ("release", "Детали в release baseline", release_parts),
    ]
    rows = [{"key": k, "label": label, "covered": len(values), "total": n, "coverage_pct": _pct(len(values), n), "missing_parts": sorted(set(parts) - set(values))[:50]} for k, label, values in metrics]
    score = round(sum(x["coverage_pct"] for x in rows) / len(rows), 1) if rows else 0.0
    weakest = min(rows, key=lambda x: x["coverage_pct"]) if rows else None
    return {"score": score, "parts": n, "metrics": rows, "weakest": weakest, "advisory_only": True}


def variant_impact_matrix(
    db: Session,
    project_code: str,
    visible_document_ids: set[str],
    visible_part_numbers: set[str],
    manufacturing_area: str | None,
    allowed_area_codes: set[str],
) -> dict:
    variants = [
        v for v in db.scalars(select(VehicleVariant).where(VehicleVariant.project_code == project_code)).all()
        if _area_ok(v.manufacturing_area, manufacturing_area, allowed_area_codes) and _doc_ok(v.evidence_document_ids, visible_document_ids)
    ]
    variant_ids = {v.id for v in variants}
    appl = [
        a for a in db.scalars(select(ConfigurationApplicability).where(ConfigurationApplicability.project_code == project_code, ConfigurationApplicability.entity_type == "part")).all()
        if a.variant_id in variant_ids and a.entity_key.upper() in visible_part_numbers and _area_ok(a.manufacturing_area, manufacturing_area, allowed_area_codes) and _doc_ok(a.evidence_document_ids, visible_document_ids)
    ]
    lookup = {(a.entity_key.upper(), a.variant_id): a.applicability for a in appl}
    rows = []
    for pn in sorted(visible_part_numbers):
        cells = []
        for v in variants:
            cells.append({"variant_id": v.id, "variant_code": v.code, "applicability": lookup.get((pn, v.id), "unknown")})
        rows.append({"part_number": pn, "variants": cells})
    return {
        "variants": [{"id": v.id, "code": v.code, "name": v.name, "market": v.market, "model_year": v.model_year} for v in variants],
        "rows": rows[:150], "unknown_is_not_included": True,
    }


def _operations_by_part(db: Session, project_code: str, manufacturing_area: str | None, allowed: set[str]) -> dict[str, list[dict]]:
    lines = [x for x in db.scalars(select(ManufacturingLine).where(ManufacturingLine.project_code == project_code)).all() if _area_ok(x.manufacturing_area, manufacturing_area, allowed)]
    line_by_id = {x.id: x for x in lines}
    stations = db.scalars(select(ProcessStation).where(ProcessStation.line_id.in_(set(line_by_id)))).all() if line_by_id else []
    st_by_id = {x.id: x for x in stations}
    ops = db.scalars(select(ProcessOperation).where(ProcessOperation.station_id.in_(set(st_by_id)))).all() if st_by_id else []
    out: dict[str, list[dict]] = defaultdict(list)
    for op in ops:
        if not op.part_number:
            continue
        st = st_by_id[op.station_id]
        ln = line_by_id[st.line_id]
        out[op.part_number].append({"id": op.id, "code": op.code, "name": op.name, "line": ln.code, "station": st.code, "area": ln.manufacturing_area, "work_instruction_document_ids": op.work_instruction_document_ids or []})
    return out


def workshop_change_heatmap(
    db: Session,
    project_code: str,
    visible_document_ids: set[str],
    visible_part_numbers: set[str],
    manufacturing_area: str | None,
    allowed_area_codes: set[str],
) -> list[dict]:
    ops = _operations_by_part(db, project_code, manufacturing_area, allowed_area_codes)
    changes = [
        c for c in db.scalars(select(ChangeRequest)).all()
        if c.part_number in visible_part_numbers and c.status not in TERMINAL_CHANGE and _doc_ok(c.affected_document_ids, visible_document_ids)
    ]
    buckets: dict[str, dict] = {}
    for c in changes:
        for op in ops.get(c.part_number, []):
            area = op["area"] or "general"
            b = buckets.setdefault(area, {"manufacturing_area": area, "label": AREA_LABELS.get(area, area), "changes": set(), "parts": set(), "operations": [], "critical": 0})
            b["changes"].add(c.id); b["parts"].add(c.part_number); b["operations"].append(op)
            if c.risk_level in {"critical", "high"}:
                b["critical"] += 1
    result = []
    for b in buckets.values():
        score = len(b["operations"]) + 2 * b["critical"]
        severity = "critical" if b["critical"] and score >= 4 else ("high" if score >= 3 else "medium")
        result.append({
            "manufacturing_area": b["manufacturing_area"], "label": b["label"], "severity": severity,
            "change_count": len(b["changes"]), "part_count": len(b["parts"]), "operation_count": len(b["operations"]),
            "operations": b["operations"][:30],
        })
    return sorted(result, key=lambda x: ({"critical": 0, "high": 1, "medium": 2, "low": 3}.get(x["severity"], 9), x["label"]))


def engineering_action_queue(
    db: Session,
    project_code: str,
    visible_document_ids: set[str],
    visible_part_numbers: set[str],
    manufacturing_area: str | None,
    allowed_area_codes: set[str],
    thread: dict | None = None,
    stale: list[dict] | None = None,
) -> list[dict]:
    thread = thread or engineering_digital_thread(db, project_code, visible_document_ids, visible_part_numbers, manufacturing_area, allowed_area_codes, None, 3, 500)
    stale = stale if stale is not None else stale_evidence_register(db, project_code, visible_document_ids, visible_part_numbers, manufacturing_area, allowed_area_codes)
    items: list[dict] = []
    for x in stale:
        if x["state"] == "CURRENT":
            continue
        priority = "critical" if x.get("severity") == "critical" or x["state"] == "STALE" else ("high" if x["state"] in {"MISSING", "REVIEW_REQUIRED"} else "medium")
        items.append({"priority": priority, "type": "freshness", "title": x["title"], "reason": x["reason"], "part_number": x.get("part_number"), "manufacturing_area": x.get("manufacturing_area"), "entity_type": x.get("entity_type"), "entity_id": x.get("entity_id")})
    for g in thread.get("gaps", []):
        items.append({"priority": "critical" if g.get("severity") == "critical" else "high", "type": "trace_gap", "title": g.get("title"), "reason": "Digital Thread trace gap", "part_number": g.get("part_number"), "manufacturing_area": manufacturing_area, "entity_type": g.get("type"), "entity_id": g.get("id")})
    for c in db.scalars(select(ChangeRequest).order_by(ChangeRequest.updated_at.desc())).all():
        if not c.part_number or c.part_number not in visible_part_numbers or c.status in TERMINAL_CHANGE or not _doc_ok(c.affected_document_ids, visible_document_ids):
            continue
        if c.risk_level in {"critical", "high"}:
            items.append({"priority": "critical" if c.risk_level == "critical" else "high", "type": "change", "title": f"{c.eco_code or c.code} · {c.title}", "reason": f"Открытое {c.risk_level} изменение в статусе {c.status}", "part_number": c.part_number, "manufacturing_area": manufacturing_area, "entity_type": "change", "entity_id": c.id})
    dedup = {}
    for x in items:
        key = (x.get("entity_type"), x.get("entity_id"), x.get("title"))
        dedup.setdefault(key, x)
    rank = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    return sorted(dedup.values(), key=lambda x: (rank.get(x["priority"], 9), x["title"]))[:120]


def change_intelligence_workspace(
    db: Session,
    project_code: str,
    visible_document_ids: set[str],
    visible_part_numbers: set[str],
    manufacturing_area: str | None = None,
    allowed_area_codes: set[str] | None = None,
) -> dict:
    allowed = set(allowed_area_codes or [])
    stale = stale_evidence_register(db, project_code, visible_document_ids, visible_part_numbers, manufacturing_area, allowed)
    thread = engineering_digital_thread(db, project_code, visible_document_ids, visible_part_numbers, manufacturing_area, allowed, None, 3, 500)
    queue = engineering_action_queue(db, project_code, visible_document_ids, visible_part_numbers, manufacturing_area, allowed, thread=thread, stale=stale)
    coverage = traceability_coverage(db, project_code, visible_document_ids, visible_part_numbers, manufacturing_area, allowed)
    variants = variant_impact_matrix(db, project_code, visible_document_ids, visible_part_numbers, manufacturing_area, allowed)
    heatmap = workshop_change_heatmap(db, project_code, visible_document_ids, visible_part_numbers, manufacturing_area, allowed)
    counts = defaultdict(int)
    for x in stale:
        counts[x["state"]] += 1
    return {
        "project_code": project_code, "manufacturing_area": manufacturing_area,
        "counts": {"actions": len(queue), "stale": counts["STALE"], "review_required": counts["REVIEW_REQUIRED"], "missing": counts["MISSING"], "unknown": counts["UNKNOWN"]},
        "action_queue": queue, "stale_evidence": stale, "coverage": coverage, "variant_matrix": variants, "workshop_impact": heatmap,
        "advisory_only": True, "no_automatic_release_or_approval": True,
    }


def _changed_flags(scenario: dict) -> dict[str, bool]:
    def diff(a: str, b: str) -> bool:
        x, y = scenario.get(a), scenario.get(b)
        return x is not None and y is not None and x != y
    return {
        "revision": diff("from_revision", "to_revision"),
        "material": diff("material_from", "material_to"),
        "thickness": diff("thickness_from_mm", "thickness_to_mm"),
        "supplier": diff("supplier_from", "supplier_to"),
        "unit_cost": diff("unit_cost_from", "unit_cost_to"),
        "quantity": diff("quantity_from", "quantity_to"),
        "geometry": bool(scenario.get("geometry_changed")),
    }


def simulate_change_impact(
    db: Session,
    project_code: str,
    visible_document_ids: set[str],
    visible_part_numbers: set[str],
    scenario: dict,
    manufacturing_area: str | None = None,
    allowed_area_codes: set[str] | None = None,
) -> dict:
    allowed = set(allowed_area_codes or [])
    pn = str(scenario.get("part_number") or "").strip().upper()
    if not pn or pn not in visible_part_numbers:
        raise LookupError("Part not found")
    flags = _changed_flags(scenario)
    if not any(flags.values()):
        raise ValueError("Scenario does not contain a material engineering change")
    thread = engineering_digital_thread(db, project_code, visible_document_ids, visible_part_numbers, manufacturing_area, allowed, pn, 4, 500)
    nodes = thread.get("nodes", [])
    by_type: dict[str, list[dict]] = defaultdict(list)
    for n in nodes:
        by_type[n["type"]].append(n)

    categories = []
    def category(key: str, label: str, types: set[str], active: bool, base_severity: str, note: str):
        affected = [n for t in types for n in by_type.get(t, [])]
        if active and affected:
            categories.append({"key": key, "label": label, "severity": base_severity, "count": len(affected), "note": note, "entities": affected[:25]})
        elif active:
            categories.append({"key": key, "label": label, "severity": "review", "count": 0, "note": note + " Связанные объекты не настроены.", "entities": []})

    design_change = flags["revision"] or flags["material"] or flags["thickness"] or flags["geometry"]
    product_change = design_change or flags["quantity"] or flags["supplier"]
    category("product", "Product / BOM", {"part", "variant"}, product_change, "high", "Проверить применимость по вариантам и product structure.")
    category("design", "Design", {"document", "architecture", "interface"}, design_change, "high", "Проверить CAD, drawing и интерфейсы после изменения конструкции.")
    category("validation", "Validation / V&V", {"requirement", "verification", "issue"}, design_change, "high", "Проверить requirements и повторную применимость verification evidence.")
    category("manufacturing", "Manufacturing", {"operation"}, design_change or flags["supplier"], "high", "Проверить операции, tooling/fixture и рабочие инструкции.")
    category("supplier", "Supplier / PPAP", {"supplier"}, flags["supplier"] or design_change, "high" if flags["supplier"] else "medium", "Проверить PPAP, capacity/Run@Rate и supplier evidence.")
    category("cost", "Cost", {"cost"}, flags["material"] or flags["thickness"] or flags["supplier"] or flags["unit_cost"], "medium", "Пересчитать engineering economics; ERP остаётся финансовым source of record.")
    category("release", "Release", {"release", "change"}, True, "high", "После закрытия изменения потребуется новый immutable baseline; старый baseline не редактируется.")

    simulated_stale: list[dict] = []
    if design_change:
        for n in by_type.get("document", []):
            if n.get("meta", {}).get("doc_type") in {"drawing", "cad", "cad_native"}:
                simulated_stale.append({"entity_id": n["id"], "entity_type": "document", "state": "REVIEW_REQUIRED", "title": n["label"], "reason": "Design-affecting scenario may invalidate revision-specific CAD/drawing evidence."})
        for n in by_type.get("verification", []):
            simulated_stale.append({"entity_id": n["id"], "entity_type": "verification", "state": "STALE", "title": n["label"], "reason": "Verification must be re-evaluated after a design-affecting change."})
    if flags["supplier"]:
        for n in by_type.get("supplier", []):
            simulated_stale.append({"entity_id": n["id"], "entity_type": "supplier", "state": "STALE", "title": n["label"], "reason": "Supplier change requires new supplier qualification/PPAP evidence."})
    if design_change or flags["supplier"]:
        for n in by_type.get("operation", []):
            simulated_stale.append({"entity_id": n["id"], "entity_type": "operation", "state": "REVIEW_REQUIRED", "title": n["label"], "reason": "Process/WI applicability must be confirmed against the proposed part state."})
    for n in by_type.get("release", []):
        simulated_stale.append({"entity_id": n["id"], "entity_type": "release", "state": "REVIEW_REQUIRED", "title": n["label"], "reason": "Historical baseline remains immutable; a new baseline is required after approved implementation."})

    actions = []
    if design_change:
        actions += [
            {"priority": "critical" if flags["geometry"] else "high", "action": "Обновить CAD/drawing и повторить Drawing↔3D validation."},
            {"priority": "high", "action": "Пересмотреть связанные requirements и V&V; stale PASSED нельзя считать effective."},
            {"priority": "high", "action": "Проверить manufacturing operations, fixture/tooling и Work Instruction."},
        ]
    if flags["supplier"]:
        actions += [
            {"priority": "critical", "action": "Создать/обновить supplier qualification и PPAP для нового поставщика."},
            {"priority": "high", "action": "Подтвердить capacity / Run@Rate и incoming quality readiness."},
        ]
    if flags["material"] or flags["thickness"] or flags["unit_cost"] or flags["supplier"]:
        actions.append({"priority": "medium", "action": "Пересчитать engineering cost scenario и annual impact; финансовое утверждение остаётся в ERP/Finance."})
    actions.append({"priority": "high", "action": "После ECR/ECO implementation + verification зафиксировать новый Release/Design Freeze baseline."})

    ops = _operations_by_part(db, project_code, manufacturing_area, allowed).get(pn, [])
    heat = defaultdict(lambda: {"operations": [], "severity": "medium"})
    for op in ops:
        area = op["area"] or "general"
        heat[area]["operations"].append(op)
        if design_change or flags["supplier"]:
            heat[area]["severity"] = "high"
    workshop = [{"manufacturing_area": a, "label": AREA_LABELS.get(a, a), "severity": v["severity"], "operation_count": len(v["operations"]), "operations": v["operations"]} for a, v in heat.items()]

    variants = []
    for n in by_type.get("variant", []):
        variants.append({"id": n["key"], "label": n["label"], "applicability": next((e.get("label") for e in thread.get("edges", []) if e.get("target") == n["id"] and e.get("relation") == "APPLICABLE_TO"), "unknown")})

    cost = {"comparable": False, "currency": scenario.get("currency") or "RUB", "unit_delta": None, "annual_delta": None}
    if scenario.get("unit_cost_from") is not None and scenario.get("unit_cost_to") is not None:
        delta = float(scenario["unit_cost_to"]) - float(scenario["unit_cost_from"])
        qty = float(scenario.get("quantity_per_vehicle") or 1.0)
        cost["unit_delta"] = round(delta * qty, 4)
        if scenario.get("annual_volume") is not None:
            cost["annual_delta"] = round(cost["unit_delta"] * float(scenario["annual_volume"]), 2)
        cost["comparable"] = True

    return {
        "project_code": project_code, "part_number": pn, "scenario": scenario, "changed_fields": [k for k, v in flags.items() if v],
        "summary": {"affected_entities": sum(x["count"] for x in categories), "categories": len(categories), "actions": len(actions), "stale_or_review": len(simulated_stale)},
        "categories": categories, "stale_evidence": simulated_stale, "actions": actions, "workshop_impact": workshop,
        "affected_variants": variants, "cost_impact": cost, "explainable_routes": thread.get("routes", []),
        "advisory_only": True, "simulation_only": True, "does_not_modify_engineering_records": True,
    }


def _keyed_diff(left: list[dict], right: list[dict], key_fields: tuple[str, ...]) -> dict:
    def key(x): return tuple(x.get(k) for k in key_fields)
    a = {key(x): x for x in left}; b = {key(x): x for x in right}
    added = [b[k] for k in sorted(set(b) - set(a), key=str)]
    removed = [a[k] for k in sorted(set(a) - set(b), key=str)]
    changed = []
    for k in sorted(set(a) & set(b), key=str):
        if a[k] != b[k]:
            changed.append({"key": k, "from": a[k], "to": b[k]})
    return {"added": added, "removed": removed, "changed": changed, "summary": {"added": len(added), "removed": len(removed), "changed": len(changed)}}


def _baseline_advisory_score(snapshot: dict) -> float:
    req = snapshot.get("requirements", [])
    ver = snapshot.get("verifications", [])
    passed_req = {v.get("requirement_id") for v in ver if v.get("status") == "passed" and (v.get("evidence_document_ids") or [])}
    verification_score = _pct(len({r.get("id") for r in req} & passed_req), len(req)) if req else 100.0
    unknown = len((snapshot.get("configuration") or {}).get("unknown_parts", [])) + len((snapshot.get("configuration") or {}).get("unknown_document_ids", []))
    config_total = max(len(snapshot.get("part_revisions", [])) + len(snapshot.get("documents", [])), 1)
    config_score = max(0.0, 100.0 - 100.0 * unknown / config_total)
    critical = len(snapshot.get("critical_issues", []))
    issue_score = max(0.0, 100.0 - critical * 25.0)
    process_score = 100.0 if snapshot.get("process_operations") else (50.0 if snapshot.get("schema") == "mgc-release-baseline-v1" else 0.0)
    return round(verification_score * 0.45 + config_score * 0.20 + issue_score * 0.25 + process_score * 0.10, 1)


def compare_digital_thread_baselines(left: ReleaseBaseline, right: ReleaseBaseline) -> dict:
    base = compare_release_baselines(left, right)
    a = left.snapshot_json or {}; b = right.snapshot_json or {}
    base["verifications"] = _keyed_diff(a.get("verifications", []), b.get("verifications", []), ("code",))
    base["suppliers"] = _keyed_diff(a.get("suppliers", []), b.get("suppliers", []), ("part_number", "supplier_code"))
    base["ppap"] = _keyed_diff(a.get("ppap", []), b.get("ppap", []), ("part_number", "supplier_code"))
    base["changes"] = _keyed_diff(a.get("changes", []), b.get("changes", []), ("code",))
    base["critical_issues"] = _keyed_diff(a.get("critical_issues", []), b.get("critical_issues", []), ("part_number", "rule_code"))
    base["process"] = _keyed_diff(a.get("process_operations", []), b.get("process_operations", []), ("part_number", "line", "station", "code"))
    base["cost"] = _keyed_diff(a.get("cost_lines", []), b.get("cost_lines", []), ("part_number", "baseline_code", "supplier_code"))
    base["architecture"] = _keyed_diff(a.get("architecture_nodes", []), b.get("architecture_nodes", []), ("code",))
    base["interfaces"] = _keyed_diff(a.get("interfaces", []), b.get("interfaces", []), ("code",))
    base["configuration"] = {
        "included_parts": {"from": (a.get("configuration") or {}).get("included_parts", []), "to": (b.get("configuration") or {}).get("included_parts", [])},
        "excluded_parts": {"from": (a.get("configuration") or {}).get("excluded_parts", []), "to": (b.get("configuration") or {}).get("excluded_parts", [])},
        "unknown_parts": {"from": (a.get("configuration") or {}).get("unknown_parts", []), "to": (b.get("configuration") or {}).get("unknown_parts", [])},
    }
    lscore, rscore = _baseline_advisory_score(a), _baseline_advisory_score(b)
    base["readiness"] = {"left_score": lscore, "right_score": rscore, "delta": round(rscore - lscore, 1), "advisory_only": True, "does_not_grant_release": True}
    base["schema"] = {"left": a.get("schema", "unknown"), "right": b.get("schema", "unknown")}
    base["full_digital_thread_diff"] = True
    return base


def deterministic_thread_facts(thread: dict, workspace: dict, focus_part: str | None = None) -> list[str]:
    facts = []
    s = thread.get("summary", {})
    facts.append(f"Digital Thread: {s.get('nodes', 0)} узлов, {s.get('edges', 0)} связей, coverage {s.get('coverage_pct', 0)}%.")
    if focus_part:
        facts.append(f"Фокус: {focus_part}; explainable impact routes: {len(thread.get('routes', []))}.")
    counts = workspace.get("counts", {})
    facts.append(f"Action Queue: {counts.get('actions', 0)}; STALE {counts.get('stale', 0)}; REVIEW_REQUIRED {counts.get('review_required', 0)}; MISSING {counts.get('missing', 0)}.")
    for x in workspace.get("action_queue", [])[:5]:
        facts.append(f"{x.get('priority', '').upper()}: {x.get('title')} — {x.get('reason')}")
    return facts
