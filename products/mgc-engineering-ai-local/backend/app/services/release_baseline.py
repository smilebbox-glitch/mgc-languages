from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from collections import defaultdict
from typing import Iterable

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import (
    ArchitectureNode, BOMItem, ChangeRequest, CostBaseline, CostLine, DesignReview, Document, EngineeringRequirement,
    InterfaceDefinition, LocalizationItem, ManufacturingLine, PartRevision, PPAPSubmission, ProcessOperation, ProcessStation, ReleaseBaseline,
    RequirementVerification, ValidationIssue, VehicleVariant, ConfigurationApplicability,
    ManufacturingBOMItem, ConfigurationEffectivity, ChangeCutIn, PartSupersession,
)


def _dt(value):
    return value.isoformat() if value else None


def _canonical_hash(payload: dict | list) -> str:
    raw=json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _status(value) -> str:
    return value.value if hasattr(value, "value") else str(value)


def _bom_row(row: BOMItem) -> dict:
    return {
        "id": row.id,
        "parent_part_number": row.parent_part_number,
        "parent_revision": row.parent_revision,
        "child_part_number": row.child_part_number,
        "child_revision": row.child_revision,
        "quantity": float(row.quantity or 0),
        "unit": row.unit or "pcs",
        "description": row.description,
        "position": row.position,
        "supplier_code": row.supplier_code,
        "supplier_name": row.supplier_name,
        "unit_cost": row.unit_cost,
        "currency": row.currency,
        "source_document_id": row.source_document_id,
    }


def _normalize_bom(rows: list[BOMItem] | list[dict]) -> list[dict]:
    out=[]
    for r in rows:
        x=_bom_row(r) if isinstance(r, BOMItem) else dict(r)
        x.pop("id", None)
        out.append(x)
    return sorted(out, key=lambda x: (x.get("parent_part_number") or "", x.get("position") or "", x.get("child_part_number") or "", x.get("child_revision") or ""))


def list_bom_versions(db: Session, project_code: str, visible_document_ids: set[str], parent_part_number: str | None = None, manufacturing_area: str | None = None) -> list[dict]:
    q=select(BOMItem)
    if parent_part_number:
        q=q.where(BOMItem.parent_part_number==parent_part_number.upper())
    rows=[r for r in db.scalars(q).all() if r.source_document_id in visible_document_ids]
    by_doc: dict[str,list[BOMItem]]=defaultdict(list)
    for row in rows: by_doc[row.source_document_id].append(row)
    result=[]
    for doc_id, items in by_doc.items():
        doc=db.get(Document,doc_id)
        if not doc or doc.project_code!=project_code: continue
        if manufacturing_area and doc.manufacturing_area not in {None, manufacturing_area}: continue
        normalized=_normalize_bom(items)
        total_qty=round(sum(float(x.get("quantity") or 0) for x in normalized),4)
        result.append({
            "document_id":doc.id,"filename":doc.filename,"revision":doc.revision,"parent_part_number":items[0].parent_part_number,
            "parent_revision":items[0].parent_revision,"version_label":doc.revision or doc.filename,
            "created_at":_dt(doc.created_at),"sha256":doc.sha256,"items_count":len(normalized),"total_quantity":total_qty,
            "fingerprint":_canonical_hash(normalized),"manufacturing_area":doc.manufacturing_area,
        })
    return sorted(result,key=lambda x:(x["parent_part_number"],x["created_at"] or "",x["version_label"]))


def _aggregate_by_part(rows: list[dict]) -> dict[str,dict]:
    grouped: dict[str,list[dict]]=defaultdict(list)
    for r in rows: grouped[(r.get("child_part_number") or "").upper()].append(r)
    out={}
    for pn, items in grouped.items():
        if not pn: continue
        first=items[0]
        out[pn]={
            "child_part_number":pn,
            "child_revision": next((x.get("child_revision") for x in items if x.get("child_revision")), None),
            "quantity": round(sum(float(x.get("quantity") or 0) for x in items),6),
            "unit": first.get("unit") or "pcs",
            "description": next((x.get("description") for x in items if x.get("description")), None),
            "positions": sorted({str(x.get("position")) for x in items if x.get("position")}),
            "supplier_code": next((x.get("supplier_code") for x in items if x.get("supplier_code")), None),
            "supplier_name": next((x.get("supplier_name") for x in items if x.get("supplier_name")), None),
            "unit_cost": next((x.get("unit_cost") for x in items if x.get("unit_cost") is not None), None),
            "currency": next((x.get("currency") for x in items if x.get("currency")), None),
        }
    return out


