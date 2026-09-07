from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime, timezone
from typing import Iterable

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import (
    ChangeEffectivenessReview, ChangeRequest, EngineeringDecisionRecord, EngineeringDeviation,
    EngineeringRisk, IncomingQualityRecord, LocalizationItem, PPAPSubmission, Problem8D,
    ProcessDefect, ProductionFeedback, RequirementVerification, VehicleVariant,
)
from app.services.change_intelligence import stale_evidence_register
from app.services.engineering_knowledge_memory import collect_project_cases


TERMINAL_CHANGE = {"implemented", "rejected", "cancelled"}
CLOSED_RISK = {"closed", "accepted"}
EFFECTIVE = {"effective", "verified_effective"}
INEFFECTIVE = {"ineffective", "verified_ineffective"}


def _area_ok(area: str | None, requested: str | None, allowed: set[str]) -> bool:
    if area and area not in allowed:
        return False
    return not requested or area in {None, requested}


def _doc_ok(ids: Iterable[str] | None, visible_document_ids: set[str]) -> bool:
    values = set(ids or [])
    return not values or values.issubset(visible_document_ids)


def _part_ok(part_number: str | None, visible_part_numbers: set[str]) -> bool:
    return not part_number or part_number in visible_part_numbers


def _iso(value):
    return value.isoformat() if value else None


def _risk_score(probability: int | None, severity: int | None, detectability: int | None) -> int:
    return int((probability or 1) * (severity or 1) * (detectability or 1))


def _risk_band(score: int) -> str:
    if score >= 60:
        return "critical"
    if score >= 30:
        return "high"
    if score >= 12:
        return "medium"
    return "low"


def _pct(num: float, den: float) -> float:
    return round(100.0 * num / den, 3) if den else 0.0


def serialize_decision(x: EngineeringDecisionRecord) -> dict:
    return {
        "id": x.id, "code": x.code, "title": x.title, "project_code": x.project_code,
        "manufacturing_area": x.manufacturing_area, "part_number": x.part_number, "change_id": x.change_id,
        "problem_statement": x.problem_statement, "alternatives": x.alternatives_json or [],
        "chosen_option": x.chosen_option, "rationale": x.rationale, "expected_result": x.expected_result,
        "accepted_risk": x.accepted_risk, "status": x.status, "owner": x.owner,
        "approved_by": x.approved_by, "approved_at": _iso(x.approved_at),
        "effectiveness_status": x.effectiveness_status, "effectiveness_summary": x.effectiveness_summary,
        "evidence_document_ids": x.evidence_document_ids or [], "metadata": x.metadata_json or {},
        "created_by": x.created_by, "created_at": _iso(x.created_at), "updated_at": _iso(x.updated_at),
        "human_decision_required": True,
    }


def serialize_feedback(x: ProductionFeedback) -> dict:
    defect_rate = _pct(x.defect_quantity, x.built_quantity)
    improvement = None
    if x.before_defect_rate_pct is not None and x.before_defect_rate_pct > 0:
        improvement = round(100.0 * (x.before_defect_rate_pct - defect_rate) / x.before_defect_rate_pct, 2)
    return {
        "id": x.id, "code": x.code, "project_code": x.project_code, "manufacturing_area": x.manufacturing_area,
        "change_id": x.change_id, "decision_id": x.decision_id, "part_number": x.part_number,
        "supplier_code": x.supplier_code, "observation_from": _iso(x.observation_from), "observation_to": _iso(x.observation_to),
        "built_quantity": x.built_quantity, "defect_quantity": x.defect_quantity, "defect_rate_pct": defect_rate,
        "before_defect_rate_pct": x.before_defect_rate_pct, "defect_rate_improvement_pct": improvement,
        "planned_cost_delta": x.planned_cost_delta, "actual_cost_delta": x.actual_cost_delta,
        "planned_mass_delta_kg": x.planned_mass_delta_kg, "actual_mass_delta_kg": x.actual_mass_delta_kg,
        "planned_cycle_time_delta_sec": x.planned_cycle_time_delta_sec, "actual_cycle_time_delta_sec": x.actual_cycle_time_delta_sec,
        "currency": x.currency, "status": x.status, "metrics": x.metrics_json or {},
        "evidence_document_ids": x.evidence_document_ids or [], "notes": x.notes, "metadata": x.metadata_json or {},
        "created_by": x.created_by, "created_at": _iso(x.created_at), "updated_at": _iso(x.updated_at),
        "not_mes_or_scada": True,
    }


