from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import (
    BuildDefectLink, BuildGenealogyItem, ChangeRequest, ConfigurationApplicability,
    ProcessDefect, Problem8D, ProductionFeedback, SafeLaunchControl, VehicleBuild,
    VehicleVariant,
)

CLOSED_DEFECT = {"resolved", "closed", "cancelled"}
TERMINAL_CHANGE = {"closed", "cancelled", "rejected"}


def _iso(v):
    return v.isoformat() if v else None


def _visible_evidence(ids: list[str] | None, visible_document_ids: set[str]) -> bool:
    return not ids or set(ids).issubset(visible_document_ids)


def _area_ok(area: str | None, requested: str | None, allowed: set[str] | None) -> bool:
    if area and allowed is not None and area not in allowed:
        return False
    return not requested or area in {None, requested}


def serialize_build(x: VehicleBuild) -> dict:
    return {
        "id": x.id, "code": x.code, "vehicle_identifier": x.vehicle_identifier,
        "variant_id": x.variant_id, "plant": x.plant, "line_id": x.line_id,
        "manufacturing_area": x.manufacturing_area, "build_type": x.build_type,
        "build_sequence": x.build_sequence, "planned_at": _iso(x.planned_at),
        "completed_at": _iso(x.completed_at), "status": x.status,
        "release_baseline_id": x.release_baseline_id,
        "evidence_document_ids": x.evidence_document_ids or [], "notes": x.notes,
        "metadata": x.metadata_json or {},
    }


def serialize_genealogy(x: BuildGenealogyItem) -> dict:
    return {
        "id": x.id, "build_id": x.build_id, "manufacturing_area": x.manufacturing_area,
        "part_number": x.part_number, "revision": x.revision, "supplier_code": x.supplier_code,
        "lot_number": x.lot_number, "serial_number": x.serial_number,
        "quantity": float(x.quantity or 0), "installed_at": _iso(x.installed_at),
        "source_system": x.source_system, "evidence_document_ids": x.evidence_document_ids or [],
        "metadata": x.metadata_json or {},
    }


def serialize_safe_launch(x: SafeLaunchControl) -> dict:
    inspected = int(x.inspected_quantity or 0)
    defects = int(x.defect_quantity or 0)
    clean = int(x.consecutive_clean_builds or 0)
    req_clean = int(x.required_clean_builds or 0)
    req_qty = int(x.required_inspected_quantity or 0)
    gaps = []
    if inspected < req_qty:
        gaps.append("inspection_population_below_exit_requirement")
    if defects > 0:
        gaps.append("safe_launch_defects_detected")
    if clean < req_clean:
        gaps.append("clean_build_streak_below_requirement")
    exit_candidate = not gaps and x.status not in {"exited", "cancelled"}
    return {
        "id": x.id, "code": x.code, "manufacturing_area": x.manufacturing_area,
        "part_number": x.part_number, "supplier_code": x.supplier_code,
        "characteristic": x.characteristic, "status": x.status,
        "inspected_quantity": inspected, "defect_quantity": defects,
        "defect_rate_pct": round(defects * 100 / inspected, 4) if inspected else None,
        "consecutive_clean_builds": clean, "required_clean_builds": req_clean,
        "required_inspected_quantity": req_qty, "exit_candidate": exit_candidate,
        "exit_gaps": gaps, "exit_criteria": x.exit_criteria_json or {},
        "evidence_document_ids": x.evidence_document_ids or [], "notes": x.notes,
        "human_exit_approval_required": True,
    }


def visible_build_rows(db: Session, project_code: str, visible_document_ids: set[str], visible_part_numbers: set[str], manufacturing_area: str | None = None, allowed_area_codes: set[str] | None = None) -> dict:
    visible_parts = {x.upper() for x in visible_part_numbers}
    builds = [x for x in db.scalars(select(VehicleBuild).where(VehicleBuild.project_code == project_code)).all()
              if _area_ok(x.manufacturing_area, manufacturing_area, allowed_area_codes)
              and _visible_evidence(x.evidence_document_ids, visible_document_ids)]
    build_ids = {x.id for x in builds}
    genealogy = [x for x in db.scalars(select(BuildGenealogyItem)).all()
                 if x.build_id in build_ids and x.part_number.upper() in visible_parts
                 and _area_ok(x.manufacturing_area, manufacturing_area, allowed_area_codes)
                 and _visible_evidence(x.evidence_document_ids, visible_document_ids)]
    defect_by_id = {x.id: x for x in db.scalars(select(ProcessDefect).where(ProcessDefect.project_code == project_code)).all()
                    if _area_ok(x.manufacturing_area, manufacturing_area, allowed_area_codes)
                    and (not x.part_number or x.part_number.upper() in visible_parts)
                    and _visible_evidence(x.evidence_document_ids, visible_document_ids)}
    links = [x for x in db.scalars(select(BuildDefectLink)).all()
             if x.build_id in build_ids and x.defect_id in defect_by_id
             and _visible_evidence(x.evidence_document_ids, visible_document_ids)]
    safe_launch = [x for x in db.scalars(select(SafeLaunchControl).where(SafeLaunchControl.project_code == project_code)).all()
                   if _area_ok(x.manufacturing_area, manufacturing_area, allowed_area_codes)
                   and (not x.part_number or x.part_number.upper() in visible_parts)
                   and _visible_evidence(x.evidence_document_ids, visible_document_ids)]
    return {"builds": builds, "genealogy": genealogy, "defect_links": links, "defects": defect_by_id, "safe_launch": safe_launch}


