from __future__ import annotations

import hashlib
import json
from datetime import timezone
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import ArchitectureNode, InterfaceDefinition, InterfaceVerification, EngineeringRequirement, RequirementVerification, ChangeRequest, CostLine, LocalizationItem
from app.services.requirements_matrix import requirements_matrix

CRITICAL = {"critical", "safety", "regulatory"}
TERMINAL_CHANGE = {"implemented", "rejected", "cancelled"}


def _dt(v): return v.isoformat() if v else None

def _in_area(area, requested, allowed):
    if area and allowed is not None and area not in allowed: return False
    if requested: return area in {None, requested}
    return True

def _visible_evidence(ids, visible_document_ids): return [x for x in (ids or []) if x in visible_document_ids]

def serialize_node(x, visible_document_ids=None):
    return {"id":x.id,"project_code":x.project_code,"manufacturing_area":x.manufacturing_area,"code":x.code,"name":x.name,"node_type":x.node_type,"parent_node_id":x.parent_node_id,"part_number":x.part_number,"status":x.status,"owner":x.owner,"description":x.description,"evidence_document_ids":_visible_evidence(x.evidence_document_ids, visible_document_ids or set(x.evidence_document_ids or [])),"created_by":x.created_by,"metadata":x.metadata_json or {},"created_at":_dt(x.created_at),"updated_at":_dt(x.updated_at)}

def interface_fingerprint(x: InterfaceDefinition, node_map: dict[str,ArchitectureNode]) -> str:
    a=node_map.get(x.source_node_id); b=node_map.get(x.target_node_id)
    payload={"code":x.code,"type":x.interface_type,"source":(a.code,a.part_number,a.updated_at.isoformat() if a and a.updated_at else None) if a else None,"target":(b.code,b.part_number,b.updated_at.isoformat() if b and b.updated_at else None) if b else None,"criticality":x.criticality,"requirements":sorted(x.requirement_ids or []),"specifications":x.specifications_json or {},"status":x.status,"updated_at":x.updated_at.isoformat() if x.updated_at else None}
    return hashlib.sha256(json.dumps(payload,sort_keys=True,ensure_ascii=False,default=str).encode()).hexdigest()

def _verification_view(db, v, interface, node_map, visible_document_ids, effective_req_verifications):
    evidence=_visible_evidence(v.evidence_document_ids,visible_document_ids)
    req_ok=bool(v.linked_requirement_verification_id and v.linked_requirement_verification_id in effective_req_verifications)
    proof_ok=bool(evidence or req_ok)
    current=interface_fingerprint(interface,node_map)
    stale=bool(v.status=="passed" and v.interface_fingerprint_snapshot!=current)
    effective_pass=bool(v.status=="passed" and proof_ok and not stale)
    return {"id":v.id,"project_code":v.project_code,"interface_id":v.interface_id,"manufacturing_area":v.manufacturing_area,"code":v.code,"verification_type":v.verification_type,"title":v.title,"status":v.status,"effective_pass":effective_pass,"stale":stale,"proof_ok":proof_ok,"result_summary":v.result_summary,"measured_result":v.measured_result_json or {},"evidence_document_ids":evidence,"linked_requirement_verification_id":v.linked_requirement_verification_id,"performed_by":v.performed_by,"performed_at":_dt(v.performed_at),"notes":v.notes,"created_by":v.created_by,"created_at":_dt(v.created_at),"updated_at":_dt(v.updated_at)}

def _tree(nodes, visible_document_ids):
    by_parent={}
    views={x.id:{**serialize_node(x, visible_document_ids),"children":[]} for x in nodes}
    for x in nodes: by_parent.setdefault(x.parent_node_id,[]).append(x)
    def walk(parent, seen):
        out=[]
        for x in sorted(by_parent.get(parent,[]),key=lambda y:(y.node_type,y.code)):
            if x.id in seen: continue
            item=views[x.id].copy(); item["children"]=walk(x.id,seen|{x.id}); out.append(item)
        return out
    roots=walk(None,set())
    attached={x["id"] for x in roots}
    # Orphans/cyclic nodes remain visible as roots rather than disappearing.
    root_ids=set()
    def collect(rows):
        for r in rows: root_ids.add(r["id"]); collect(r["children"])
    collect(roots)
    for x in nodes:
        if x.id not in root_ids:
            item=views[x.id].copy(); item["children"]=[]; roots.append(item)
    return roots