def serialize_effectiveness(x: ChangeEffectivenessReview) -> dict:
    return {
        "id": x.id, "code": x.code, "project_code": x.project_code, "manufacturing_area": x.manufacturing_area,
        "change_id": x.change_id, "decision_id": x.decision_id, "feedback_id": x.feedback_id,
        "target_description": x.target_description, "baseline_value": x.baseline_value,
        "target_value": x.target_value, "observed_value": x.observed_value, "unit": x.unit,
        "population": x.population, "status": x.status, "conclusion": x.conclusion,
        "evidence_document_ids": x.evidence_document_ids or [], "reviewed_by": x.reviewed_by,
        "reviewed_at": _iso(x.reviewed_at), "metadata": x.metadata_json or {}, "created_by": x.created_by,
        "created_at": _iso(x.created_at), "updated_at": _iso(x.updated_at), "human_confirmation_required": True,
    }


def serialize_deviation(x: EngineeringDeviation) -> dict:
    now = datetime.now(timezone.utc)
    valid_until = x.valid_until
    if valid_until is not None and valid_until.tzinfo is None:
        valid_until = valid_until.replace(tzinfo=timezone.utc)
    expired = bool(valid_until and valid_until < now and x.status in {"draft", "approved", "active"})
    effective_status = "expired" if expired else x.status
    return {
        "id": x.id, "code": x.code, "project_code": x.project_code, "manufacturing_area": x.manufacturing_area,
        "part_number": x.part_number, "released_revision": x.released_revision, "requested_revision": x.requested_revision,
        "reason": x.reason, "quantity_limit": x.quantity_limit, "valid_from": _iso(x.valid_from), "valid_until": _iso(x.valid_until),
        "status": effective_status, "stored_status": x.status, "expired": expired,
        "affected_variant_ids": x.affected_variant_ids or [], "risks": x.risks_json or [], "approvals": x.approvals_json or [],
        "evidence_document_ids": x.evidence_document_ids or [], "notes": x.notes,
        "approved_by": x.approved_by, "approved_at": _iso(x.approved_at), "metadata": x.metadata_json or {},
        "created_by": x.created_by, "created_at": _iso(x.created_at), "updated_at": _iso(x.updated_at),
        "advisory_only": True,
    }


def serialize_risk(x: EngineeringRisk) -> dict:
    initial = _risk_score(x.probability, x.severity, x.detectability)
    residual = _risk_score(
        x.residual_probability if x.residual_probability is not None else x.probability,
        x.residual_severity if x.residual_severity is not None else x.severity,
        x.residual_detectability if x.residual_detectability is not None else x.detectability,
    )
    return {
        "id": x.id, "code": x.code, "title": x.title, "description": x.description,
        "project_code": x.project_code, "manufacturing_area": x.manufacturing_area, "part_number": x.part_number,
        "change_id": x.change_id, "supplier_code": x.supplier_code,
        "probability": x.probability, "severity": x.severity, "detectability": x.detectability,
        "initial_score": initial, "initial_band": _risk_band(initial),
        "residual_probability": x.residual_probability, "residual_severity": x.residual_severity,
        "residual_detectability": x.residual_detectability, "residual_score": residual, "residual_band": _risk_band(residual),
        "status": x.status, "owner": x.owner, "mitigations": x.mitigations_json or [],
        "evidence_document_ids": x.evidence_document_ids or [], "notes": x.notes, "metadata": x.metadata_json or {},
        "created_by": x.created_by, "created_at": _iso(x.created_at), "updated_at": _iso(x.updated_at),
        "human_risk_acceptance_required": True,
    }