def _expected_parts(db: Session, project_code: str, variant_id: str | None, visible_parts: set[str], visible_document_ids: set[str], manufacturing_area: str | None, allowed: set[str] | None) -> set[str]:
    if not variant_id:
        return set()
    out = set()
    rows = db.scalars(select(ConfigurationApplicability).where(
        ConfigurationApplicability.project_code == project_code,
        ConfigurationApplicability.variant_id == variant_id,
        ConfigurationApplicability.entity_type == "part",
    )).all()
    for x in rows:
        if x.applicability != "included" or x.entity_key.upper() not in visible_parts:
            continue
        if not _area_ok(x.manufacturing_area, manufacturing_area, allowed) or not _visible_evidence(x.evidence_document_ids, visible_document_ids):
            continue
        out.add(x.entity_key.upper())
    return out


def _defect_payload(d: ProcessDefect, link: BuildDefectLink) -> dict:
    return {
        "link_id": link.id, "defect_id": d.id, "defect_code": d.defect_code,
        "title": d.title, "severity": d.severity, "status": d.status,
        "part_number": d.part_number, "manufacturing_area": d.manufacturing_area,
        "quantity": int(d.quantity or 0), "linked_8d_id": d.linked_8d_id,
        "detection_stage": link.detection_stage, "containment_status": link.containment_status,
        "occurred_at": _iso(d.occurred_at),
    }


def _recurrence(builds: list[VehicleBuild], genealogy: list[BuildGenealogyItem], links: list[BuildDefectLink], defects: dict[str, ProcessDefect]) -> list[dict]:
    supplier_by_build_part = {}
    for g in genealogy:
        supplier_by_build_part[(g.build_id, g.part_number.upper())] = g.supplier_code
    build_by_id = {b.id: b for b in builds}
    clusters = defaultdict(lambda: {"build_ids": set(), "vehicles": set(), "quantity": 0, "severities": Counter()})
    for l in links:
        d = defects[l.defect_id]
        b = build_by_id[l.build_id]
        pn = (d.part_number or "UNKNOWN").upper()
        supplier = supplier_by_build_part.get((b.id, pn))
        key = (d.defect_code or d.title, pn, supplier, b.variant_id)
        c = clusters[key]
        c["build_ids"].add(b.id); c["vehicles"].add(b.vehicle_identifier); c["quantity"] += int(d.quantity or 1); c["severities"][d.severity] += 1
    out=[]
    for (code,pn,supplier,variant_id), c in clusters.items():
        count=len(c["build_ids"])
        if count < 2:
            continue
        out.append({"defect_key": code, "part_number": pn, "supplier_code": supplier, "variant_id": variant_id,
                    "affected_builds": count, "affected_vehicles": len(c["vehicles"]), "defect_quantity": c["quantity"],
                    "severity_counts": dict(c["severities"]), "recurrence": True})
    return sorted(out, key=lambda x: (x["affected_builds"], x["defect_quantity"]), reverse=True)


def _feedback_loop(db: Session, project_code: str, links: list[BuildDefectLink], defects: dict[str, ProcessDefect], builds: list[VehicleBuild], visible_document_ids: set[str]) -> list[dict]:
    eightds = {x.id: x for x in db.scalars(select(Problem8D).where(Problem8D.project_code == project_code)).all()
               if _visible_evidence(x.evidence_document_ids, visible_document_ids)}
    changes = {x.id: x for x in db.scalars(select(ChangeRequest)).all()
               if _visible_evidence(x.affected_document_ids, visible_document_ids)}
    build_by_id={x.id:x for x in builds}
    rows=[]
    for l in links:
        d=defects[l.defect_id]
        eight=eightds.get(d.linked_8d_id) if d.linked_8d_id else None
        ch=changes.get(eight.linked_change_id) if eight and eight.linked_change_id else None
        if not ch:
            continue
        b=build_by_id[l.build_id]
        later=[x for x in builds if x.completed_at and b.completed_at and x.completed_at>b.completed_at]
        repeated=0
        for ll in links:
            if ll.build_id not in {x.id for x in later}: continue
            dd=defects[ll.defect_id]
            if (dd.defect_code or dd.title)==(d.defect_code or d.title) and (dd.part_number or "")== (d.part_number or ""):
                repeated+=1
        rows.append({"source_build":b.code,"vehicle_identifier":b.vehicle_identifier,"defect_id":d.id,"defect":d.title,
                     "eight_d_id":eight.id,"change_id":ch.id,"change_code":ch.eco_code or ch.code,"change_status":ch.status,
                     "later_builds_observed":len(later),"same_issue_on_later_builds":repeated,
                     "loop_status":"RECURRED" if repeated else ("OBSERVING" if not later else "NO_RECURRENCE_OBSERVED"),
                     "causal_claim":False})
    return rows


