from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from collections import defaultdict

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import (
    AsBuiltConfiguration, BOMItem, ChangeCutIn, ConfigurationApplicability,
    ConfigurationEffectivity, Document, EngineeringDeviation, ManufacturingBOMItem,
    Part, PartSupersession, PPAPSubmission, ProcessOperation, ProcessStation,
    ManufacturingLine, ReleaseBaseline, VehicleVariant,
)
from app.services.release_baseline import build_release_snapshot


def _dt(v):
    return v.isoformat() if v else None


def _status(v):
    return v.value if hasattr(v, "value") else str(v)


def _area_ok(area: str | None, requested: str | None, allowed: set[str] | None) -> bool:
    if area and allowed is not None and area not in allowed:
        return False
    if requested:
        return area in {None, requested}
    return True


def _visible_evidence(ids: list[str] | None, visible_document_ids: set[str]) -> bool:
    return not ids or set(ids).issubset(visible_document_ids)


def _hash(payload) -> str:
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def serialize_mbom(x: ManufacturingBOMItem) -> dict:
    return {
        "id": x.id, "project_code": x.project_code, "manufacturing_area": x.manufacturing_area,
        "variant_id": x.variant_id, "parent_part_number": x.parent_part_number,
        "parent_revision": x.parent_revision, "child_part_number": x.child_part_number,
        "child_revision": x.child_revision, "quantity": float(x.quantity or 0), "unit": x.unit,
        "position": x.position, "operation_code": x.operation_code, "supplier_code": x.supplier_code,
        "source_system": x.source_system, "source_document_id": x.source_document_id,
        "evidence_document_ids": x.evidence_document_ids or [], "metadata": x.metadata_json or {},
        "created_at": _dt(x.created_at), "updated_at": _dt(x.updated_at),
    }


def serialize_effectivity(x: ConfigurationEffectivity) -> dict:
    return {
        "id": x.id, "project_code": x.project_code, "manufacturing_area": x.manufacturing_area,
        "variant_id": x.variant_id, "part_number": x.part_number, "revision": x.revision,
        "plant": x.plant, "market": x.market, "supplier_code": x.supplier_code,
        "vin_from": x.vin_from, "vin_to": x.vin_to, "serial_from": x.serial_from, "serial_to": x.serial_to,
        "effective_from": _dt(x.effective_from), "effective_to": _dt(x.effective_to),
        "status": x.status, "source": x.source, "evidence_document_ids": x.evidence_document_ids or [],
        "notes": x.notes, "metadata": x.metadata_json or {},
    }


def serialize_cutin(x: ChangeCutIn) -> dict:
    return {
        "id": x.id, "project_code": x.project_code, "manufacturing_area": x.manufacturing_area,
        "code": x.code, "change_id": x.change_id, "part_number": x.part_number,
        "from_revision": x.from_revision, "to_revision": x.to_revision, "variant_ids": x.variant_ids or [],
        "plant": x.plant, "line_id": x.line_id, "cut_in_at": _dt(x.cut_in_at), "vin_from": x.vin_from,
        "old_stock_qty": x.old_stock_qty, "new_stock_qty": x.new_stock_qty,
        "old_stock_disposition": x.old_stock_disposition, "logistics_confirmed": bool(x.logistics_confirmed),
        "status": x.status, "evidence_document_ids": x.evidence_document_ids or [], "notes": x.notes,
        "metadata": x.metadata_json or {},
    }


def serialize_as_built(x: AsBuiltConfiguration) -> dict:
    return {
        "id": x.id, "vehicle_identifier": x.vehicle_identifier, "variant_id": x.variant_id,
        "plant": x.plant, "built_at": _dt(x.built_at), "manufacturing_area": x.manufacturing_area,
        "part_number": x.part_number, "revision": x.revision, "supplier_code": x.supplier_code,
        "deviation_id": x.deviation_id, "source_system": x.source_system,
        "evidence_document_ids": x.evidence_document_ids or [], "metadata": x.metadata_json or {},
    }


def serialize_supersession(x: PartSupersession) -> dict:
    return {
        "id": x.id, "manufacturing_area": x.manufacturing_area,
        "old_part_number": x.old_part_number, "old_revision": x.old_revision,
        "new_part_number": x.new_part_number, "new_revision": x.new_revision,
        "interchangeable": bool(x.interchangeable), "retrofit_allowed": bool(x.retrofit_allowed),
        "stock_use_allowed": bool(x.stock_use_allowed), "status": x.status,
        "evidence_document_ids": x.evidence_document_ids or [], "notes": x.notes,
    }