def visible_closed_loop_rows(db: Session, project_code: str, visible_document_ids: set[str], visible_part_numbers: set[str], manufacturing_area: str | None, allowed_area_codes: set[str]) -> dict:
    def filt(rows):
        return [x for x in rows if _area_ok(getattr(x, "manufacturing_area", None), manufacturing_area, allowed_area_codes)
                and _part_ok(getattr(x, "part_number", None), visible_part_numbers)
                and _doc_ok(getattr(x, "evidence_document_ids", []), visible_document_ids)]
    decisions = filt(db.scalars(select(EngineeringDecisionRecord).where(EngineeringDecisionRecord.project_code == project_code)).all())
    feedback = filt(db.scalars(select(ProductionFeedback).where(ProductionFeedback.project_code == project_code)).all())
    effectiveness = filt(db.scalars(select(ChangeEffectivenessReview).where(ChangeEffectivenessReview.project_code == project_code)).all())
    deviations = filt(db.scalars(select(EngineeringDeviation).where(EngineeringDeviation.project_code == project_code)).all())
    risks = filt(db.scalars(select(EngineeringRisk).where(EngineeringRisk.project_code == project_code)).all())
    return {"decisions": decisions, "feedback": feedback, "effectiveness": effectiveness, "deviations": deviations, "risks": risks}


def planned_vs_actual(feedback: list[ProductionFeedback]) -> list[dict]:
    rows = []
    for x in feedback:
        comparisons = []
        for key, planned, actual, unit in [
            ("cost_delta", x.planned_cost_delta, x.actual_cost_delta, x.currency),
            ("mass_delta", x.planned_mass_delta_kg, x.actual_mass_delta_kg, "kg"),
            ("cycle_time_delta", x.planned_cycle_time_delta_sec, x.actual_cycle_time_delta_sec, "s"),
        ]:
            if planned is None or actual is None:
                continue
            abs_error = round(actual - planned, 4)
            pct_error = round(100.0 * abs(abs_error) / abs(planned), 2) if planned else None
            comparisons.append({"metric": key, "planned": planned, "actual": actual, "unit": unit, "delta": abs_error, "error_pct": pct_error})
        if comparisons:
            known = [c["error_pct"] for c in comparisons if c["error_pct"] is not None]
            accuracy = "high" if known and max(known) <= 10 else ("medium" if known and max(known) <= 25 else "low")
            rows.append({"feedback_id": x.id, "code": x.code, "change_id": x.change_id, "part_number": x.part_number, "accuracy": accuracy, "comparisons": comparisons})
    return rows


def risk_based_validation_plan(change: dict) -> dict:
    changed = []
    def diff(a, b, label):
        if a is not None and b is not None and a != b:
            changed.append(label)
    diff(change.get("from_revision"), change.get("to_revision"), "revision")
    diff(change.get("material_from"), change.get("material_to"), "material")
    diff(change.get("thickness_from_mm"), change.get("thickness_to_mm"), "thickness")
    diff(change.get("supplier_from"), change.get("supplier_to"), "supplier")
    diff(change.get("unit_cost_from"), change.get("unit_cost_to"), "cost")
    if change.get("geometry_changed"):
        changed.append("geometry")
    required, review, not_impacted = [], [], []
    def add(bucket, *items):
        for item in items:
            if item not in bucket:
                bucket.append(item)
    if "material" in changed:
        add(required, "material specification confirmation", "forming feasibility", "joining/weldability compatibility", "corrosion compatibility")
        add(review, "durability / fatigue validation")
    if "thickness" in changed:
        add(required, "forming feasibility", "joining parameter review", "mass update")
        add(review, "fixture/tooling clearance", "durability validation")
    if "geometry" in changed:
        add(required, "drawing↔CAD consistency", "dimensional/interface verification", "fit / packaging check")
        add(review, "durability / structural validation", "tooling and fixture impact")
    if "supplier" in changed:
        add(required, "supplier qualification", "PPAP review/resubmission", "Run@Rate / capacity evidence", "incoming-quality plan")
        add(review, "material/process equivalence", "logistics/packaging validation")
    if "revision" in changed:
        add(required, "BOM/revision applicability", "stale V&V review")
    if not changed:
        add(review, "No deterministic change fields supplied; engineer defines V&V scope")
    universal = ["homologation/regulatory impact", "functional safety/cybersecurity impact"]
    add(review, *universal)
    if "geometry" not in changed:
        add(not_impacted, "geometry-specific dimensional verification (unless engineer identifies hidden geometry impact)")
    return {"changed_fields": changed, "required": required, "review": review, "not_impacted_candidates": not_impacted, "advisory_only": True, "human_vv_scope_approval_required": True}