def _bom_cost_summary(rows: list[dict]) -> dict:
    totals: dict[str, float] = defaultdict(float)
    priced=0
    for row in rows:
        cost=row.get("unit_cost")
        currency=(row.get("currency") or "").upper()
        if cost is None or not currency:
            continue
        priced += 1
        totals[currency] += float(row.get("quantity") or 0) * float(cost)
    return {
        "rows":len(rows),
        "priced_rows":priced,
        "coverage":round(priced/len(rows),4) if rows else 1.0,
        "totals":{k:round(v,4) for k,v in sorted(totals.items())},
    }


def compare_bom_rows(left_rows: list[dict], right_rows: list[dict]) -> dict:
    left=_aggregate_by_part(left_rows); right=_aggregate_by_part(right_rows)
    left_pos={p:pn for pn,x in left.items() for p in x.get("positions",[]) if p}
    right_pos={p:pn for pn,x in right.items() for p in x.get("positions",[]) if p}
    replacements=[]; replaced_left=set(); replaced_right=set()
    for pos in sorted(set(left_pos)&set(right_pos)):
        lp,rp=left_pos[pos],right_pos[pos]
        if lp!=rp:
            replacements.append({"position":pos,"from":left[lp],"to":right[rp]})
            replaced_left.add(lp);replaced_right.add(rp)
    added=[right[pn] for pn in sorted(set(right)-set(left)-replaced_right)]
    removed=[left[pn] for pn in sorted(set(left)-set(right)-replaced_left)]
    changed=[]; moved=[]
    fields=("child_revision","quantity","unit","description","supplier_code","supplier_name","unit_cost","currency")
    common=set(left)&set(right)
    for pn in sorted(common):
        diffs={}
        for field in fields:
            a,b=left[pn].get(field),right[pn].get(field)
            if a!=b: diffs[field]={"from":a,"to":b}
        apos=left[pn].get("positions") or []; bpos=right[pn].get("positions") or []
        if apos!=bpos:
            moved.append({"child_part_number":pn,"from_positions":apos,"to_positions":bpos,"from":left[pn],"to":right[pn]})
        if diffs: changed.append({"child_part_number":pn,"changes":diffs,"from":left[pn],"to":right[pn]})
    left_cost=_bom_cost_summary(left_rows); right_cost=_bom_cost_summary(right_rows)
    currencies=set(left_cost["totals"])|set(right_cost["totals"])
    cost={"left":left_cost,"right":right_cost,"comparable":False,"currency":None,"delta":None}
    if left_cost["coverage"]==1.0 and right_cost["coverage"]==1.0 and len(currencies)==1:
        currency=next(iter(currencies))
        cost.update({
            "comparable":True,
            "currency":currency,
            "delta":round(right_cost["totals"].get(currency,0.0)-left_cost["totals"].get(currency,0.0),4),
        })
    return {
        "summary":{"added":len(added),"removed":len(removed),"replaced":len(replacements),"moved":len(moved),"changed":len(changed),"unchanged":len(common)-len(changed)-sum(1 for x in moved if x["child_part_number"] not in {c["child_part_number"] for c in changed})},
        "added":added,"removed":removed,"replaced":replacements,"moved":moved,"changed":changed,
        "cost":cost,
        "has_changes":bool(added or removed or replacements or moved or changed),
    }