def visible_assurance_rows(db: Session, project_code: str, visible_document_ids: set[str], visible_part_numbers: set[str], manufacturing_area: str | None = None, allowed_area_codes: set[str] | None = None) -> dict:
    visible_parts={p.upper() for p in visible_part_numbers}
    def ok_area(x): return _area_ok(getattr(x, "manufacturing_area", None), manufacturing_area, allowed_area_codes)
    def ok_evidence(x): return _visible_evidence(getattr(x, "evidence_document_ids", None), visible_document_ids)

    mbom=[]
    for x in db.scalars(select(ManufacturingBOMItem).where(ManufacturingBOMItem.project_code==project_code)).all():
        if not ok_area(x) or not ok_evidence(x): continue
        if x.source_document_id and x.source_document_id not in visible_document_ids: continue
        if x.parent_part_number.upper() not in visible_parts or x.child_part_number.upper() not in visible_parts: continue
        mbom.append(x)
    effectivity=[x for x in db.scalars(select(ConfigurationEffectivity).where(ConfigurationEffectivity.project_code==project_code)).all() if ok_area(x) and ok_evidence(x) and x.part_number.upper() in visible_parts]
    cutins=[x for x in db.scalars(select(ChangeCutIn).where(ChangeCutIn.project_code==project_code)).all() if ok_area(x) and ok_evidence(x) and x.part_number.upper() in visible_parts]
    as_built=[x for x in db.scalars(select(AsBuiltConfiguration).where(AsBuiltConfiguration.project_code==project_code)).all() if ok_area(x) and ok_evidence(x) and x.part_number.upper() in visible_parts]
    supersessions=[x for x in db.scalars(select(PartSupersession).where(PartSupersession.project_code==project_code)).all() if ok_area(x) and ok_evidence(x) and x.old_part_number.upper() in visible_parts and x.new_part_number.upper() in visible_parts]
    return {"mbom":mbom,"effectivity":effectivity,"cutins":cutins,"as_built":as_built,"supersessions":supersessions}


def _variant(db: Session, project_code: str, variant_id: str | None, visible_document_ids: set[str], manufacturing_area: str | None, allowed_area_codes: set[str] | None):
    if not variant_id: return None
    v=db.get(VehicleVariant,variant_id)
    if not v or v.project_code!=project_code or not _area_ok(v.manufacturing_area,manufacturing_area,allowed_area_codes) or not _visible_evidence(v.evidence_document_ids,visible_document_ids):
        raise LookupError("Vehicle variant not found")
    return v


def exact_variant_configuration(db: Session, project_code: str, variant: VehicleVariant | None, visible_parts: set[str], visible_document_ids: set[str], manufacturing_area: str | None, allowed_area_codes: set[str] | None) -> dict:
    if not variant:
        return {"configured":False,"variant":None,"included_parts":[],"excluded_parts":[],"unknown_parts":sorted(visible_parts),"exact_100_percent":False}
    rows=[]
    for x in db.scalars(select(ConfigurationApplicability).where(ConfigurationApplicability.project_code==project_code, ConfigurationApplicability.variant_id==variant.id, ConfigurationApplicability.entity_type=="part")).all():
        if not _area_ok(x.manufacturing_area,manufacturing_area,allowed_area_codes) or not _visible_evidence(x.evidence_document_ids,visible_document_ids): continue
        if x.entity_key.upper() not in visible_parts: continue
        rows.append(x)
    included={x.entity_key.upper() for x in rows if x.applicability=="included"}
    excluded={x.entity_key.upper() for x in rows if x.applicability=="excluded"}
    scoped=included|excluded
    unknown=set(visible_parts)-scoped
    return {
        "configured": bool(rows), "variant":{"id":variant.id,"code":variant.code,"name":variant.name,"market":variant.market,"trim":variant.trim,"engine":variant.engine,"transmission":variant.transmission},
        "included_parts":sorted(included), "excluded_parts":sorted(excluded), "unknown_parts":sorted(unknown),
        "exact_100_percent":bool(rows) and not unknown,
        "unknown_is_not_included":True,
    }


def _aggregate(rows: list[dict]) -> dict[str,dict]:
    out={}
    for r in rows:
        key=(r.get("position") or "").strip() or r["child_part_number"]
        if key in out:
            key=f"{key}|{r['child_part_number']}"
        out[key]=r
    return out