def defect_root_cause_explorer(db: Session, project_code: str, visible_document_ids: set[str], visible_part_numbers: set[str], manufacturing_area: str | None, allowed_area_codes: set[str], defect_id: str) -> dict:
    defect = db.get(ProcessDefect, defect_id)
    if not defect or defect.project_code != project_code or not _area_ok(defect.manufacturing_area, manufacturing_area, allowed_area_codes) or not _part_ok(defect.part_number, visible_part_numbers) or not _doc_ok(defect.evidence_document_ids, visible_document_ids):
        raise LookupError("Defect not found")
    candidates = []
    if defect.part_number:
        changes = [c for c in db.scalars(select(ChangeRequest).where(ChangeRequest.part_number == defect.part_number)).all() if _doc_ok(c.affected_document_ids, visible_document_ids)]
        for c in sorted(changes, key=lambda x: x.updated_at or x.created_at, reverse=True)[:5]:
            candidates.append({"candidate_type": "recent_change", "entity_id": c.id, "label": c.eco_code or c.code, "score": 0.72 if c.status == "implemented" else 0.56, "why": ["same part", f"change status={c.status}", "revision/change path requires investigation"], "path": [f"Defect:{defect.id}", f"Part:{defect.part_number}", f"Change:{c.eco_code or c.code}"]})
    if defect.linked_8d_id:
        p = db.get(Problem8D, defect.linked_8d_id)
        if p and _doc_ok(p.evidence_document_ids, visible_document_ids):
            candidates.append({"candidate_type": "8d", "entity_id": p.id, "label": f"8D · {p.title}", "score": 0.9, "why": ["explicit defect→8D link"], "path": [f"Defect:{defect.id}", f"8D:{p.id}"]})
    if defect.operation_id:
        peers = [d for d in db.scalars(select(ProcessDefect).where(ProcessDefect.operation_id == defect.operation_id)).all() if d.id != defect.id and _doc_ok(d.evidence_document_ids, visible_document_ids)]
        if peers:
            candidates.append({"candidate_type": "process_operation", "entity_id": defect.operation_id, "label": "Same process operation", "score": min(0.85, 0.45 + 0.05 * len(peers)), "why": [f"{len(peers)} other visible defects recorded on same operation"], "path": [f"Defect:{defect.id}", f"Operation:{defect.operation_id}"]})
    if defect.part_number:
        iq = [x for x in db.scalars(select(IncomingQualityRecord).where(IncomingQualityRecord.project_code == project_code, IncomingQualityRecord.part_number == defect.part_number)).all() if _area_ok(x.manufacturing_area, manufacturing_area, allowed_area_codes) and _doc_ok(x.evidence_document_ids, visible_document_ids)]
        bad = [x for x in iq if x.defect_quantity > 0 or x.rejected_quantity > 0]
        if bad:
            by_supplier = Counter(x.supplier_code for x in bad)
            sup, count = by_supplier.most_common(1)[0]
            candidates.append({"candidate_type": "supplier_quality", "entity_id": sup, "label": f"Supplier {sup}", "score": min(0.8, 0.45 + 0.05 * count), "why": [f"{count} incoming-quality records with defects/rejects for same part"], "path": [f"Defect:{defect.id}", f"Part:{defect.part_number}", f"Supplier:{sup}"]})
    candidates.sort(key=lambda x: x["score"], reverse=True)
    return {"defect": {"id": defect.id, "title": defect.title, "part_number": defect.part_number, "severity": defect.severity}, "investigation_candidates": candidates, "causal_claim": False, "message": "Кандидаты для расследования, а не автоматически установленная root cause.", "advisory_only": True}


