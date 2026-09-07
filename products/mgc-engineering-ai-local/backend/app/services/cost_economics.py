from __future__ import annotations

from datetime import datetime, timezone
from statistics import mean

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import CostBaseline, CostLine, EvidencePack, SupplierQuotation


ACTIVE_BASELINE = {"active", "frozen"}
ACTIVE_QUOTE = {"received", "selected"}


def _dt(value):
    return value.isoformat() if value else None


def _visible_evidence(ids: list[str] | None, visible_document_ids: set[str] | None) -> list[str]:
    values = list(ids or [])
    if visible_document_ids is None:
        return values
    return [x for x in values if x in visible_document_ids]


def _in_area(value: str | None, manufacturing_area: str | None, allowed_area_codes: set[str] | None) -> bool:
    if manufacturing_area:
        return not value or value == manufacturing_area
    return not value or allowed_area_codes is None or value in allowed_area_codes


def _money(value: float | None) -> float | None:
    return round(float(value), 4) if value is not None else None


def _safe(value: float | int | None) -> float:
    return max(float(value or 0.0), 0.0)


def line_calculation(line: CostLine) -> dict:
    """Deterministic engineering-cost calculation.

    Breakdown mode deliberately avoids hidden assumptions. Tooling enters unit cost only when an
    explicit amortization volume is supplied. Quote mode treats the supplier unit price as the
    purchased-part base and then adds only explicitly supplied logistics/packaging/other costs.
    """
    mass = _safe(line.mass_kg)
    material_price = _safe(line.material_price_per_kg)
    scrap = min(max(float(line.scrap_rate_pct or 0.0), 0.0), 1000.0)
    material_net = mass * material_price if mass and material_price else 0.0
    material_with_scrap = material_net * (1.0 + scrap / 100.0)
    tooling_unit = 0.0
    if line.tooling_cost is not None and line.tooling_amortization_volume and line.tooling_amortization_volume > 0:
        tooling_unit = _safe(line.tooling_cost) / float(line.tooling_amortization_volume)

    if line.calculation_mode == "quote":
        base = _safe(line.supplier_unit_price)
        unit = base + _safe(line.logistics_cost) + _safe(line.packaging_cost) + _safe(line.other_unit_cost) + tooling_unit
        source = "supplier_quote"
    else:
        unit = (
            material_with_scrap
            + _safe(line.conversion_cost)
            + _safe(line.logistics_cost)
            + _safe(line.packaging_cost)
            + _safe(line.overhead_cost)
            + _safe(line.other_unit_cost)
            + tooling_unit
        )
        source = "engineering_breakdown"

    qty = max(float(line.quantity_per_vehicle or 1.0), 0.0)
    vehicle_cost = unit * qty
    target = float(line.target_unit_cost) if line.target_unit_cost is not None else None
    variance = unit - target if target is not None else None
    variance_pct = (variance / target * 100.0) if target not in (None, 0) else None
    return {
        "source": source,
        "material_net": _money(material_net),
        "material_with_scrap": _money(material_with_scrap),
        "tooling_amortized_unit": _money(tooling_unit),
        "unit_cost": _money(unit),
        "quantity_per_vehicle": qty,
        "vehicle_cost": _money(vehicle_cost),
        "target_unit_cost": _money(target),
        "variance_to_target": _money(variance),
        "variance_to_target_pct": round(variance_pct, 2) if variance_pct is not None else None,
    }


def serialize_baseline(x: CostBaseline, visible_document_ids: set[str] | None = None) -> dict:
    return {
        "id": x.id,
        "project_code": x.project_code,
        "manufacturing_area": x.manufacturing_area,
        "code": x.code,
        "name": x.name,
        "baseline_type": x.baseline_type,
        "status": x.status,
        "currency": x.currency,
        "annual_volume": x.annual_volume,
        "target_vehicle_cost": x.target_vehicle_cost,
        "reference_baseline_id": x.reference_baseline_id,
        "linked_change_id": x.linked_change_id,
        "effective_at": _dt(x.effective_at),
        "evidence_document_ids": _visible_evidence(x.evidence_document_ids, visible_document_ids),
        "notes": x.notes,
        "created_by": x.created_by,
        "metadata": x.metadata_json or {},
        "created_at": _dt(x.created_at),
        "updated_at": _dt(x.updated_at),
    }