def reconcile_ebom_mbom(db: Session, project_code: str, visible_document_ids: set[str], visible_parts: set[str], assurance_rows: dict, variant: VehicleVariant | None, exact: dict, manufacturing_area: str | None=None) -> dict:
    docs={d.id:d for d in db.scalars(select(Document).where(Document.project_code==project_code)).all() if d.id in visible_document_ids}
    ebom=[]
    for x in db.scalars(select(BOMItem)).all():
        doc=docs.get(x.source_document_id)
        if not doc: continue
        if manufacturing_area and doc.manufacturing_area not in {None,manufacturing_area}: continue
        if x.parent_part_number.upper() not in visible_parts or x.child_part_number.upper() not in visible_parts: continue
        if variant and exact["configured"] and x.child_part_number.upper() not in set(exact["included_parts"]): continue
        ebom.append({"parent_part_number":x.parent_part_number,"parent_revision":x.parent_revision,"child_part_number":x.child_part_number,"child_revision":x.child_revision,"quantity":float(x.quantity or 0),"unit":x.unit,"position":x.position,"supplier_code":x.supplier_code,"source_document_id":x.source_document_id})
    mbom=[]
    for x in assurance_rows["mbom"]:
        if variant and x.variant_id not in {None,variant.id}: continue
        if not variant and x.variant_id is not None: continue
        if variant and exact["configured"] and x.child_part_number.upper() not in set(exact["included_parts"]): continue
        mbom.append(serialize_mbom(x))
    if not ebom and not mbom:
        return {"configured":False,"status":"NOT_CONFIGURED","summary":{"missing_in_mbom":0,"extra_in_mbom":0,"changed":0},"missing_in_mbom":[],"extra_in_mbom":[],"changed":[],"ebom_rows":0,"mbom_rows":0}
    if not mbom:
        return {"configured":False,"status":"NOT_CONFIGURED","summary":{"missing_in_mbom":len(ebom),"extra_in_mbom":0,"changed":0},"missing_in_mbom":ebom,"extra_in_mbom":[],"changed":[],"ebom_rows":len(ebom),"mbom_rows":0}
    le=_aggregate(ebom); rm=_aggregate(mbom)
    missing=[le[k] for k in sorted(set(le)-set(rm))]
    extra=[rm[k] for k in sorted(set(rm)-set(le))]
    changed=[]
    for k in sorted(set(le)&set(rm)):
        a,b=le[k],rm[k]; diffs={}
        for f in ("child_part_number","child_revision","quantity","unit","supplier_code"):
            if a.get(f)!=b.get(f): diffs[f]={"ebom":a.get(f),"mbom":b.get(f)}
        if diffs: changed.append({"key":k,"changes":diffs,"ebom":a,"mbom":b})
    status="ALIGNED" if not (missing or extra or changed) else "MISMATCH"
    return {"configured":True,"status":status,"summary":{"missing_in_mbom":len(missing),"extra_in_mbom":len(extra),"changed":len(changed)},"missing_in_mbom":missing,"extra_in_mbom":extra,"changed":changed,"ebom_rows":len(ebom),"mbom_rows":len(mbom)}


def effectivity_view(rows: list[ConfigurationEffectivity], variant: VehicleVariant | None) -> dict:
    filtered=[x for x in rows if x.status=="active" and (not variant or x.variant_id in {None,variant.id})]
    by_part=defaultdict(list)
    for x in filtered: by_part[x.part_number.upper()].append(serialize_effectivity(x))
    return {"configured":bool(filtered),"rules":[serialize_effectivity(x) for x in filtered],"parts_with_rules":len(by_part),"ambiguous_parts":sorted(p for p,v in by_part.items() if len(v)>1)}


def _ppap_ok(db: Session, project_code: str, part_number: str, revision: str | None, supplier_code: str | None, visible_document_ids: set[str], manufacturing_area: str | None, allowed_area_codes: set[str] | None) -> bool:
    for p in db.scalars(select(PPAPSubmission).where(PPAPSubmission.project_code==project_code, PPAPSubmission.part_number==part_number)).all():
        if not _area_ok(p.manufacturing_area,manufacturing_area,allowed_area_codes) or not _visible_evidence(p.evidence_document_ids,visible_document_ids): continue
        if p.status!="approved": continue
        if revision and p.revision and p.revision!=revision: continue
        if supplier_code and p.supplier_code and p.supplier_code!=supplier_code: continue
        return True
    return False