def supplier_quality_closed_loop(db: Session, project_code: str, visible_document_ids: set[str], visible_part_numbers: set[str], manufacturing_area: str | None, allowed_area_codes: set[str]) -> list[dict]:
    loc = [x for x in db.scalars(select(LocalizationItem).where(LocalizationItem.project_code == project_code)).all() if x.part_number in visible_part_numbers and _area_ok(x.manufacturing_area, manufacturing_area, allowed_area_codes) and _doc_ok(x.evidence_document_ids, visible_document_ids)]
    supplier_parts: dict[str, set[str]] = defaultdict(set)
    supplier_names = {}
    for x in loc:
        supplier_parts[x.supplier_code].add(x.part_number); supplier_names[x.supplier_code] = x.supplier_name
    iq = [x for x in db.scalars(select(IncomingQualityRecord).where(IncomingQualityRecord.project_code == project_code)).all() if x.part_number in visible_part_numbers and _area_ok(x.manufacturing_area, manufacturing_area, allowed_area_codes) and _doc_ok(x.evidence_document_ids, visible_document_ids)]
    ppap = [x for x in db.scalars(select(PPAPSubmission).where(PPAPSubmission.project_code == project_code)).all() if x.part_number in visible_part_numbers and _area_ok(x.manufacturing_area, manufacturing_area, allowed_area_codes) and _doc_ok(x.evidence_document_ids, visible_document_ids)]
    problems = [x for x in db.scalars(select(Problem8D).where(Problem8D.project_code == project_code)).all() if _part_ok(x.part_number, visible_part_numbers) and _area_ok(x.manufacturing_area, manufacturing_area, allowed_area_codes) and _doc_ok(x.evidence_document_ids, visible_document_ids)]
    out=[]
    suppliers=set(supplier_parts)|{x.supplier_code for x in iq}|{x.supplier_code for x in ppap if x.supplier_code}
    for code in sorted(s for s in suppliers if s):
        siq=[x for x in iq if x.supplier_code==code]
        inspected=sum(x.inspected_quantity for x in siq); defects=sum(x.defect_quantity for x in siq); rejects=sum(x.rejected_quantity for x in siq)
        sppap=[x for x in ppap if x.supplier_code==code]
        partset=supplier_parts.get(code,set())|{x.part_number for x in siq}|{x.part_number for x in sppap}
        related_8d=[p for p in problems if p.part_number in partset and ((p.metadata_json or {}).get("supplier_code")==code or p.part_number in {x.part_number for x in siq if x.linked_8d_id==p.id})]
        defect_codes=Counter(x.defect_code for x in siq if x.defect_code)
        out.append({"supplier_code":code,"supplier_name":supplier_names.get(code) or next((x.supplier_name for x in siq if x.supplier_name),None),"parts":sorted(partset),"incoming_inspected":inspected,"incoming_defects":defects,"incoming_rejected":rejects,"incoming_defect_rate_pct":_pct(defects,inspected),"ppap":{"approved":sum(x.status=="approved" for x in sppap),"review_required":sum(x.status in {"draft","submitted","review_required"} for x in sppap),"total":len(sppap)},"open_8d":sum(p.status not in {"closed","cancelled"} for p in related_8d),"repeated_failure_modes":defect_codes.most_common(5),"advisory_only":True})
    return sorted(out,key=lambda x:(-x["open_8d"],-x["incoming_defect_rate_pct"],x["supplier_code"]))