def compare_bom_versions(db: Session, project_code: str, visible_document_ids: set[str], left_document_id: str, right_document_id: str, parent_part_number: str | None = None) -> dict:
    if left_document_id==right_document_id: raise ValueError("Choose two different BOM versions")
    docs=[]
    for doc_id in (left_document_id,right_document_id):
        doc=db.get(Document,doc_id)
        if not doc or doc.id not in visible_document_ids or doc.project_code!=project_code: raise LookupError("BOM version not found")
        docs.append(doc)
    rows=[]
    for doc in docs:
        q=select(BOMItem).where(BOMItem.source_document_id==doc.id)
        if parent_part_number: q=q.where(BOMItem.parent_part_number==parent_part_number.upper())
        rows.append(_normalize_bom(list(db.scalars(q).all())))
    if not rows[0] or not rows[1]: raise LookupError("BOM items not found for selected version")
    diff=compare_bom_rows(rows[0],rows[1])
    diff.update({
        "project_code":project_code,
        "parent_part_number":parent_part_number.upper() if parent_part_number else (rows[1][0].get("parent_part_number") or rows[0][0].get("parent_part_number")),
        "left":{"document_id":docs[0].id,"filename":docs[0].filename,"revision":docs[0].revision,"sha256":docs[0].sha256,"fingerprint":_canonical_hash(rows[0])},
        "right":{"document_id":docs[1].id,"filename":docs[1].filename,"revision":docs[1].revision,"sha256":docs[1].sha256,"fingerprint":_canonical_hash(rows[1])},
        "advisory_only":True,
    })
    return diff


def _area_ok(area: str | None, requested: str | None, allowed: set[str]) -> bool:
    if area and area not in allowed: return False
    if requested: return area in {None,requested}
    return True