def cutin_readiness(db: Session, rows: list[ChangeCutIn], visible_document_ids: set[str], manufacturing_area: str | None, allowed_area_codes: set[str] | None) -> list[dict]:
    out=[]
    for x in rows:
        gaps=[]
        if not x.cut_in_at and not x.vin_from: gaps.append("cut_in_point_missing")
        if (x.old_stock_qty or 0)>0 and not x.old_stock_disposition: gaps.append("old_stock_disposition_missing")
        if not x.logistics_confirmed: gaps.append("logistics_cutover_not_confirmed")
        if not _ppap_ok(db,x.project_code,x.part_number,x.to_revision,None,visible_document_ids,manufacturing_area,allowed_area_codes): gaps.append("ppap_for_new_revision_not_approved")
        out.append({**serialize_cutin(x),"readiness":"READY" if not gaps else "BLOCKED","gaps":gaps})
    return out


def _aware_utc(value):
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _effectivity_applies(rule: ConfigurationEffectivity, built: AsBuiltConfiguration) -> bool:
    # Fail closed when a scoped rule cannot be proven to apply to the observed build.
    if rule.variant_id and built.variant_id != rule.variant_id:
        return False
    if rule.plant and (not built.plant or built.plant != rule.plant):
        return False
    if rule.supplier_code and (not built.supplier_code or built.supplier_code != rule.supplier_code):
        return False
    vin=(built.vehicle_identifier or "").strip()
    if rule.vin_from and (not vin or vin < rule.vin_from):
        return False
    if rule.vin_to and (not vin or vin > rule.vin_to):
        return False
    bt=_aware_utc(built.built_at)
    if rule.effective_from and (not bt or bt < _aware_utc(rule.effective_from)):
        return False
    if rule.effective_to and (not bt or bt > _aware_utc(rule.effective_to)):
        return False
    serial=(built.metadata_json or {}).get("serial_number")
    if rule.serial_from is not None and (serial is None or int(serial) < rule.serial_from):
        return False
    if rule.serial_to is not None and (serial is None or int(serial) > rule.serial_to):
        return False
    return True


def as_built_assurance(db: Session, rows: list[AsBuiltConfiguration], effectivity_rows: list[ConfigurationEffectivity], visible_document_ids: set[str]) -> dict:
    issues=[]; checked=0
    active_devs={d.id:d for d in db.scalars(select(EngineeringDeviation)).all() if d.status in {"approved","active"} and _visible_evidence(d.evidence_document_ids,visible_document_ids)}
    eff_by_part=defaultdict(list)
    for e in effectivity_rows:
        if e.status=="active": eff_by_part[e.part_number.upper()].append(e)
    for x in rows:
        candidate_rules=eff_by_part.get(x.part_number.upper(),[])
        if not candidate_rules:
            continue
        checked+=1
        rules=[r for r in candidate_rules if _effectivity_applies(r,x)]
        if not rules:
            issues.append({"vehicle_identifier":x.vehicle_identifier,"part_number":x.part_number,"built_revision":x.revision,"expected_revisions":[],"authorized_deviation":False,"deviation_code":None,"severity":"critical","type":"effectivity_unresolved","message":"No active effectivity rule can be proven for this vehicle/variant/plant/date scope"})
            continue
        allowed_revs={r.revision for r in rules if r.revision}
        if allowed_revs and x.revision not in allowed_revs:
            dev=active_devs.get(x.deviation_id) if x.deviation_id else None
            issues.append({"vehicle_identifier":x.vehicle_identifier,"part_number":x.part_number,"built_revision":x.revision,"expected_revisions":sorted(allowed_revs),"authorized_deviation":bool(dev),"deviation_code":dev.code if dev else None,"severity":"warning" if dev else "critical","type":"revision_mismatch","message":"AS-BUILT revision is outside the applicable released effectivity"})
    return {"configured":bool(rows),"checked":checked,"mismatches":issues,"status":"RED" if any(x["severity"]=="critical" for x in issues) else ("AMBER" if issues else ("GREEN" if rows else "NOT_CONFIGURED"))}


def _semantic_snapshot(snapshot: dict) -> dict:
    out=dict(snapshot or {})
    out.pop("captured_at",None)
    # v5.5 extends v2 release snapshots with configuration-authority domains.
    # Empty new domains must not make an unchanged legacy baseline look drifted.
    if out.get("schema") in {"mgc-release-baseline-v2","mgc-release-baseline-v3"}:
        out["schema"]="mgc-release-baseline-v2plus"
    for key in ("manufacturing_bom","configuration_effectivity","change_cutins","part_supersessions"):
        if not out.get(key):
            out.pop(key,None)
    return out