def vehicle_build_launch_workspace(db: Session, project_code: str, visible_document_ids: set[str], visible_part_numbers: set[str], manufacturing_area: str | None = None, allowed_area_codes: set[str] | None = None, vehicle_identifier: str | None = None) -> dict:
    rows=visible_build_rows(db,project_code,visible_document_ids,visible_part_numbers,manufacturing_area,allowed_area_codes)
    builds=sorted(rows["builds"], key=lambda x: (x.completed_at or x.planned_at or x.created_at), reverse=True)
    selected=next((x for x in builds if vehicle_identifier and x.vehicle_identifier==vehicle_identifier), builds[0] if builds else None)
    genealogy_by_build=defaultdict(list)
    for g in rows["genealogy"]: genealogy_by_build[g.build_id].append(g)
    links_by_build=defaultdict(list)
    for l in rows["defect_links"]: links_by_build[l.build_id].append(l)
    build_payload=[]
    for b in builds:
        gs=genealogy_by_build[b.id]; ls=links_by_build[b.id]
        defects=[rows["defects"][x.defect_id] for x in ls]
        open_critical=sum(d.status not in CLOSED_DEFECT and d.severity in {"high","critical"} for d in defects)
        item=serialize_build(b)
        item.update({"genealogy_items":len(gs),"defects":len(defects),"open_critical_defects":open_critical,
                     "quality_status":"RED" if open_critical else ("AMBER" if any(d.status not in CLOSED_DEFECT for d in defects) else "GREEN")})
        build_payload.append(item)
    selected_out=None
    if selected:
        gs=genealogy_by_build[selected.id]; ls=links_by_build[selected.id]
        expected=_expected_parts(db,project_code,selected.variant_id,{x.upper() for x in visible_part_numbers},visible_document_ids,manufacturing_area,allowed_area_codes)
        actual={x.part_number.upper() for x in gs}
        missing=sorted(expected-actual) if expected else []
        selected_out={**serialize_build(selected),"genealogy":[serialize_genealogy(x) for x in gs],
                      "defects":[_defect_payload(rows["defects"][x.defect_id],x) for x in ls],
                      "genealogy_coverage_pct":round(100*len(expected&actual)/len(expected),1) if expected else None,
                      "expected_part_count":len(expected),"observed_part_count":len(actual),"missing_expected_parts":missing,
                      "genealogy_status":"GREEN" if expected and not missing else ("AMBER" if not expected else "RED")}
    recurrence=_recurrence(builds,rows["genealogy"],rows["defect_links"],rows["defects"])
    safe=[serialize_safe_launch(x) for x in rows["safe_launch"]]
    safe_status="NOT_CONFIGURED" if not safe else ("RED" if any(x["defect_quantity"]>0 for x in safe) else ("GREEN" if all(x["status"]=="exited" for x in safe) else "AMBER"))
    loop=_feedback_loop(db,project_code,rows["defect_links"],rows["defects"],builds,visible_document_ids)
    completed=[b for b in builds if b.status in {"completed","passed","failed"} or b.completed_at]
    total_defects=len(rows["defect_links"])
    pulse={"builds":len(builds),"completed_builds":len(completed),"linked_defects":total_defects,"recurring_issue_clusters":len(recurrence),
           "safe_launch_status":safe_status,"safe_launch_exit_candidates":sum(x["exit_candidate"] for x in safe),
           "feedback_loops":len(loop),"next_action":("Investigate recurring build issues" if recurrence else ("Review Safe Launch exit candidates" if any(x["exit_candidate"] for x in safe) else "Continue controlled build observation"))}
    return {"builds":build_payload,"selected_build":selected_out,"recurrence":recurrence,"safe_launch":{"status":safe_status,"controls":safe},
            "engineering_feedback_loop":loop,"launch_pulse":pulse,
            "governance":{"advisory_only":True,"read_only_source_systems":True,"not_mes_qms_or_erp":True,"human_safe_launch_exit_required":True,"human_root_cause_and_release_required":True,"causal_claims":False}}