def vehicle_architecture_workspace(db:Session, project_code:str, visible_document_ids:set[str], visible_part_numbers:set[str], manufacturing_area:str|None=None, allowed_area_codes:set[str]|None=None):
    all_nodes=db.scalars(select(ArchitectureNode).where(ArchitectureNode.project_code==project_code).order_by(ArchitectureNode.code)).all()
    nodes=[]
    for x in all_nodes:
        if not _in_area(x.manufacturing_area,manufacturing_area,allowed_area_codes): continue
        if x.part_number and x.part_number not in visible_part_numbers: continue
        if x.evidence_document_ids and not set(x.evidence_document_ids).issubset(visible_document_ids): continue
        nodes.append(x)
    node_map={x.id:x for x in nodes}

    req_ws=requirements_matrix(db,project_code,visible_document_ids,visible_part_numbers,manufacturing_area,allowed_area_codes)
    visible_req_ids={x["id"] for x in req_ws.get("requirements",[])}
    effective_req_v=set()
    for r in req_ws.get("requirements",[]):
        for v in r.get("verifications",[]):
            if v.get("effective_pass"): effective_req_v.add(v["id"])

    interfaces=[]
    for x in db.scalars(select(InterfaceDefinition).where(InterfaceDefinition.project_code==project_code).order_by(InterfaceDefinition.code)).all():
        if not _in_area(x.manufacturing_area,manufacturing_area,allowed_area_codes): continue
        if x.source_node_id not in node_map or x.target_node_id not in node_map: continue
        if x.evidence_document_ids and not set(x.evidence_document_ids).issubset(visible_document_ids): continue
        interfaces.append(x)
    interface_ids={x.id for x in interfaces}
    raw_v=[x for x in db.scalars(select(InterfaceVerification).where(InterfaceVerification.project_code==project_code).order_by(InterfaceVerification.code)).all() if x.interface_id in interface_ids and _in_area(x.manufacturing_area,manufacturing_area,allowed_area_codes)]
    by_if={}
    for v in raw_v: by_if.setdefault(v.interface_id,[]).append(v)

    gaps=[]; interface_views=[]; verified=0; traceable=0
    for x in interfaces:
        req_ids=[rid for rid in (x.requirement_ids or []) if rid in visible_req_ids]
        vv=[_verification_view(db,v,x,node_map,visible_document_ids,effective_req_v) for v in by_if.get(x.id,[])]
        effective=any(v["effective_pass"] for v in vv)
        critical=x.criticality in CRITICAL
        if req_ids: traceable+=1
        if effective: verified+=1
        sev="critical" if critical else "warning"
        if critical and not req_ids: gaps.append({"type":"interface_requirement","severity":"critical","id":x.id,"title":f"{x.code}: критичный интерфейс не связан с требованием"})
        elif not req_ids: gaps.append({"type":"interface_requirement","severity":"warning","id":x.id,"title":f"{x.code}: интерфейс не связан с требованием"})
        if x.status in {"active","released"} and not effective:
            failed=any(v["status"]=="failed" for v in vv); stale=any(v["stale"] for v in vv if v["status"]=="passed"); no_proof=any(v["status"]=="passed" and not v["proof_ok"] for v in vv)
            if failed: gaps.append({"type":"interface_failed","severity":"critical" if critical else "warning","id":x.id,"title":f"{x.code}: interface verification FAILED"})
            elif stale: gaps.append({"type":"interface_stale","severity":sev,"id":x.id,"title":f"{x.code}: подтверждение устарело после изменения интерфейса"})
            elif no_proof: gaps.append({"type":"interface_evidence","severity":sev,"id":x.id,"title":f"{x.code}: PASSED не подтверждён доступным evidence"})
            else: gaps.append({"type":"interface_unverified","severity":sev,"id":x.id,"title":f"{x.code}: интерфейс ещё не подтверждён"})
        visible_linked_changes=[]; open_changes=[]
        for cid in x.linked_change_ids or []:
            c=db.get(ChangeRequest,cid)
            if c and (not c.part_number or c.part_number in visible_part_numbers):
                view={"id":c.id,"code":c.eco_code or c.code,"status":c.status,"part_number":c.part_number}
                visible_linked_changes.append(view)
                if c.status not in TERMINAL_CHANGE: open_changes.append(view)
        if open_changes: gaps.append({"type":"interface_change","severity":"warning","id":x.id,"title":f"{x.code}: есть незавершённое связанное ECR/ECO"})
        interface_views.append({"id":x.id,"project_code":x.project_code,"manufacturing_area":x.manufacturing_area,"code":x.code,"name":x.name,"interface_type":x.interface_type,"source_node_id":x.source_node_id,"target_node_id":x.target_node_id,"source":serialize_node(node_map[x.source_node_id],visible_document_ids),"target":serialize_node(node_map[x.target_node_id],visible_document_ids),"criticality":x.criticality,"status":x.status,"owner":x.owner,"requirement_ids":req_ids,"linked_change_ids":[c["id"] for c in visible_linked_changes],"open_changes":open_changes,"specifications":x.specifications_json or {},"evidence_document_ids":_visible_evidence(x.evidence_document_ids,visible_document_ids),"notes":x.notes,"fingerprint":interface_fingerprint(x,node_map),"verifications":vv,"verification_state":"verified" if effective else ("planned" if vv else "missing"),"created_at":_dt(x.created_at),"updated_at":_dt(x.updated_at)})

    configured=bool(nodes or interfaces)
    n=max(len(interfaces),1)
    trace_score=round(100*traceable/n,1) if interfaces else (100.0 if nodes else 0.0)
    verify_score=round(100*verified/n,1) if interfaces else (100.0 if nodes else 0.0)
    hierarchy_score=100.0 if not nodes else round(100*sum(1 for x in nodes if x.node_type=="vehicle" or x.parent_node_id in node_map)/len(nodes),1)
    score=round(hierarchy_score*.20+trace_score*.35+verify_score*.45,1) if configured else 0.0
    status="blocked" if any(x["severity"]=="critical" for x in gaps) else ("needs_review" if gaps or score<90 else "verified")
    return {"configured":configured,"score":score,"status":status,"advisory_only":True,"human_interface_approval_required":True,"gates":{"hierarchy":hierarchy_score if configured else None,"requirements":trace_score if configured else None,"verification":verify_score if configured else None},"counts":{"nodes":len(nodes),"interfaces":len(interfaces),"critical_interfaces":sum(x.criticality in CRITICAL for x in interfaces),"verified_interfaces":verified,"gaps":len(gaps)},"tree":_tree(nodes, visible_document_ids),"nodes":[serialize_node(x,visible_document_ids) for x in nodes],"interfaces":interface_views,"gaps":gaps,"recommended_checks":["Критичные интерфейсы имеют владельца, требования и подтверждение.","Механические интерфейсы проверены на геометрию/зазоры/крепёж и сопряжённые ревизии.","Электрические/data/control интерфейсы имеют согласованные параметры и V&V evidence.","После ECR/ECO или изменения сопряжённой детали interface verification пересмотрена.","Interface Matrix используется как инженерная трассировка, а не как автоматическое разрешение на выпуск."]}