def release_drift(db: Session, project, visible_document_ids: set[str], visible_parts: set[str], allowed_area_codes: set[str], variant: VehicleVariant | None, manufacturing_area: str | None) -> dict:
    q=select(ReleaseBaseline).where(ReleaseBaseline.project_code==project.code).order_by(ReleaseBaseline.frozen_at.desc())
    bases=list(db.scalars(q).all())
    if variant: bases=[b for b in bases if b.variant_id==variant.id]
    bases=[b for b in bases if _area_ok(b.manufacturing_area,manufacturing_area,allowed_area_codes) and _visible_evidence(b.source_document_ids,visible_document_ids)]
    if not bases: return {"configured":False,"status":"NO_BASELINE","drift":False,"baseline":None}
    base=bases[0]
    current,_,warnings=build_release_snapshot(db,project,visible_document_ids,visible_parts,allowed_area_codes,variant.id if variant else None,manufacturing_area)
    baseline_fp=_hash(_semantic_snapshot(base.snapshot_json or {}))
    current_fp=_hash(_semantic_snapshot(current))
    return {"configured":True,"status":"DRIFT" if baseline_fp!=current_fp else "MATCH","drift":baseline_fp!=current_fp,"baseline":{"id":base.id,"code":base.code,"type":base.baseline_type,"frozen_at":_dt(base.frozen_at),"fingerprint":base.fingerprint},"current_snapshot_fingerprint":current_fp,"baseline_snapshot_fingerprint":baseline_fp,"warnings":warnings}


def _domain(status: str, blockers: list[dict], reviews: list[dict]) -> dict:
    return {"status":status,"blockers":blockers,"review":reviews,"score":0 if status=="RED" else 70 if status in {"AMBER","NOT_CONFIGURED"} else 100}


def buildability_check(db: Session, project, visible_document_ids: set[str], visible_parts: set[str], allowed_area_codes: set[str], variant: VehicleVariant | None, exact: dict, reconciliation: dict, assurance_rows: dict, manufacturing_area: str | None) -> dict:
    domains={}; blockers=[]; reviews=[]
    conf_block=[]; conf_rev=[]
    if not variant: conf_rev.append({"type":"variant_not_selected","message":"Select a vehicle variant for 100% configuration assurance"})
    elif not exact["configured"]: conf_rev.append({"type":"configuration_not_configured","message":"Variant applicability is not configured"})
    elif exact["unknown_parts"]: conf_block.append({"type":"unknown_applicability","count":len(exact["unknown_parts"]),"message":"UNKNOWN applicability is never treated as included"})
    domains["configuration"]=_domain("RED" if conf_block else ("AMBER" if conf_rev else "GREEN"),conf_block,conf_rev)

    eb=[]; er=[]
    if reconciliation["status"]=="MISMATCH": eb.append({"type":"ebom_mbom_mismatch","summary":reconciliation["summary"],"message":"EBOM and MBOM are not aligned"})
    elif reconciliation["status"]=="NOT_CONFIGURED": er.append({"type":"mbom_not_configured","message":"MBOM has not been imported/configured"})
    domains["product_structure"]=_domain("RED" if eb else ("AMBER" if er else "GREEN"),eb,er)

    parts=set(exact["included_parts"]) if variant and exact["configured"] else set(visible_parts)
    operations=[]
    for op in db.scalars(select(ProcessOperation)).all():
        if not op.part_number or op.part_number.upper() not in parts: continue
        station=db.get(ProcessStation,op.station_id); line=db.get(ManufacturingLine,station.line_id) if station else None
        if not line or line.project_code!=project.code or not _area_ok(line.manufacturing_area,manufacturing_area,allowed_area_codes): continue
        operations.append(op)
    proc_rev=[]
    if parts and not operations: proc_rev.append({"type":"process_not_linked","message":"No visible process operations are linked to the selected configuration"})
    wi_missing=[op for op in operations if not op.work_instruction_document_ids or not set(op.work_instruction_document_ids).issubset(visible_document_ids)]
    if wi_missing: proc_rev.append({"type":"work_instruction_missing_or_hidden","count":len(wi_missing),"message":"Some process operations do not have visible Work Instruction evidence"})
    domains["manufacturing"]=_domain("AMBER" if proc_rev else "GREEN",[],proc_rev)

    sup_block=[]
    mbom_for_variant=[x for x in assurance_rows["mbom"] if not variant or x.variant_id in {None,variant.id}]
    for x in mbom_for_variant:
        if x.supplier_code and not _ppap_ok(db,project.code,x.child_part_number,x.child_revision,x.supplier_code,visible_document_ids,manufacturing_area,allowed_area_codes):
            sup_block.append({"type":"ppap_missing","part_number":x.child_part_number,"revision":x.child_revision,"supplier_code":x.supplier_code,"message":"Approved PPAP not found for MBOM revision/supplier"})
    domains["supplier"]=_domain("RED" if sup_block else ("AMBER" if not mbom_for_variant else "GREEN"),sup_block,[] if mbom_for_variant else [{"type":"supplier_scope_unknown","message":"Supplier assurance requires MBOM/supplier data"}])

    cut=cutin_readiness(db,[x for x in assurance_rows["cutins"] if not variant or not x.variant_ids or variant.id in x.variant_ids],visible_document_ids,manufacturing_area,allowed_area_codes)
    cut_block=[{"type":"cutin_blocked","code":x["code"],"gaps":x["gaps"],"message":"Change cut-in is not ready"} for x in cut if x["readiness"]=="BLOCKED"]
    domains["change_cutin"]=_domain("RED" if cut_block else ("AMBER" if not cut else "GREEN"),cut_block,[] if cut else [{"type":"cutin_not_configured","message":"No cut-in record configured"}])

    for name,d in domains.items():
        blockers.extend({"domain":name,**x} for x in d["blockers"]); reviews.extend({"domain":name,**x} for x in d["review"])
    overall="RED" if blockers else ("AMBER" if reviews else "GREEN")
    return {"status":overall,"domains":domains,"blockers":blockers,"review_required":reviews,"human_release_approval_required":True,"advisory_only":True}