def release_confidence(db: Session, project_code: str, visible_document_ids: set[str], visible_part_numbers: set[str], manufacturing_area: str | None, allowed_area_codes: set[str], risks: list[EngineeringRisk], effectiveness: list[ChangeEffectivenessReview], deviations: list[EngineeringDeviation]) -> dict:
    stale = stale_evidence_register(db, project_code, visible_document_ids, visible_part_numbers, manufacturing_area, allowed_area_codes)
    stale_critical=sum(1 for x in stale if x.get("state") in {"STALE","MISSING"} and x.get("severity") in {"critical","warning"})
    reqs=[x for x in db.scalars(select(RequirementVerification).where(RequirementVerification.project_code==project_code)).all() if _area_ok(x.manufacturing_area,manufacturing_area,allowed_area_codes) and _doc_ok(x.evidence_document_ids,visible_document_ids)]
    vv_total=len(reqs); vv_good=sum(x.status in {"passed","waived"} and bool(x.evidence_document_ids) for x in reqs)
    ppaps=[x for x in db.scalars(select(PPAPSubmission).where(PPAPSubmission.project_code==project_code)).all() if x.part_number in visible_part_numbers and _area_ok(x.manufacturing_area,manufacturing_area,allowed_area_codes) and _doc_ok(x.evidence_document_ids,visible_document_ids)]
    ppap_total=len(ppaps); ppap_good=sum(x.status=="approved" and bool(x.evidence_document_ids) for x in ppaps)
    open_high=sum(serialize_risk(x)["residual_band"] in {"high","critical"} and x.status not in CLOSED_RISK for x in risks)
    ineffective=sum(x.status in INEFFECTIVE for x in effectiveness)
    expired=sum(serialize_deviation(x)["expired"] for x in deviations)
    domains={
        "product": max(0,100-min(60,10*stale_critical)),
        "vv": round(100*vv_good/vv_total,1) if vv_total else 70.0,
        "supplier": round(100*ppap_good/ppap_total,1) if ppap_total else 70.0,
        "quality": max(0,100-20*ineffective),
        "risk": max(0,100-15*open_high),
        "configuration": max(0,100-20*expired),
    }
    overall=round(sum(domains.values())/len(domains),1)
    band="GREEN" if overall>=90 and not open_high and not ineffective else ("AMBER" if overall>=70 else "RED")
    reasons=[]
    if stale_critical: reasons.append(f"{stale_critical} stale/missing engineering evidence signals")
    if open_high: reasons.append(f"{open_high} open high/critical residual engineering risks")
    if ineffective: reasons.append(f"{ineffective} ineffective change reviews")
    if expired: reasons.append(f"{expired} expired deviations")
    return {"overall":overall,"band":band,"domains":domains,"why_not_green":reasons[:10],"not_release_authority":True,"human_release_approval_required":True}


def early_warning_signals(rows: dict, supplier_quality: list[dict], planned_actual: list[dict]) -> list[dict]:
    out=[]
    for x in rows["feedback"]:
        sx=serialize_feedback(x)
        if sx["before_defect_rate_pct"] is not None and sx["defect_rate_pct"] > sx["before_defect_rate_pct"] * 1.5 and sx["built_quantity"] >= 20:
            out.append({"severity":"high","type":"defect_increase","title":f"{x.code}: defect rate increased after change","detail":f"{sx['before_defect_rate_pct']:.3f}% → {sx['defect_rate_pct']:.3f}%","entity_id":x.id})
    for x in rows["effectiveness"]:
        if x.status in INEFFECTIVE:
            out.append({"severity":"high","type":"ineffective_change","title":f"{x.code}: effectiveness target not achieved","detail":x.conclusion or x.target_description,"entity_id":x.id})
    for x in rows["risks"]:
        sx=serialize_risk(x)
        if sx["residual_band"] in {"high","critical"} and x.status not in CLOSED_RISK:
            out.append({"severity":"high" if sx["residual_band"]=="critical" else "medium","type":"residual_risk","title":f"{x.code}: {x.title}","detail":f"Residual risk {sx['residual_band'].upper()} ({sx['residual_score']})","entity_id":x.id})
    for x in rows["deviations"]:
        sx=serialize_deviation(x)
        if sx["expired"]:
            out.append({"severity":"high","type":"expired_deviation","title":f"{x.code}: deviation expired","detail":f"Part {x.part_number}; allowed quantity {x.quantity_limit or 'not specified'}","entity_id":x.id})
    for s in supplier_quality:
        if s["open_8d"]>=2:
            out.append({"severity":"medium","type":"supplier_repeat_8d","title":f"Supplier {s['supplier_code']}: repeated open 8D","detail":f"{s['open_8d']} open 8D; incoming defect rate {s['incoming_defect_rate_pct']}%","entity_id":s["supplier_code"]})
    for p in planned_actual:
        if p["accuracy"]=="low":
            out.append({"severity":"medium","type":"prediction_miss","title":f"{p['code']}: planned vs actual differs materially","detail":"At least one observed engineering impact differs from plan by >25%.","entity_id":p["feedback_id"]})
    order={"critical":0,"high":1,"medium":2,"low":3}
    return sorted(out,key=lambda x:(order.get(x["severity"],9),x["title"]))[:30]