def architecture_impact(db:Session, project_code:str, part_number:str, visible_document_ids:set[str], visible_part_numbers:set[str], manufacturing_area:str|None=None, allowed_area_codes:set[str]|None=None):
    ws=vehicle_architecture_workspace(db,project_code,visible_document_ids,visible_part_numbers,manufacturing_area,allowed_area_codes)
    pn=part_number.upper()
    seeds=[n for n in ws["nodes"] if n.get("part_number")==pn]
    seed_ids={n["id"] for n in seeds}
    interfaces=[x for x in ws["interfaces"] if x["source_node_id"] in seed_ids or x["target_node_id"] in seed_ids]
    adjacent=[]
    for x in interfaces:
        adjacent.append(x["target"] if x["source_node_id"] in seed_ids else x["source"])
    req_ids=sorted({rid for x in interfaces for rid in x.get("requirement_ids",[])})
    changes=[]
    for x in interfaces:
        changes.extend(x.get("open_changes",[]))
    cost_lines=[x for x in db.scalars(select(CostLine).where(CostLine.project_code==project_code,CostLine.part_number==pn)).all() if _in_area(x.manufacturing_area,manufacturing_area,allowed_area_codes)]
    localization=[x for x in db.scalars(select(LocalizationItem).where(LocalizationItem.project_code==project_code,LocalizationItem.part_number==pn)).all() if _in_area(x.manufacturing_area,manufacturing_area,allowed_area_codes)]
    return {"part_number":pn,"architecture_nodes":seeds,"connected_interfaces":interfaces,"adjacent_nodes":list({x["id"]:x for x in adjacent}.values()),"requirement_ids":req_ids,"open_changes":list({x["id"]:x for x in changes}.values()),"cost_line_ids":[x.id for x in cost_lines],"localization_item_ids":[x.id for x in localization],"impact_count":len(interfaces)+len(adjacent)+len(req_ids)+len(changes),"advisory_only":True}