def release_package(db: Session, project, visible_document_ids: set[str], visible_parts: set[str], allowed_area_codes: set[str], variant: VehicleVariant | None, manufacturing_area: str | None, buildability: dict) -> dict:
    engineering_snapshot,candidate,warnings=build_release_snapshot(db,project,visible_document_ids,visible_parts,allowed_area_codes,variant.id if variant else None,manufacturing_area)
    rows=visible_assurance_rows(db,project.code,visible_document_ids,visible_parts,manufacturing_area,allowed_area_codes)
    exact=exact_variant_configuration(db,project.code,variant,visible_parts,visible_document_ids,manufacturing_area,allowed_area_codes)
    reconciliation=reconcile_ebom_mbom(db,project.code,visible_document_ids,visible_parts,rows,variant,exact,manufacturing_area)
    eff=effectivity_view(rows["effectivity"],variant)
    cut=cutin_readiness(db,[x for x in rows["cutins"] if not variant or not x.variant_ids or variant.id in x.variant_ids],visible_document_ids,manufacturing_area,allowed_area_codes)
    configuration_snapshot={
        "configuration":exact,
        "ebom_mbom":reconciliation,
        "effectivity":eff,
        "change_cutins":cut,
        "supersessions":supersession_chain(rows["supersessions"]),
        "buildability":buildability,
    }
    composite={"engineering":engineering_snapshot,"configuration_assurance":configuration_snapshot}
    docs=engineering_snapshot.get("documents",[])
    return {
        "schema":"mgc-configuration-release-package-v2","project_code":project.code,
        "variant":{"id":variant.id,"code":variant.code,"name":variant.name} if variant else None,
        "manufacturing_area":manufacturing_area,"fingerprint":_hash(composite),"snapshot":composite,
        "counts":{"documents":len(docs),"bom_items":len(engineering_snapshot.get("bom",[])),"manufacturing_bom_items":len(engineering_snapshot.get("manufacturing_bom",[])),"effectivity_rules":len(engineering_snapshot.get("configuration_effectivity",[])),"change_cutins":len(engineering_snapshot.get("change_cutins",[])),"requirements":len(engineering_snapshot.get("requirements",[])),"verifications":len(engineering_snapshot.get("verifications",[])),"ppap":len(engineering_snapshot.get("ppap",[]))},
        "buildability_status":buildability["status"],"release_candidate":bool(candidate and buildability["status"]=="GREEN"),
        "warnings":warnings + [x.get("message",x.get("type","review")) for x in buildability.get("blockers",[]) + buildability.get("review_required",[])],
        "immutable_when_frozen_via_release_baseline":True,"human_release_approval_required":True,
        "source_authority":{"ebom":"PLM/PDM","mbom":"ERP/Manufacturing","as_built":"MES/import"},
    }


def supersession_chain(rows: list[PartSupersession]) -> list[dict]:
    active=[x for x in rows if x.status=="active"]
    return [serialize_supersession(x) for x in active]