def build_release_snapshot(db: Session, project, visible_document_ids: set[str], visible_part_numbers: set[str], allowed_area_codes: set[str], variant_id: str | None=None, manufacturing_area: str | None=None) -> tuple[dict,bool,list[str]]:
    docs=[d for d in db.scalars(select(Document).where(Document.project_code==project.code)).all() if d.id in visible_document_ids and _area_ok(d.manufacturing_area,manufacturing_area,allowed_area_codes)]
    variant=None; applicability=[]; included_parts=set(); excluded_parts=set(); included_docs=set(); excluded_docs=set()
    if variant_id:
        variant=db.get(VehicleVariant,variant_id)
        if not variant or variant.project_code!=project.code or not _area_ok(variant.manufacturing_area,manufacturing_area,allowed_area_codes): raise LookupError("Vehicle variant not found")
        if variant.evidence_document_ids and not set(variant.evidence_document_ids).issubset(visible_document_ids): raise LookupError("Vehicle variant not found")
        applicability=[x for x in db.scalars(select(ConfigurationApplicability).where(ConfigurationApplicability.project_code==project.code,ConfigurationApplicability.variant_id==variant.id)).all() if _area_ok(x.manufacturing_area,manufacturing_area,allowed_area_codes) and (not x.evidence_document_ids or set(x.evidence_document_ids).issubset(visible_document_ids))]
        for x in applicability:
            if x.entity_type=="part": (included_parts if x.applicability=="included" else excluded_parts).add(x.entity_key.upper())
            if x.entity_type=="document": (included_docs if x.applicability=="included" else excluded_docs).add(x.entity_key)
    filtered_docs=[]; unknown_docs=[]
    for d in docs:
        if d.id in excluded_docs or (d.part_number and d.part_number in excluded_parts): continue
        if variant and d.part_number and d.part_number not in included_parts and d.id not in included_docs:
            unknown_docs.append(d.id); continue
        filtered_docs.append(d)
    docs=filtered_docs
    doc_ids={d.id for d in docs}; parts={d.part_number for d in docs if d.part_number}
    if project.root_part_number: parts.add(project.root_part_number.upper())
    unknown_parts=[]
    if variant:
        candidate_parts={p for p in visible_part_numbers if p not in excluded_parts}
        unknown_parts=sorted(p for p in candidate_parts if p not in included_parts)
    bom_rows=[r for r in db.scalars(select(BOMItem)).all() if r.source_document_id in doc_ids and _area_ok((db.get(Document,r.source_document_id).manufacturing_area if db.get(Document,r.source_document_id) else None),manufacturing_area,allowed_area_codes)]
    if variant:
        bom_rows=[r for r in bom_rows if r.child_part_number not in excluded_parts and r.parent_part_number not in excluded_parts]
    normalized_bom=_normalize_bom(bom_rows)
    revisions=[]
    for r in db.scalars(select(PartRevision)).all():
        if r.part_number not in parts: continue
        visible_rdocs=[x for x in (r.document_ids or []) if x in doc_ids]
        if visible_rdocs: revisions.append({"part_number":r.part_number,"revision":r.revision,"document_ids":visible_rdocs,"metadata":r.metadata_json or {}})
    requirements=[]
    req_ids=set()
    for r in db.scalars(select(EngineeringRequirement).where(EngineeringRequirement.project_code==project.code)).all():
        if not _area_ok(r.manufacturing_area,manufacturing_area,allowed_area_codes): continue
        if r.source_document_id and r.source_document_id not in doc_ids: continue
        if r.part_numbers and not set(x.upper() for x in r.part_numbers)&parts: continue
        req_ids.add(r.id); requirements.append({"id":r.id,"code":r.code,"criticality":r.criticality,"status":r.status,"title":r.title,"source_document_id":r.source_document_id,"part_numbers":r.part_numbers or [],"updated_at":_dt(r.updated_at)})
    verifications=[]
    for v in db.scalars(select(RequirementVerification).where(RequirementVerification.project_code==project.code)).all():
        if v.requirement_id not in req_ids: continue
        if v.evidence_document_ids and not set(v.evidence_document_ids).issubset(doc_ids): continue
        verifications.append({"id":v.id,"requirement_id":v.requirement_id,"code":v.code,"phase":v.phase,"status":v.status,"evidence_document_ids":v.evidence_document_ids or [],"performed_at":_dt(v.performed_at),"requirement_updated_at_snapshot":_dt(v.requirement_updated_at_snapshot),"source_document_sha256_snapshot":v.source_document_sha256_snapshot})
    ppap=[]
    for p in db.scalars(select(PPAPSubmission).where(PPAPSubmission.project_code==project.code)).all():
        if p.part_number not in parts or not _area_ok(p.manufacturing_area,manufacturing_area,allowed_area_codes): continue
        if p.evidence_document_ids and not set(p.evidence_document_ids).issubset(doc_ids): continue
        ppap.append({"id":p.id,"part_number":p.part_number,"revision":p.revision,"supplier_code":p.supplier_code,"supplier_name":p.supplier_name,"status":p.status,"approved_at":_dt(p.approved_at),"evidence_document_ids":p.evidence_document_ids or []})
    suppliers=[]
    for s in db.scalars(select(LocalizationItem).where(LocalizationItem.project_code==project.code)).all():
        if s.part_number not in parts or not _area_ok(s.manufacturing_area,manufacturing_area,allowed_area_codes): continue
        if s.evidence_document_ids and not set(s.evidence_document_ids).issubset(doc_ids): continue
        suppliers.append({"id":s.id,"part_number":s.part_number,"revision":s.revision,"supplier_code":s.supplier_code,"supplier_name":s.supplier_name,"status":s.status,"localization_percent":s.localization_percent,"capacity_status":s.capacity_status,"tooling_status":s.tooling_status})
    changes=[]
    for c in db.scalars(select(ChangeRequest).order_by(ChangeRequest.updated_at)).all():
        if c.part_number and c.part_number not in parts: continue
        changes.append({"id":c.id,"code":c.code,"eco_code":c.eco_code,"part_number":c.part_number,"from_revision":c.from_revision,"to_revision":c.to_revision,"status":c.status,"completed_at":_dt(c.completed_at)})
    reviews=[]
    for r in db.scalars(select(DesignReview)).all():
        if r.part_number not in parts: continue
        if r.evidence_document_ids and not set(r.evidence_document_ids).issubset(doc_ids): continue
        reviews.append({"id":r.id,"part_number":r.part_number,"revision":r.revision,"status":_status(r.status),"risk_score":r.risk_score,"evidence_document_ids":r.evidence_document_ids or []})
    critical_issues=[]
    for i in db.scalars(select(ValidationIssue)).all():
        if _status(i.status)=="resolved" or _status(i.severity)!="critical": continue
        if i.document_ids and not set(i.document_ids).issubset(doc_ids): continue
        if not i.document_ids and i.part_number not in parts: continue
        critical_issues.append({"id":i.id,"part_number":i.part_number,"rule_code":i.rule_code,"title":i.title})

    # v5.1: richer immutable thread snapshot. These are advisory engineering views only.
    process_operations=[]
    lines=[x for x in db.scalars(select(ManufacturingLine).where(ManufacturingLine.project_code==project.code)).all() if _area_ok(x.manufacturing_area,manufacturing_area,allowed_area_codes)]
    line_by_id={x.id:x for x in lines}
    stations=db.scalars(select(ProcessStation).where(ProcessStation.line_id.in_(set(line_by_id)))).all() if line_by_id else []
    station_by_id={x.id:x for x in stations}
    operations=db.scalars(select(ProcessOperation).where(ProcessOperation.station_id.in_(set(station_by_id)))).all() if station_by_id else []
    for op in operations:
        if not op.part_number or op.part_number not in parts: continue
        if op.work_instruction_document_ids and not set(op.work_instruction_document_ids).issubset(doc_ids): continue
        st=station_by_id[op.station_id];ln=line_by_id[st.line_id]
        process_operations.append({"id":op.id,"part_number":op.part_number,"line":ln.code,"station":st.code,"code":op.code,"name":op.name,"operation_type":op.operation_type,"cycle_time_sec":op.cycle_time_sec,"status":op.status,"manufacturing_area":ln.manufacturing_area,"work_instruction_document_ids":op.work_instruction_document_ids or []})

    cost_baselines={x.id:x for x in db.scalars(select(CostBaseline).where(CostBaseline.project_code==project.code)).all() if _area_ok(x.manufacturing_area,manufacturing_area,allowed_area_codes) and (not x.evidence_document_ids or set(x.evidence_document_ids).issubset(doc_ids))}
    cost_lines=[]
    for c in db.scalars(select(CostLine).where(CostLine.project_code==project.code)).all():
        if c.part_number not in parts or c.baseline_id not in cost_baselines or not _area_ok(c.manufacturing_area,manufacturing_area,allowed_area_codes): continue
        if c.evidence_document_ids and not set(c.evidence_document_ids).issubset(doc_ids): continue
        base=cost_baselines[c.baseline_id]
        cost_lines.append({"id":c.id,"part_number":c.part_number,"revision":c.revision,"baseline_code":base.code,"baseline_type":base.baseline_type,"currency":base.currency,"supplier_code":c.supplier_code,"supplier_name":c.supplier_name,"quantity_per_vehicle":c.quantity_per_vehicle,"mass_kg":c.mass_kg,"material_name":c.material_name,"supplier_unit_price":c.supplier_unit_price,"target_unit_cost":c.target_unit_cost,"calculation_mode":c.calculation_mode})

    architecture_nodes=[]
    arch_ids=set()
    for a in db.scalars(select(ArchitectureNode).where(ArchitectureNode.project_code==project.code)).all():
        if not _area_ok(a.manufacturing_area,manufacturing_area,allowed_area_codes): continue
        if a.evidence_document_ids and not set(a.evidence_document_ids).issubset(doc_ids): continue
        if a.part_number and a.part_number not in parts: continue
        arch_ids.add(a.id);architecture_nodes.append({"id":a.id,"code":a.code,"name":a.name,"node_type":a.node_type,"parent_node_id":a.parent_node_id,"part_number":a.part_number,"status":a.status,"manufacturing_area":a.manufacturing_area})
    interfaces=[]
    for itf in db.scalars(select(InterfaceDefinition).where(InterfaceDefinition.project_code==project.code)).all():
        if itf.source_node_id not in arch_ids or itf.target_node_id not in arch_ids: continue
        if not _area_ok(itf.manufacturing_area,manufacturing_area,allowed_area_codes): continue
        if itf.evidence_document_ids and not set(itf.evidence_document_ids).issubset(doc_ids): continue
        interfaces.append({"id":itf.id,"code":itf.code,"name":itf.name,"interface_type":itf.interface_type,"source_node_id":itf.source_node_id,"target_node_id":itf.target_node_id,"criticality":itf.criticality,"status":itf.status,"requirement_ids":itf.requirement_ids or [],"manufacturing_area":itf.manufacturing_area})

    # v5.5 freezes the manufacturing/configuration handover state alongside the engineering snapshot.
    # These rows are still advisory shadows of authoritative PLM/ERP/MES data and remain ACL filtered.
    manufacturing_bom=[]
    for m in db.scalars(select(ManufacturingBOMItem).where(ManufacturingBOMItem.project_code==project.code)).all():
        if not _area_ok(m.manufacturing_area,manufacturing_area,allowed_area_codes): continue
        if m.source_document_id and m.source_document_id not in doc_ids: continue
        if m.evidence_document_ids and not set(m.evidence_document_ids).issubset(doc_ids): continue
        if m.parent_part_number not in parts or m.child_part_number not in parts: continue
        if variant and m.variant_id not in {None,variant.id}: continue
        if variant and m.child_part_number not in included_parts: continue
        manufacturing_bom.append({"parent_part_number":m.parent_part_number,"parent_revision":m.parent_revision,"child_part_number":m.child_part_number,"child_revision":m.child_revision,"quantity":float(m.quantity or 0),"unit":m.unit,"position":m.position,"operation_code":m.operation_code,"supplier_code":m.supplier_code,"variant_id":m.variant_id,"source_system":m.source_system,"source_document_id":m.source_document_id,"manufacturing_area":m.manufacturing_area})

    configuration_effectivity=[]
    for e in db.scalars(select(ConfigurationEffectivity).where(ConfigurationEffectivity.project_code==project.code)).all():
        if not _area_ok(e.manufacturing_area,manufacturing_area,allowed_area_codes): continue
        if e.evidence_document_ids and not set(e.evidence_document_ids).issubset(doc_ids): continue
        if e.part_number not in parts: continue
        if variant and e.variant_id not in {None,variant.id}: continue
        configuration_effectivity.append({"part_number":e.part_number,"revision":e.revision,"variant_id":e.variant_id,"plant":e.plant,"market":e.market,"supplier_code":e.supplier_code,"vin_from":e.vin_from,"vin_to":e.vin_to,"serial_from":e.serial_from,"serial_to":e.serial_to,"effective_from":_dt(e.effective_from),"effective_to":_dt(e.effective_to),"status":e.status,"source":e.source,"manufacturing_area":e.manufacturing_area})

    change_cutins=[]
    for c in db.scalars(select(ChangeCutIn).where(ChangeCutIn.project_code==project.code)).all():
        if not _area_ok(c.manufacturing_area,manufacturing_area,allowed_area_codes): continue
        if c.evidence_document_ids and not set(c.evidence_document_ids).issubset(doc_ids): continue
        if c.part_number not in parts: continue
        if variant and c.variant_ids and variant.id not in c.variant_ids: continue
        change_cutins.append({"code":c.code,"change_id":c.change_id,"part_number":c.part_number,"from_revision":c.from_revision,"to_revision":c.to_revision,"variant_ids":c.variant_ids or [],"plant":c.plant,"line_id":c.line_id,"cut_in_at":_dt(c.cut_in_at),"vin_from":c.vin_from,"old_stock_qty":c.old_stock_qty,"new_stock_qty":c.new_stock_qty,"old_stock_disposition":c.old_stock_disposition,"logistics_confirmed":bool(c.logistics_confirmed),"status":c.status,"manufacturing_area":c.manufacturing_area})

    part_supersessions=[]
    for x in db.scalars(select(PartSupersession).where(PartSupersession.project_code==project.code)).all():
        if not _area_ok(x.manufacturing_area,manufacturing_area,allowed_area_codes): continue
        if x.evidence_document_ids and not set(x.evidence_document_ids).issubset(doc_ids): continue
        if x.old_part_number not in parts or x.new_part_number not in parts: continue
        part_supersessions.append({"old_part_number":x.old_part_number,"old_revision":x.old_revision,"new_part_number":x.new_part_number,"new_revision":x.new_revision,"interchangeable":bool(x.interchangeable),"retrofit_allowed":bool(x.retrofit_allowed),"stock_use_allowed":bool(x.stock_use_allowed),"status":x.status,"manufacturing_area":x.manufacturing_area})

    snapshot={
        "schema":"mgc-release-baseline-v3","project":{"code":project.code,"name":project.name,"phase":project.phase,"root_part_number":project.root_part_number},
        "variant":({"id":variant.id,"code":variant.code,"name":variant.name,"model_year":variant.model_year,"market":variant.market,"body_style":variant.body_style,"engine":variant.engine,"transmission":variant.transmission,"trim":variant.trim} if variant else None),
        "configuration":{"included_parts":sorted(included_parts),"excluded_parts":sorted(excluded_parts),"unknown_parts":unknown_parts,"unknown_document_ids":sorted(unknown_docs)},
        "documents":[{"id":d.id,"filename":d.filename,"sha256":d.sha256,"part_number":d.part_number,"revision":d.revision,"doc_type":d.doc_type,"manufacturing_area":d.manufacturing_area,"created_at":_dt(d.created_at)} for d in sorted(docs,key=lambda x:(x.part_number or "",x.doc_type or "",x.filename))],
        "part_revisions":sorted(revisions,key=lambda x:(x["part_number"],x["revision"])),
        "bom":normalized_bom,"bom_fingerprint":_canonical_hash(normalized_bom),
        "requirements":sorted(requirements,key=lambda x:x["code"]),"verifications":sorted(verifications,key=lambda x:x["code"]),
        "ppap":sorted(ppap,key=lambda x:(x["part_number"],x.get("supplier_code") or "")),"suppliers":sorted(suppliers,key=lambda x:(x["part_number"],x["supplier_code"])),
        "changes":changes,"design_reviews":reviews,"critical_issues":critical_issues,
        "process_operations":sorted(process_operations,key=lambda x:(x["part_number"],x["line"],x["station"],x["code"])),
        "cost_lines":sorted(cost_lines,key=lambda x:(x["part_number"],x["baseline_code"],x.get("supplier_code") or "")),
        "architecture_nodes":sorted(architecture_nodes,key=lambda x:x["code"]),
        "interfaces":sorted(interfaces,key=lambda x:x["code"]),
        "manufacturing_bom":sorted(manufacturing_bom,key=lambda x:(x.get("parent_part_number") or "",x.get("position") or "",x.get("child_part_number") or "")),
        "configuration_effectivity":sorted(configuration_effectivity,key=lambda x:(x.get("part_number") or "",x.get("revision") or "",x.get("plant") or "",x.get("vin_from") or "")),
        "change_cutins":sorted(change_cutins,key=lambda x:(x.get("part_number") or "",x.get("code") or "")),
        "part_supersessions":sorted(part_supersessions,key=lambda x:(x.get("old_part_number") or "",x.get("old_revision") or "",x.get("new_part_number") or "")),
        "captured_at":datetime.now(timezone.utc).isoformat(),
    }
    warnings=[]
    if unknown_parts: warnings.append(f"{len(unknown_parts)} parts have UNKNOWN variant applicability")
    if unknown_docs: warnings.append(f"{len(unknown_docs)} documents have UNKNOWN variant applicability")
    if critical_issues: warnings.append(f"{len(critical_issues)} critical validation issues are open")
    failed=[d for d in docs if _status(d.status)=="failed"]
    if failed: warnings.append(f"{len(failed)} source documents are failed")
    release_candidate=not warnings
    snapshot["warnings"]=warnings;snapshot["release_candidate"]=release_candidate
    return snapshot,release_candidate,warnings