def closed_loop_workspace(db: Session, project_code: str, visible_document_ids: set[str], visible_part_numbers: set[str], manufacturing_area: str | None, allowed_area_codes: set[str]) -> dict:
    rows=visible_closed_loop_rows(db,project_code,visible_document_ids,visible_part_numbers,manufacturing_area,allowed_area_codes)
    supplier=supplier_quality_closed_loop(db,project_code,visible_document_ids,visible_part_numbers,manufacturing_area,allowed_area_codes)
    pva=planned_vs_actual(rows["feedback"])
    confidence=release_confidence(db,project_code,visible_document_ids,visible_part_numbers,manufacturing_area,allowed_area_codes,rows["risks"],rows["effectiveness"],rows["deviations"])
    warnings=early_warning_signals(rows,supplier,pva)
    decisions=[serialize_decision(x) for x in sorted(rows["decisions"],key=lambda x:x.updated_at or x.created_at,reverse=True)]
    feedback=[serialize_feedback(x) for x in sorted(rows["feedback"],key=lambda x:x.updated_at or x.created_at,reverse=True)]
    effectiveness=[serialize_effectiveness(x) for x in sorted(rows["effectiveness"],key=lambda x:x.updated_at or x.created_at,reverse=True)]
    deviations=[serialize_deviation(x) for x in sorted(rows["deviations"],key=lambda x:x.updated_at or x.created_at,reverse=True)]
    risks=[serialize_risk(x) for x in sorted(rows["risks"],key=lambda x:_risk_score(x.residual_probability or x.probability,x.residual_severity or x.severity,x.residual_detectability or x.detectability),reverse=True)]
    active_changes=[c for c in db.scalars(select(ChangeRequest)).all() if c.status not in TERMINAL_CHANGE and _part_ok(c.part_number,visible_part_numbers) and _doc_ok(c.affected_document_ids,visible_document_ids)]
    defect_rows=[d for d in db.scalars(select(ProcessDefect).where(ProcessDefect.project_code==project_code)).all() if d.status not in {"resolved","closed","cancelled"} and _part_ok(d.part_number,visible_part_numbers) and _area_ok(d.manufacturing_area,manufacturing_area,allowed_area_codes) and _doc_ok(d.evidence_document_ids,visible_document_ids)]
    open_defects=[{"id":d.id,"title":d.title,"part_number":d.part_number,"severity":d.severity,"defect_code":d.defect_code,"manufacturing_area":d.manufacturing_area,"occurred_at":_iso(d.occurred_at)} for d in sorted(defect_rows,key=lambda x:x.occurred_at,reverse=True)[:50]]
    pulse={"active_changes":len(active_changes),"critical_open_risks":sum(x["residual_band"]=="critical" and x["status"] not in CLOSED_RISK for x in risks),"ineffective_changes":sum(x["status"] in INEFFECTIVE for x in effectiveness),"open_supplier_8d":sum(x["open_8d"] for x in supplier),"expired_deviations":sum(x["expired"] for x in deviations),"open_defects":len(open_defects),"release_confidence":confidence["band"],"top_signal":warnings[0] if warnings else None}
    return {"decisions":decisions,"production_feedback":feedback,"effectiveness_reviews":effectiveness,"deviations":deviations,"risks":risks,"open_defects":open_defects,"supplier_quality":supplier,"planned_vs_actual":pva,"early_warnings":warnings,"release_confidence":confidence,"engineering_pulse":pulse,"governance":{"advisory_only":True,"not_mes_or_scada":True,"not_qms_or_plm_authority":True,"human_release_approval_required":True}}