def configuration_release_assurance_workspace(db: Session, project, visible_document_ids: set[str], visible_part_numbers: set[str], manufacturing_area: str | None=None, allowed_area_codes: set[str] | None=None, variant_id: str | None=None, vehicle_identifier: str | None=None) -> dict:
    visible_parts={p.upper() for p in visible_part_numbers}
    allowed=allowed_area_codes or set()
    variant=_variant(db,project.code,variant_id,visible_document_ids,manufacturing_area,allowed)
    rows=visible_assurance_rows(db,project.code,visible_document_ids,visible_parts,manufacturing_area,allowed)
    exact=exact_variant_configuration(db,project.code,variant,visible_parts,visible_document_ids,manufacturing_area,allowed)
    rec=reconcile_ebom_mbom(db,project.code,visible_document_ids,visible_parts,rows,variant,exact,manufacturing_area)
    eff=effectivity_view(rows["effectivity"],variant)
    cut=cutin_readiness(db,[x for x in rows["cutins"] if not variant or not x.variant_ids or variant.id in x.variant_ids],visible_document_ids,manufacturing_area,allowed)
    built_rows=[x for x in rows["as_built"] if (not variant or x.variant_id in {None,variant.id}) and (not vehicle_identifier or x.vehicle_identifier==vehicle_identifier)]
    built=as_built_assurance(db,built_rows,rows["effectivity"],visible_document_ids)
    build=buildability_check(db,project,visible_document_ids,visible_parts,allowed,variant,exact,rec,rows,manufacturing_area)
    drift=release_drift(db,project,visible_document_ids,visible_parts,allowed,variant,manufacturing_area)
    package=release_package(db,project,visible_document_ids,visible_parts,allowed,variant,manufacturing_area,build)
    confidence_domains={k:v["score"] for k,v in build["domains"].items()}
    confidence_domains.update({"effectivity":100 if eff["configured"] and not eff["ambiguous_parts"] else 70 if eff["configured"] else 50,"as_built":100 if built["status"]=="GREEN" else 70 if built["status"] in {"AMBER","NOT_CONFIGURED"} else 0,"release_drift":100 if drift["status"]=="MATCH" else 70 if drift["status"]=="NO_BASELINE" else 0})
    overall=round(sum(confidence_domains.values())/max(len(confidence_domains),1),1)
    matrix=variant_plant_matrix(db,project,visible_document_ids,visible_parts,allowed,manufacturing_area)
    base_payload={
        "version":"5.5.0","project_code":project.code,"manufacturing_area":manufacturing_area,
        "variant":exact["variant"],"configuration":exact,"ebom_mbom":rec,"effectivity":eff,
        "change_cutins":cut,"as_built":built,"release_drift":drift,"buildability":build,
        "release_package":{k:v for k,v in package.items() if k!="snapshot"},
        "supersessions":supersession_chain(rows["supersessions"]),
        "confidence":{"overall":overall,"band":"GREEN" if overall>=90 and build["status"]=="GREEN" else "RED" if build["status"]=="RED" else "AMBER","domains":confidence_domains},
        "counts":{"mbom":len(rows["mbom"]),"effectivity":len(rows["effectivity"]),"cutins":len(rows["cutins"]),"as_built":len(built_rows),"supersessions":len(rows["supersessions"])},
        "governance":{"advisory_only":True,"plm_pdm_authoritative_for_ebom":True,"erp_manufacturing_authoritative_for_mbom":True,"mes_authoritative_for_as_built":True,"no_automatic_release":True,"no_automatic_stock_transaction":True,"unknown_is_not_included":True},
    }
    base_payload["variant_plant_matrix"]=matrix
    base_payload["system_consistency"]=cross_system_consistency(base_payload)
    base_payload["manufacturing_handover"]={"status":build["status"],"blockers":build["blockers"],"review_required":build["review_required"],"human_approval_required":True}
    base_payload["as_designed_planned_built"]={"as_designed":{"source":"PLM/PDM / EBOM","rows":rec.get("ebom_rows",0)},"as_planned":{"source":"ERP/Manufacturing / MBOM","rows":rec.get("mbom_rows",0),"status":rec.get("status")},"as_built":{"source":"MES/import","records":built.get("checked",0),"status":built.get("status")}}
    return base_payload