def create_release_baseline(db: Session, project, *, code: str, name: str, baseline_type: str, created_by: str, visible_document_ids: set[str], visible_part_numbers: set[str], allowed_area_codes: set[str], variant_id: str | None=None, manufacturing_area: str | None=None, root_part_number: str | None=None, notes: str | None=None) -> ReleaseBaseline:
    snapshot,candidate,warnings=build_release_snapshot(db,project,visible_document_ids,visible_part_numbers,allowed_area_codes,variant_id,manufacturing_area)
    if root_part_number: snapshot["project"]["root_part_number"]=root_part_number.upper()
    fingerprint=_canonical_hash(snapshot)
    row=ReleaseBaseline(project_code=project.code,manufacturing_area=manufacturing_area,variant_id=variant_id,code=code.upper(),name=name.strip(),baseline_type=baseline_type,root_part_number=(root_part_number or project.root_part_number),status="frozen",snapshot_json=snapshot,fingerprint=fingerprint,source_document_ids=[d["id"] for d in snapshot["documents"]],release_candidate=candidate,created_by=created_by,notes=notes,metadata_json={"warnings":warnings,"immutable":True,"human_release_approval_required":True})
    db.add(row);db.commit();db.refresh(row);return row


def serialize_release_baseline(row: ReleaseBaseline, visible_document_ids: set[str], include_snapshot: bool=False) -> dict:
    if row.source_document_ids and not set(row.source_document_ids).issubset(visible_document_ids): raise LookupError("Release baseline not found")
    snap=row.snapshot_json or {}
    out={"id":row.id,"project_code":row.project_code,"manufacturing_area":row.manufacturing_area,"variant_id":row.variant_id,"code":row.code,"name":row.name,"baseline_type":row.baseline_type,"root_part_number":row.root_part_number,"status":row.status,"fingerprint":row.fingerprint,"release_candidate":row.release_candidate,"created_by":row.created_by,"frozen_at":_dt(row.frozen_at),"notes":row.notes,"warnings":(row.metadata_json or {}).get("warnings",[]),"counts":{"documents":len(snap.get("documents",[])),"bom_items":len(snap.get("bom",[])),"requirements":len(snap.get("requirements",[])),"verifications":len(snap.get("verifications",[])),"ppap":len(snap.get("ppap",[])),"suppliers":len(snap.get("suppliers",[])),"changes":len(snap.get("changes",[])),"process_operations":len(snap.get("process_operations",[])),"cost_lines":len(snap.get("cost_lines",[])),"architecture_nodes":len(snap.get("architecture_nodes",[])),"interfaces":len(snap.get("interfaces",[])),"manufacturing_bom":len(snap.get("manufacturing_bom",[])),"configuration_effectivity":len(snap.get("configuration_effectivity",[])),"change_cutins":len(snap.get("change_cutins",[])),"part_supersessions":len(snap.get("part_supersessions",[]))},"immutable":True,"human_release_approval_required":True}
    if include_snapshot: out["snapshot"]=snap
    return out