def serialize_line(x: CostLine, visible_document_ids: set[str] | None = None) -> dict:
    data = {
        "id": x.id,
        "project_code": x.project_code,
        "baseline_id": x.baseline_id,
        "manufacturing_area": x.manufacturing_area,
        "part_number": x.part_number,
        "revision": x.revision,
        "supplier_code": x.supplier_code,
        "supplier_name": x.supplier_name,
        "quantity_per_vehicle": x.quantity_per_vehicle,
        "calculation_mode": x.calculation_mode,
        "mass_kg": x.mass_kg,
        "material_name": x.material_name,
        "material_price_per_kg": x.material_price_per_kg,
        "scrap_rate_pct": x.scrap_rate_pct,
        "conversion_cost": x.conversion_cost,
        "logistics_cost": x.logistics_cost,
        "packaging_cost": x.packaging_cost,
        "overhead_cost": x.overhead_cost,
        "supplier_unit_price": x.supplier_unit_price,
        "other_unit_cost": x.other_unit_cost,
        "tooling_cost": x.tooling_cost,
        "tooling_amortization_volume": x.tooling_amortization_volume,
        "target_unit_cost": x.target_unit_cost,
        "evidence_document_ids": _visible_evidence(x.evidence_document_ids, visible_document_ids),
        "notes": x.notes,
        "metadata": x.metadata_json or {},
        "created_at": _dt(x.created_at),
        "updated_at": _dt(x.updated_at),
    }
    data["calculation"] = line_calculation(x)
    return data


def serialize_quote(x: SupplierQuotation, visible_document_ids: set[str] | None = None) -> dict:
    now = datetime.now(timezone.utc)
    valid_until = x.valid_until
    if valid_until and valid_until.tzinfo is None:
        valid_until = valid_until.replace(tzinfo=timezone.utc)
    expired = bool(valid_until and valid_until < now)
    return {
        "id": x.id,
        "project_code": x.project_code,
        "manufacturing_area": x.manufacturing_area,
        "code": x.code,
        "part_number": x.part_number,
        "revision": x.revision,
        "supplier_code": x.supplier_code,
        "supplier_name": x.supplier_name,
        "currency": x.currency,
        "unit_price": x.unit_price,
        "tooling_cost": x.tooling_cost,
        "annual_volume": x.annual_volume,
        "status": x.status,
        "valid_until": _dt(x.valid_until),
        "expired": expired,
        "evidence_document_ids": _visible_evidence(x.evidence_document_ids, visible_document_ids),
        "notes": x.notes,
        "created_by": x.created_by,
        "metadata": x.metadata_json or {},
        "created_at": _dt(x.created_at),
        "updated_at": _dt(x.updated_at),
    }


def _baseline_summary(base: CostBaseline, lines: list[CostLine], visible_document_ids: set[str] | None) -> dict:
    views = [serialize_line(x, visible_document_ids) for x in lines]
    vehicle_cost = sum(float(x["calculation"]["vehicle_cost"] or 0.0) for x in views)
    tooling = sum(_safe(x.tooling_cost) for x in lines)
    mass = sum(_safe(x.mass_kg) * max(float(x.quantity_per_vehicle or 1.0), 0.0) for x in lines)
    targets = [float(x["target_unit_cost"]) * float(x["quantity_per_vehicle"] or 1.0) for x in views if x.get("target_unit_cost") is not None]
    explicit_target = float(base.target_vehicle_cost) if base.target_vehicle_cost is not None else (sum(targets) if targets else None)
    variance = vehicle_cost - explicit_target if explicit_target is not None else None
    annual_delta = variance * base.annual_volume if variance is not None and base.annual_volume else None
    return {
        **serialize_baseline(base, visible_document_ids),
        "line_count": len(lines),
        "vehicle_cost": _money(vehicle_cost),
        "tooling_total": _money(tooling),
        "mass_kg_per_vehicle": round(mass, 4),
        "effective_target_vehicle_cost": _money(explicit_target),
        "variance_to_target": _money(variance),
        "variance_to_target_pct": round(variance / explicit_target * 100.0, 2) if explicit_target not in (None, 0) else None,
        "annual_variance": _money(annual_delta),
        "lines": views,
    }


def _select_primary(baselines: list[CostBaseline], baseline_type: str) -> CostBaseline | None:
    candidates = [x for x in baselines if x.baseline_type == baseline_type]
    if not candidates:
        return None
    candidates.sort(key=lambda x: (x.status in ACTIVE_BASELINE, x.effective_at or x.updated_at or x.created_at), reverse=True)
    return candidates[0]