def cross_system_consistency(workspace: dict) -> dict:
    rec=workspace.get("ebom_mbom",{})
    built=workspace.get("as_built",{})
    issues=[]
    if rec.get("status")=="MISMATCH":
        issues.append({"systems":["PLM/PDM (EBOM)","ERP/Manufacturing (MBOM)"],"type":"product_structure_drift","severity":"critical","summary":rec.get("summary",{})})
    elif rec.get("status")=="NOT_CONFIGURED":
        issues.append({"systems":["PLM/PDM (EBOM)","ERP/Manufacturing (MBOM)"],"type":"mbom_not_configured","severity":"review"})
    for x in built.get("mismatches",[]):
        issues.append({"systems":["Released configuration","MES/AS-BUILT"],"type":"as_built_revision_drift","severity":x.get("severity","critical"),"vehicle_identifier":x.get("vehicle_identifier"),"part_number":x.get("part_number"),"built_revision":x.get("built_revision"),"expected_revisions":x.get("expected_revisions"),"authorized_deviation":x.get("authorized_deviation")})
    return {"status":"RED" if any(x["severity"]=="critical" for x in issues) else ("AMBER" if issues else "GREEN"),"issues":issues,"read_only":True,"no_automatic_source_system_write":True}


def variant_plant_matrix(db: Session, project, visible_document_ids: set[str], visible_parts: set[str], allowed_area_codes: set[str], manufacturing_area: str | None=None) -> list[dict]:
    rows=visible_assurance_rows(db,project.code,visible_document_ids,visible_parts,manufacturing_area,allowed_area_codes)
    variants=[]
    for v in db.scalars(select(VehicleVariant).where(VehicleVariant.project_code==project.code).order_by(VehicleVariant.code)).all():
        if v.status not in {"active","released"}: continue
        if not _area_ok(v.manufacturing_area,manufacturing_area,allowed_area_codes) or not _visible_evidence(v.evidence_document_ids,visible_document_ids): continue
        variants.append(v)
    plants=sorted({x.plant for x in rows["effectivity"]+rows["cutins"]+rows["as_built"] if getattr(x,"plant",None)}) or [None]
    matrix=[]
    for v in variants:
        exact=exact_variant_configuration(db,project.code,v,visible_parts,visible_document_ids,manufacturing_area,allowed_area_codes)
        rec=reconcile_ebom_mbom(db,project.code,visible_document_ids,visible_parts,rows,v,exact,manufacturing_area)
        for plant in plants:
            eff=[x for x in rows["effectivity"] if x.status=="active" and x.variant_id in {None,v.id} and (not plant or x.plant in {None,plant})]
            cuts=[x for x in rows["cutins"] if (not x.variant_ids or v.id in x.variant_ids) and (not plant or x.plant in {None,plant})]
            gaps=[]
            if exact["unknown_parts"]: gaps.append("unknown_applicability")
            if rec["status"]=="MISMATCH": gaps.append("ebom_mbom_mismatch")
            if rec["status"]=="NOT_CONFIGURED": gaps.append("mbom_not_configured")
            if not eff: gaps.append("effectivity_not_configured")
            if any(x["readiness"]=="BLOCKED" for x in cutin_readiness(db,cuts,visible_document_ids,manufacturing_area,allowed_area_codes)): gaps.append("cutin_blocked")
            band="RED" if any(x in {"unknown_applicability","ebom_mbom_mismatch","cutin_blocked"} for x in gaps) else ("AMBER" if gaps else "READY")
            matrix.append({"variant_id":v.id,"variant_code":v.code,"variant_name":v.name,"plant":plant or "ALL/UNSPECIFIED","status":band,"gaps":gaps})
    return matrix


def configuration_assurance_answer(workspace: dict, query: str) -> dict:
    q=(query or "").strip()
    b=workspace.get("buildability",{})
    rec=workspace.get("ebom_mbom",{})
    drift=workspace.get("release_drift",{})
    conf=workspace.get("confidence",{})
    blockers=b.get("blockers",[]); reviews=b.get("review_required",[])
    lines=[f"Configuration assurance: {b.get('status','UNKNOWN')}. Confidence: {conf.get('overall','—')}% ({conf.get('band','UNKNOWN')})."]
    if blockers:
        lines.append(f"Blocking gaps: {len(blockers)}.")
        for x in blockers[:6]: lines.append(f"- {x.get('domain')}: {x.get('message') or x.get('type')}")
    elif reviews:
        lines.append(f"Review items: {len(reviews)}.")
        for x in reviews[:6]: lines.append(f"- {x.get('domain')}: {x.get('message') or x.get('type')}")
    else:
        lines.append("No deterministic blocking/review gaps were found in the currently visible evidence.")
    lines.append(f"EBOM↔MBOM: {rec.get('status','UNKNOWN')}; Release drift: {drift.get('status','UNKNOWN')}.")
    return {"query":q,"answer":"\n".join(lines),"deterministic":True,"llm_required":False,"advisory_only":True,"blockers":blockers,"review_required":reviews,"evidence_summary":{"release_package_fingerprint":workspace.get("release_package",{}).get("fingerprint"),"variant":workspace.get("variant")}}