def release_workspace(db: Session, project_code: str, visible_document_ids: set[str], parent_part_number: str | None=None, manufacturing_area: str | None=None) -> dict:
    baselines=[]
    for row in db.scalars(select(ReleaseBaseline).where(ReleaseBaseline.project_code==project_code).order_by(ReleaseBaseline.frozen_at.desc())).all():
        if manufacturing_area and row.manufacturing_area not in {None, manufacturing_area}: continue
        try: baselines.append(serialize_release_baseline(row,visible_document_ids,False))
        except LookupError: continue
    versions=list_bom_versions(db,project_code,visible_document_ids,parent_part_number,manufacturing_area)
    return {"configured":bool(baselines or versions),"baselines":baselines,"bom_versions":versions,"counts":{"baselines":len(baselines),"bom_versions":len(versions)},"advisory_only":True,"immutable_baselines":True,"human_release_approval_required":True}


def compare_release_baselines(left: ReleaseBaseline, right: ReleaseBaseline) -> dict:
    a=left.snapshot_json or {};b=right.snapshot_json or {}
    adocs={x["id"]:x for x in a.get("documents",[])};bdocs={x["id"]:x for x in b.get("documents",[])}
    added_docs=[bdocs[k] for k in sorted(set(bdocs)-set(adocs))];removed_docs=[adocs[k] for k in sorted(set(adocs)-set(bdocs))]
    changed_docs=[]
    # Same engineering slot but changed content/revision/document id.
    def slot(x): return (x.get("part_number"),x.get("doc_type"),x.get("filename"))
    aslots={slot(x):x for x in adocs.values()};bslots={slot(x):x for x in bdocs.values()}
    for k in sorted(set(aslots)&set(bslots),key=str):
        x,y=aslots[k],bslots[k]
        if x.get("sha256")!=y.get("sha256") or x.get("revision")!=y.get("revision"):
            changed_docs.append({"from":x,"to":y})
    bom=compare_bom_rows(a.get("bom",[]),b.get("bom",[]))
    av={(x.get("code"),x.get("status")) for x in a.get("requirements",[])};bv={(x.get("code"),x.get("status")) for x in b.get("requirements",[])}
    return {"left":{"id":left.id,"code":left.code,"fingerprint":left.fingerprint},"right":{"id":right.id,"code":right.code,"fingerprint":right.fingerprint},"same_fingerprint":left.fingerprint==right.fingerprint,"documents":{"added":added_docs,"removed":removed_docs,"changed":changed_docs},"bom":bom,"requirements":{"added":[x for x in b.get("requirements",[]) if (x.get("code"),x.get("status")) not in av],"removed":[x for x in a.get("requirements",[]) if (x.get("code"),x.get("status")) not in bv]},"advisory_only":True}