def cost_economics_workspace(
    db: Session,
    project_code: str,
    visible_document_ids: set[str],
    visible_part_numbers: set[str],
    manufacturing_area: str | None = None,
    allowed_area_codes: set[str] | None = None,
) -> dict:
    baselines = db.scalars(select(CostBaseline).where(CostBaseline.project_code == project_code).order_by(CostBaseline.updated_at.desc())).all()
    baselines = [x for x in baselines if _in_area(x.manufacturing_area, manufacturing_area, allowed_area_codes)]
    baseline_ids = {x.id for x in baselines}
    lines = db.scalars(select(CostLine).where(CostLine.project_code == project_code).order_by(CostLine.updated_at.desc())).all()
    lines = [x for x in lines if x.baseline_id in baseline_ids and x.part_number in visible_part_numbers and _in_area(x.manufacturing_area, manufacturing_area, allowed_area_codes)]
    quotes = db.scalars(select(SupplierQuotation).where(SupplierQuotation.project_code == project_code).order_by(SupplierQuotation.updated_at.desc())).all()
    quotes = [x for x in quotes if x.part_number in visible_part_numbers and _in_area(x.manufacturing_area, manufacturing_area, allowed_area_codes)]

    by_baseline: dict[str, list[CostLine]] = {}
    for line in lines:
        by_baseline.setdefault(line.baseline_id, []).append(line)
    summaries = [_baseline_summary(x, by_baseline.get(x.id, []), visible_document_ids) for x in baselines]
    summary_by_id = {x["id"]: x for x in summaries}

    current = _select_primary(baselines, "current")
    target = _select_primary(baselines, "target")
    current_view = summary_by_id.get(current.id) if current else None
    target_view = summary_by_id.get(target.id) if target else None

    target_vehicle = None
    if target_view:
        target_vehicle = target_view.get("vehicle_cost")
        if target_view.get("target_vehicle_cost") is not None:
            target_vehicle = target_view.get("target_vehicle_cost")
    if current_view and current_view.get("effective_target_vehicle_cost") is not None:
        target_vehicle = current_view.get("effective_target_vehicle_cost")

    current_vehicle = current_view.get("vehicle_cost") if current_view else None
    variance = (float(current_vehicle) - float(target_vehicle)) if current_vehicle is not None and target_vehicle is not None else None
    volume = (current.annual_volume if current else None) or (target.annual_volume if target else None)
    annual_variance = variance * volume if variance is not None and volume else None

    change_impacts = []
    for base in baselines:
        if base.baseline_type != "change" or not base.linked_change_id:
            continue
        view = summary_by_id.get(base.id)
        ref = summary_by_id.get(base.reference_baseline_id) if base.reference_baseline_id else current_view
        if not view:
            continue
        delta = float(view.get("vehicle_cost") or 0.0) - float(ref.get("vehicle_cost") or 0.0) if ref else None
        vol = base.annual_volume or (current.annual_volume if current else None)
        change_impacts.append({
            "baseline_id": base.id,
            "baseline_code": base.code,
            "linked_change_id": base.linked_change_id,
            "reference_baseline_id": ref.get("id") if ref else None,
            "currency": base.currency,
            "unit_delta_per_vehicle": _money(delta),
            "annual_delta": _money(delta * vol) if delta is not None and vol else None,
            "annual_volume": vol,
        })

    gaps: list[dict] = []
    def gap(kind: str, severity: str, title: str, ident: str | None = None, part: str | None = None):
        gaps.append({"type": kind, "severity": severity, "title": title, "id": ident, "part_number": part})

    if current_view and not current_view.get("line_count"):
        gap("current_baseline_empty", "warning", f"{current.code}: нет строк расчёта", current.id)
    if current_vehicle is not None and target_vehicle not in (None, 0):
        pct = variance / float(target_vehicle) * 100.0 if variance is not None else 0.0
        if pct > 10:
            gap("over_target", "critical", f"Engineering cost выше target на {pct:.1f}%", current.id if current else None)
        elif pct > 3:
            gap("over_target", "warning", f"Engineering cost выше target на {pct:.1f}%", current.id if current else None)
    for line in lines:
        calc = line_calculation(line)
        if calc["unit_cost"] == 0 and line.target_unit_cost not in (None, 0):
            gap("line_cost_missing", "warning", f"{line.part_number}: не заполнен engineering cost", line.id, line.part_number)
        if line.tooling_cost and not line.tooling_amortization_volume:
            gap("tooling_not_amortized", "warning", f"{line.part_number}: tooling показан отдельно — не задан объём амортизации", line.id, line.part_number)
    quote_views = [serialize_quote(x, visible_document_ids) for x in quotes]
    for q in quote_views:
        if q["status"] == "selected" and q["expired"]:
            gap("selected_quote_expired", "warning", f"{q['part_number']}: выбранная quotation {q['code']} просрочена", q["id"], q["part_number"])
        if q["status"] == "selected" and not q["evidence_document_ids"]:
            gap("quote_evidence_missing", "warning", f"{q['part_number']}: выбранная quotation без доступного evidence", q["id"], q["part_number"])
    for x in change_impacts:
        if x["reference_baseline_id"] is None:
            gap("change_reference_missing", "warning", f"{x['baseline_code']}: не определена исходная cost baseline", x["baseline_id"])

    configured = bool(baselines or lines or quotes)
    # Cost health is advisory, not a release gate. Score reflects completeness/target pressure only.
    completeness = 100.0
    if configured:
        if not current_view:
            completeness -= 30
        if current_view and not current_view.get("line_count"):
            completeness -= 30
        if current_view and target_vehicle is None:
            completeness -= 10
        completeness -= 8 * sum(g["severity"] == "warning" for g in gaps)
        completeness -= 20 * sum(g["severity"] == "critical" for g in gaps)
        completeness = max(0.0, min(100.0, completeness))
    else:
        completeness = 0.0

    localization_scenarios = [summary_by_id[x.id] for x in baselines if x.baseline_type == "localization" and x.id in summary_by_id]
    return {
        "configured": configured,
        "score": round(completeness, 1),
        "status": "over_target" if any(g["type"] == "over_target" and g["severity"] == "critical" for g in gaps) else ("needs_review" if gaps else ("controlled" if configured else "not_configured")),
        "currency": (current.currency if current else (target.currency if target else (baselines[0].currency if baselines else "RUB"))),
        "current_vehicle_cost": _money(current_vehicle),
        "target_vehicle_cost": _money(target_vehicle),
        "variance_to_target": _money(variance),
        "variance_to_target_pct": round(variance / float(target_vehicle) * 100.0, 2) if variance is not None and target_vehicle not in (None, 0) else None,
        "annual_volume": volume,
        "annual_variance": _money(annual_variance),
        "baselines": summaries,
        "quotes": quote_views,
        "change_impacts": change_impacts,
        "localization_scenarios": localization_scenarios,
        "gaps": gaps,
        "counts": {"baselines": len(baselines), "lines": len(lines), "quotes": len(quotes), "change_scenarios": len(change_impacts)},
        "governance": {
            "advisory_only": True,
            "finance_approval_required": True,
            "erp_is_financial_system_of_record": True,
            "no_automatic_sourcing_or_investment_approval": True,
        },
    }


def create_cost_evidence_pack(db: Session, project_code: str, baseline: CostBaseline, user: str, visible_document_ids: set[str], workspace: dict) -> EvidencePack:
    view = next((x for x in workspace.get("baselines", []) if x.get("id") == baseline.id), serialize_baseline(baseline, visible_document_ids))
    manifest = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "project_code": project_code,
        "pack_type": "engineering_cost",
        "baseline": view,
        "project_economics_snapshot": {
            "current_vehicle_cost": workspace.get("current_vehicle_cost"),
            "target_vehicle_cost": workspace.get("target_vehicle_cost"),
            "variance_to_target": workspace.get("variance_to_target"),
            "annual_variance": workspace.get("annual_variance"),
            "change_impacts": workspace.get("change_impacts", []),
            "gaps": workspace.get("gaps", []),
        },
        "governance": workspace.get("governance", {}),
        "integrity": {"snapshot_only": True, "visible_evidence_document_ids": _visible_evidence(baseline.evidence_document_ids, visible_document_ids)},
    }
    pack = EvidencePack(pack_type="engineering_cost", project_code=project_code, manifest=manifest, created_by=user)
    db.add(pack); db.commit(); db.refresh(pack)
    return pack
