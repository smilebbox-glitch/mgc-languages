from __future__ import annotations

import math
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from typing import Iterable

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import (
    BuildGenealogyItem, ControlPlanItem, FieldQualityClaim, PFMEAItem,
    ProcessAsset, ProcessCapabilityRecord, ProcessDefect, ProcessOperation,
    ProcessStation, ManufacturingLine, SeriesContainmentCase,
    SeriesQualityObservation, VehicleBuild,
)


def _iso(v):
    return v.isoformat() if v else None


def _aware(v: datetime | None) -> datetime | None:
    if not v:
        return None
    return v if v.tzinfo else v.replace(tzinfo=timezone.utc)


def _evidence_ok(ids: Iterable[str] | None, visible_document_ids: set[str]) -> bool:
    values=set(ids or [])
    return not values or values.issubset(visible_document_ids)


def _area_ok(area: str | None, requested: str | None, allowed: set[str] | None) -> bool:
    if area and allowed is not None and area not in allowed:
        return False
    return not requested or area in {None, requested}


def _rate(defects: int | float, inspected: int | float) -> float | None:
    return round(float(defects) * 100.0 / float(inspected), 4) if inspected else None


def _band_from_cpk(value: float | None) -> str:
    if value is None:
        return "UNKNOWN"
    if value < 1.0:
        return "RED"
    if value < 1.33:
        return "AMBER"
    return "GREEN"


def serialize_series_observation(x: SeriesQualityObservation) -> dict:
    return {
        "id":x.id,"manufacturing_area":x.manufacturing_area,"plant":x.plant,"line_id":x.line_id,
        "station_id":x.station_id,"operation_id":x.operation_id,"shift_code":x.shift_code,"variant_id":x.variant_id,
        "part_number":x.part_number,"revision":x.revision,"supplier_code":x.supplier_code,"supplier_lot":x.supplier_lot,
        "defect_code":x.defect_code,"characteristic":x.characteristic,"produced_quantity":int(x.produced_quantity or 0),
        "inspected_quantity":int(x.inspected_quantity or 0),"defect_quantity":int(x.defect_quantity or 0),
        "detected_in_process_quantity":int(x.detected_in_process_quantity or 0),"escaped_quantity":int(x.escaped_quantity or 0),
        "defect_rate_pct":_rate(x.defect_quantity or 0,x.inspected_quantity or x.produced_quantity or 0),
        "scrap_cost":float(x.scrap_cost or 0),"rework_cost":float(x.rework_cost or 0),"containment_cost":float(x.containment_cost or 0),
        "warranty_cost_estimate":float(x.warranty_cost_estimate or 0),"currency":x.currency,"observed_at":_iso(x.observed_at),
        "period_key":x.period_key,"source_system":x.source_system,"evidence_document_ids":x.evidence_document_ids or [],"metadata":x.metadata_json or {},
    }


def serialize_capability(x: ProcessCapabilityRecord) -> dict:
    return {
        "id":x.id,"manufacturing_area":x.manufacturing_area,"plant":x.plant,"line_id":x.line_id,"station_id":x.station_id,
        "operation_id":x.operation_id,"asset_id":x.asset_id,"part_number":x.part_number,"supplier_code":x.supplier_code,
        "characteristic":x.characteristic,"unit":x.unit,"sample_size":int(x.sample_size or 0),"mean":x.mean_value,"sigma":x.sigma_value,
        "lsl":x.lower_spec_limit,"usl":x.upper_spec_limit,"cp":x.cp,"cpk":x.cpk,"pp":x.pp,"ppk":x.ppk,
        "status":_band_from_cpk(x.cpk if x.cpk is not None else x.ppk),"measured_at":_iso(x.measured_at),
        "source_system":x.source_system,"evidence_document_ids":x.evidence_document_ids or [],"metadata":x.metadata_json or {},
    }


def serialize_containment(x: SeriesContainmentCase) -> dict:
    suspect=len(x.suspect_vehicle_identifiers or [])
    inspected=int(x.inspected_quantity or 0); defects=int(x.defect_quantity or 0)
    return {
        "id":x.id,"code":x.code,"title":x.title,"manufacturing_area":x.manufacturing_area,"part_number":x.part_number,
        "defect_code":x.defect_code,"supplier_code":x.supplier_code,"supplier_lot":x.supplier_lot,"status":x.status,
        "suspect_criteria":x.suspect_criteria_json or {},"suspect_vehicle_identifiers":x.suspect_vehicle_identifiers or [],
        "suspect_quantity":suspect,"inspected_quantity":inspected,"defect_quantity":defects,
        "remaining_quantity":max(suspect-inspected,0),"inspection_progress_pct":round(inspected*100/suspect,1) if suspect else None,
        "defect_rate_pct":_rate(defects,inspected),"actions":x.actions_json or [],"linked_8d_id":x.linked_8d_id,
        "opened_at":_iso(x.opened_at),"closed_at":_iso(x.closed_at),"evidence_document_ids":x.evidence_document_ids or [],"notes":x.notes,
        "human_status_control_required":True,
    }


def serialize_field_claim(x: FieldQualityClaim) -> dict:
    return {
        "id":x.id,"claim_reference":x.claim_reference,"vehicle_identifier":x.vehicle_identifier,"manufacturing_area":x.manufacturing_area,
        "part_number":x.part_number,"revision":x.revision,"supplier_code":x.supplier_code,"failure_mode":x.failure_mode,"severity":x.severity,
        "status":x.status,"claim_at":_iso(x.claim_at),"cost_estimate":float(x.cost_estimate or 0),"currency":x.currency,
        "linked_8d_id":x.linked_8d_id,"evidence_document_ids":x.evidence_document_ids or [],"metadata":x.metadata_json or {},
    }


def visible_series_rows(db: Session, project_code: str, visible_document_ids: set[str], visible_part_numbers: set[str], manufacturing_area: str | None=None, allowed_area_codes: set[str] | None=None) -> dict:
    parts={x.upper() for x in visible_part_numbers if x}
    obs=[x for x in db.scalars(select(SeriesQualityObservation).where(SeriesQualityObservation.project_code==project_code)).all()
         if _area_ok(x.manufacturing_area,manufacturing_area,allowed_area_codes)
         and (not x.part_number or x.part_number.upper() in parts) and _evidence_ok(x.evidence_document_ids,visible_document_ids)]
    caps=[x for x in db.scalars(select(ProcessCapabilityRecord).where(ProcessCapabilityRecord.project_code==project_code)).all()
          if _area_ok(x.manufacturing_area,manufacturing_area,allowed_area_codes)
          and (not x.part_number or x.part_number.upper() in parts) and _evidence_ok(x.evidence_document_ids,visible_document_ids)]
    contain=[x for x in db.scalars(select(SeriesContainmentCase).where(SeriesContainmentCase.project_code==project_code)).all()
             if _area_ok(x.manufacturing_area,manufacturing_area,allowed_area_codes)
             and (not x.part_number or x.part_number.upper() in parts) and _evidence_ok(x.evidence_document_ids,visible_document_ids)]
    claims=[x for x in db.scalars(select(FieldQualityClaim).where(FieldQualityClaim.project_code==project_code)).all()
            if _area_ok(x.manufacturing_area,manufacturing_area,allowed_area_codes)
            and (not x.part_number or x.part_number.upper() in parts) and _evidence_ok(x.evidence_document_ids,visible_document_ids)]
    defects=[x for x in db.scalars(select(ProcessDefect).where(ProcessDefect.project_code==project_code)).all()
             if _area_ok(x.manufacturing_area,manufacturing_area,allowed_area_codes)
             and (not x.part_number or x.part_number.upper() in parts) and _evidence_ok(x.evidence_document_ids,visible_document_ids)]
    pfmea=[x for x in db.scalars(select(PFMEAItem).where(PFMEAItem.project_code==project_code)).all()
           if _area_ok(x.manufacturing_area,manufacturing_area,allowed_area_codes)
           and (not x.part_number or x.part_number.upper() in parts) and _evidence_ok(x.evidence_document_ids,visible_document_ids)]
    cp=[x for x in db.scalars(select(ControlPlanItem).where(ControlPlanItem.project_code==project_code)).all()
        if _area_ok(x.manufacturing_area,manufacturing_area,allowed_area_codes)
        and (not x.part_number or x.part_number.upper() in parts) and _evidence_ok(x.evidence_document_ids,visible_document_ids)]
    return {"observations":obs,"capability":caps,"containment":contain,"field_claims":claims,"defects":defects,"pfmea":pfmea,"control_plan":cp}


def _latest_capability(caps: list[ProcessCapabilityRecord]) -> list[dict]:
    groups=defaultdict(list)
    for x in caps:
        groups[(x.characteristic,x.part_number,x.station_id,x.operation_id)].append(x)
    out=[]
    for key,rows in groups.items():
        rows.sort(key=lambda x:_aware(x.measured_at) or datetime.min.replace(tzinfo=timezone.utc))
        latest=rows[-1]; payload=serialize_capability(latest)
        if len(rows)>1:
            prev=rows[-2]
            a=latest.cpk if latest.cpk is not None else latest.ppk
            b=prev.cpk if prev.cpk is not None else prev.ppk
            payload["previous_cpk"]=b
            payload["delta_cpk"]=round(a-b,3) if a is not None and b is not None else None
            payload["trend"]="DEGRADING" if a is not None and b is not None and a < b-0.1 else ("IMPROVING" if a is not None and b is not None and a>b+0.1 else "STABLE")
        else:
            payload.update({"previous_cpk":None,"delta_cpk":None,"trend":"UNKNOWN"})
        out.append(payload)
    return sorted(out,key=lambda x:((0 if x["status"]=="RED" else 1 if x["status"]=="AMBER" else 2),x["characteristic"]))


def _change_points(obs: list[SeriesQualityObservation]) -> list[dict]:
    groups=defaultdict(list)
    for x in obs:
        if not (x.defect_code or x.characteristic):
            continue
        groups[(x.defect_code or x.characteristic,x.part_number)].append(x)
    out=[]
    for (key,part),rows in groups.items():
        rows=sorted(rows,key=lambda x:_aware(x.observed_at) or datetime.min.replace(tzinfo=timezone.utc))
        if len(rows)<4:
            continue
        split=max(2,len(rows)//2); base=rows[:split]; recent=rows[split:]
        bi=sum(int(x.inspected_quantity or x.produced_quantity or 0) for x in base); bd=sum(int(x.defect_quantity or 0) for x in base)
        ri=sum(int(x.inspected_quantity or x.produced_quantity or 0) for x in recent); rd=sum(int(x.defect_quantity or 0) for x in recent)
        br=(bd/bi) if bi else 0.0; rr=(rd/ri) if ri else 0.0
        ratio=(rr/br) if br>0 else (math.inf if rr>0 else 1.0)
        if rd<3 or rr<0.005 or not (ratio>=2.0):
            continue
        def dominant(items,field):
            vals=[getattr(x,field) for x in items if getattr(x,field)]
            return Counter(vals).most_common(1)[0][0] if vals else None
        associations=[]
        for field,label in [("supplier_lot","supplier_lot"),("revision","part_revision"),("station_id","station"),("shift_code","shift")]:
            before,after=dominant(base,field),dominant(recent,field)
            if before!=after and after:
                associations.append({"type":label,"before":before,"after":after})
        out.append({"signal_key":key,"part_number":part,"change_point_at":_iso(recent[0].observed_at),
                    "baseline_rate_pct":round(br*100,4),"recent_rate_pct":round(rr*100,4),
                    "rate_ratio":None if math.isinf(ratio) else round(ratio,2),"baseline_defects":bd,"recent_defects":rd,
                    "associations":associations,"method":"two_window_rate_ratio","correlation_only":True,"causal_claim":False})
    return sorted(out,key=lambda x:(x["recent_rate_pct"],x["recent_defects"]),reverse=True)


def _supplier_lot_signals(obs: list[SeriesQualityObservation]) -> list[dict]:
    groups=defaultdict(list)
    by_supplier_part=defaultdict(list)
    for x in obs:
        if x.supplier_code and x.supplier_lot and x.part_number:
            groups[(x.part_number,x.supplier_code,x.supplier_lot)].append(x)
            by_supplier_part[(x.part_number,x.supplier_code)].append(x)
    out=[]
    for (part,supplier,lot),rows in groups.items():
        inspected=sum(int(x.inspected_quantity or x.produced_quantity or 0) for x in rows); defects=sum(int(x.defect_quantity or 0) for x in rows)
        rate=defects/inspected if inspected else 0
        other=[x for x in by_supplier_part[(part,supplier)] if x.supplier_lot!=lot]
        oi=sum(int(x.inspected_quantity or x.produced_quantity or 0) for x in other); od=sum(int(x.defect_quantity or 0) for x in other)
        baseline=od/oi if oi else 0
        ratio=rate/baseline if baseline>0 else (math.inf if rate>0 else 1)
        if defects>=3 and rate>=0.005 and (ratio>=2.0 or (not other and rate>=0.01)):
            out.append({"part_number":part,"supplier_code":supplier,"supplier_lot":lot,"inspected":inspected,"defects":defects,
                        "defect_rate_pct":round(rate*100,4),"baseline_rate_pct":round(baseline*100,4) if other else None,
                        "rate_ratio":None if math.isinf(ratio) else round(ratio,2),"signal":"QUALITY_SIGNAL","correlation_only":True,"causal_claim":False})
    return sorted(out,key=lambda x:(x["defect_rate_pct"],x["defects"]),reverse=True)


def _dimension_patterns(obs: list[SeriesQualityObservation], field: str) -> list[dict]:
    total_i=sum(int(x.inspected_quantity or x.produced_quantity or 0) for x in obs); total_d=sum(int(x.defect_quantity or 0) for x in obs)
    baseline=total_d/total_i if total_i else 0
    groups=defaultdict(lambda:[0,0])
    for x in obs:
        value=getattr(x,field)
        if not value: continue
        groups[value][0]+=int(x.inspected_quantity or x.produced_quantity or 0); groups[value][1]+=int(x.defect_quantity or 0)
    out=[]
    for key,(ins,defs) in groups.items():
        rate=defs/ins if ins else 0; ratio=rate/baseline if baseline else (math.inf if rate else 1)
        if defs>=3 and rate>=0.005 and ratio>=1.8:
            out.append({"dimension":field,"value":key,"inspected":ins,"defects":defs,"defect_rate_pct":round(rate*100,4),
                        "overall_rate_pct":round(baseline*100,4),"rate_ratio":None if math.isinf(ratio) else round(ratio,2),
                        "investigation_signal":True,"causal_claim":False})
    return sorted(out,key=lambda x:x["defect_rate_pct"],reverse=True)


def _tokens(text: str | None) -> set[str]:
    if not text: return set()
    return {x for x in re.findall(r"[a-zа-я0-9]+",text.lower()) if len(x)>=3}


def _pfmea_control_defect_loop(pfmea: list[PFMEAItem], cp: list[ControlPlanItem], defects: list[ProcessDefect], obs: list[SeriesQualityObservation]) -> list[dict]:
    out=[]
    for p in pfmea:
        pt=_tokens(p.failure_mode)
        matched_defects=[d for d in defects if (not p.part_number or d.part_number==p.part_number) and (not p.process_operation_id or d.operation_id==p.process_operation_id) and (pt & _tokens((d.defect_code or '')+' '+d.title))]
        matched_obs=[o for o in obs if (not p.part_number or o.part_number==p.part_number) and (not p.process_operation_id or o.operation_id==p.process_operation_id) and (pt & _tokens((o.defect_code or '')+' '+(o.characteristic or '')))]
        if not matched_defects and not matched_obs: continue
        controls=[c for c in cp if (not p.part_number or c.part_number==p.part_number) and (not p.process_operation_id or c.process_operation_id==p.process_operation_id)]
        actual_defects=sum(int(d.quantity or 1) for d in matched_defects)+sum(int(o.defect_quantity or 0) for o in matched_obs)
        inspected=sum(int(o.inspected_quantity or o.produced_quantity or 0) for o in matched_obs)
        actual_rate=_rate(sum(int(o.defect_quantity or 0) for o in matched_obs),inspected)
        review=(not controls) or (int(p.occurrence or 1)<=2 and actual_defects>=5) or (actual_rate is not None and actual_rate>=1.0 and int(p.occurrence or 1)<=3)
        out.append({"pfmea_id":p.id,"failure_mode":p.failure_mode,"part_number":p.part_number,"pfmea_occurrence":p.occurrence,
                    "actual_defect_quantity":actual_defects,"actual_defect_rate_pct":actual_rate,"control_plan_items":len(controls),
                    "control_plan_ids":[c.id for c in controls],"review_required":review,
                    "reason":"observed_series_data_exceeds_low_occurrence_assumption" if review and controls else ("control_plan_link_missing" if not controls else "monitor"),
                    "human_pfmea_update_required":True})
    return sorted(out,key=lambda x:(x["review_required"],x["actual_defect_quantity"]),reverse=True)


def _control_effectiveness(obs: list[SeriesQualityObservation]) -> dict:
    detected=sum(int(x.detected_in_process_quantity or 0) for x in obs); escaped=sum(int(x.escaped_quantity or 0) for x in obs)
    known=detected+escaped
    return {"detected_in_process":detected,"escaped_downstream":escaped,"known_detection_outcomes":known,
            "detection_effectiveness_pct":round(detected*100/known,2) if known else None,
            "escape_rate_pct":round(escaped*100/known,2) if known else None}


def _asset_signals(db: Session, project_code: str, caps: list[ProcessCapabilityRecord], defects: list[ProcessDefect], allowed: set[str] | None, requested: str | None) -> list[dict]:
    lines={x.id:x for x in db.scalars(select(ManufacturingLine).where(ManufacturingLine.project_code==project_code)).all()}
    stations={x.id:x for x in db.scalars(select(ProcessStation)).all() if x.line_id in lines}
    ops={x.id:x for x in db.scalars(select(ProcessOperation)).all() if x.station_id in stations}
    assets=[x for x in db.scalars(select(ProcessAsset)).all() if x.operation_id in ops and _area_ok(lines[stations[ops[x.operation_id].station_id].line_id].manufacturing_area,requested,allowed)]
    caps_by_asset=defaultdict(list)
    for c in caps:
        if c.asset_id: caps_by_asset[c.asset_id].append(c)
    defects_by_op=Counter(d.operation_id for d in defects if d.operation_id)
    now=datetime.now(timezone.utc); out=[]
    for a in assets:
        cal=_aware(a.calibration_due_at); maint=_aware(a.maintenance_due_at)
        rows=sorted(caps_by_asset.get(a.id,[]),key=lambda x:_aware(x.measured_at) or datetime.min.replace(tzinfo=timezone.utc))
        latest=rows[-1] if rows else None; samples_after=sum(int(x.sample_size or 0) for x in rows if cal and _aware(x.measured_at) and _aware(x.measured_at)>cal)
        latest_cpk=(latest.cpk if latest and latest.cpk is not None else latest.ppk if latest else None)
        reasons=[]
        if cal and cal<now: reasons.append("calibration_expired")
        if maint and maint<now: reasons.append("maintenance_overdue")
        if latest_cpk is not None and latest_cpk<1.0: reasons.append("capability_below_1_0")
        if defects_by_op.get(a.operation_id,0)>=3: reasons.append("related_defects_present")
        if reasons:
            out.append({"asset_id":a.id,"code":a.code,"name":a.name,"asset_type":a.asset_type,"operation_id":a.operation_id,
                        "calibration_due_at":_iso(a.calibration_due_at),"maintenance_due_at":_iso(a.maintenance_due_at),"latest_cpk":latest_cpk,
                        "samples_after_calibration_expiry":samples_after,"related_defect_records":defects_by_op.get(a.operation_id,0),
                        "signal":"REVIEW_REQUIRED","reasons":reasons,"machine_control":False})
    return sorted(out,key=lambda x:len(x["reasons"]),reverse=True)


def suspect_population(db: Session, project_code: str, visible_document_ids: set[str], visible_part_numbers: set[str], allowed_area_codes: set[str] | None, criteria: dict, manufacturing_area: str | None=None, max_results: int=5000) -> dict:
    parts={x.upper() for x in visible_part_numbers if x}
    builds=[b for b in db.scalars(select(VehicleBuild).where(VehicleBuild.project_code==project_code)).all()
            if _area_ok(b.manufacturing_area,manufacturing_area,allowed_area_codes) and _evidence_ok(b.evidence_document_ids,visible_document_ids)]
    bmap={b.id:b for b in builds}; rows=[]
    start=_aware(criteria.get("built_from")) if isinstance(criteria.get("built_from"),datetime) else None
    end=_aware(criteria.get("built_to")) if isinstance(criteria.get("built_to"),datetime) else None
    pn=(criteria.get("part_number") or "").upper() or None
    for g in db.scalars(select(BuildGenealogyItem)).all():
        b=bmap.get(g.build_id)
        if not b or not _evidence_ok(g.evidence_document_ids,visible_document_ids) or g.part_number.upper() not in parts: continue
        if pn and g.part_number.upper()!=pn: continue
        if criteria.get("revision") and g.revision!=criteria["revision"]: continue
        if criteria.get("supplier_code") and g.supplier_code!=criteria["supplier_code"]: continue
        if criteria.get("supplier_lot") and g.lot_number!=criteria["supplier_lot"]: continue
        if criteria.get("plant") and b.plant!=criteria["plant"]: continue
        if criteria.get("variant_id") and b.variant_id!=criteria["variant_id"]: continue
        bt=_aware(b.completed_at or b.planned_at)
        if start and (not bt or bt<start): continue
        if end and (not bt or bt>end): continue
        rows.append({"vehicle_identifier":b.vehicle_identifier,"build_id":b.id,"build_code":b.code,"variant_id":b.variant_id,"plant":b.plant,
                     "built_at":_iso(b.completed_at or b.planned_at),"part_number":g.part_number,"revision":g.revision,"supplier_code":g.supplier_code,"supplier_lot":g.lot_number})
    uniq={x["vehicle_identifier"]:x for x in rows}
    values=list(uniq.values())[:max_results]
    return {"criteria":{k:(_iso(v) if isinstance(v,datetime) else v) for k,v in criteria.items() if v not in (None,"")},"suspect_vehicle_count":len(uniq),"returned":len(values),"vehicles":values,"truncated":len(uniq)>max_results,"read_only":True}


def _copq(obs: list[SeriesQualityObservation], claims: list[FieldQualityClaim]) -> dict:
    by_currency=defaultdict(lambda:{"scrap":0.0,"rework":0.0,"containment":0.0,"warranty":0.0})
    for x in obs:
        c=x.currency or "RUB"; d=by_currency[c]; d["scrap"]+=float(x.scrap_cost or 0);d["rework"]+=float(x.rework_cost or 0);d["containment"]+=float(x.containment_cost or 0);d["warranty"]+=float(x.warranty_cost_estimate or 0)
    for x in claims:
        by_currency[x.currency or "RUB"]["warranty"]+=float(x.cost_estimate or 0)
    values=[]
    for c,d in by_currency.items():
        values.append({"currency":c,**{k:round(v,2) for k,v in d.items()},"total":round(sum(d.values()),2)})
    return {"advisory_only":True,"erp_finance_system_of_record":True,"by_currency":sorted(values,key=lambda x:x["total"],reverse=True)}


def _field_clusters(claims: list[FieldQualityClaim]) -> list[dict]:
    groups=defaultdict(lambda:{"claims":0,"vehicles":set(),"cost":0.0,"currencies":Counter()})
    for x in claims:
        key=(x.failure_mode,x.part_number,x.supplier_code)
        g=groups[key];g["claims"]+=1;g["cost"]+=float(x.cost_estimate or 0);g["currencies"][x.currency or "RUB"]+=1
        if x.vehicle_identifier:g["vehicles"].add(x.vehicle_identifier)
    out=[]
    for (failure,part,supplier),g in groups.items():
        if g["claims"]<2: continue
        out.append({"failure_mode":failure,"part_number":part,"supplier_code":supplier,"claims":g["claims"],"vehicles":len(g["vehicles"]),"cost_estimate":round(g["cost"],2),"currency":g["currencies"].most_common(1)[0][0]})
    return sorted(out,key=lambda x:x["claims"],reverse=True)


def series_quality_workspace(db: Session, project_code: str, visible_document_ids: set[str], visible_part_numbers: set[str], manufacturing_area: str | None=None, allowed_area_codes: set[str] | None=None) -> dict:
    rows=visible_series_rows(db,project_code,visible_document_ids,visible_part_numbers,manufacturing_area,allowed_area_codes)
    obs=rows["observations"]; caps=rows["capability"]; claims=rows["field_claims"]
    inspected=sum(int(x.inspected_quantity or x.produced_quantity or 0) for x in obs); defects=sum(int(x.defect_quantity or 0) for x in obs); produced=sum(int(x.produced_quantity or 0) for x in obs)
    change_points=_change_points(obs); supplier_lots=_supplier_lot_signals(obs); capability=_latest_capability(caps)
    red_cap=sum(1 for x in capability if x["status"]=="RED"); amber_cap=sum(1 for x in capability if x["status"]=="AMBER")
    rate=_rate(defects,inspected); quality_band="RED" if change_points or (rate is not None and rate>=2.0) else ("AMBER" if (rate is not None and rate>=0.5) else ("GREEN" if inspected else "UNKNOWN"))
    capability_band="RED" if red_cap else ("AMBER" if amber_cap else ("GREEN" if capability else "UNKNOWN"))
    supplier_band="RED" if any((x["rate_ratio"] or 999)>=5 for x in supplier_lots) else ("AMBER" if supplier_lots else "GREEN" if obs else "UNKNOWN")
    contain=[serialize_containment(x) for x in rows["containment"]]
    open_contain=sum(1 for x in contain if x["status"] not in {"closed","cancelled"})
    pfmea=_pfmea_control_defect_loop(rows["pfmea"],rows["control_plan"],rows["defects"],obs)
    control=_control_effectiveness(obs)
    assets=_asset_signals(db,project_code,caps,rows["defects"],allowed_area_codes,manufacturing_area)
    shifts=_dimension_patterns(obs,"shift_code"); stations=_dimension_patterns(obs,"station_id")
    field=[serialize_field_claim(x) for x in sorted(claims,key=lambda x:_aware(x.claim_at) or datetime.min.replace(tzinfo=timezone.utc),reverse=True)]
    field_clusters=_field_clusters(claims)
    # Build traceability coverage: percentage of visible completed series-observation builds that have at least one genealogy item.
    builds=[b for b in db.scalars(select(VehicleBuild).where(VehicleBuild.project_code==project_code)).all() if _area_ok(b.manufacturing_area,manufacturing_area,allowed_area_codes) and _evidence_ok(b.evidence_document_ids,visible_document_ids) and b.build_type in {"series_observation","safe_launch","pre_series"}]
    build_ids={b.id for b in builds}; genealogy_build_ids={g.build_id for g in db.scalars(select(BuildGenealogyItem)).all() if g.build_id in build_ids and _evidence_ok(g.evidence_document_ids,visible_document_ids)}
    trace=round(len(genealogy_build_ids)*100/len(build_ids),1) if build_ids else None
    status="RED" if "RED" in {quality_band,capability_band,supplier_band} or open_contain else ("AMBER" if "AMBER" in {quality_band,capability_band,supplier_band} or assets else ("GREEN" if obs or caps else "NOT_CONFIGURED"))
    early=[]
    for x in change_points[:4]: early.append({"severity":"critical" if (x["rate_ratio"] or 999)>=5 else "high","type":"quality_change_point","title":f"{x['signal_key']}: рост дефектности","detail":f"{x['baseline_rate_pct']}% → {x['recent_rate_pct']}%","causal_claim":False})
    for x in supplier_lots[:4]: early.append({"severity":"critical" if (x["rate_ratio"] or 999)>=5 else "high","type":"supplier_lot","title":f"Supplier lot {x['supplier_lot']}","detail":f"{x['part_number']} · {x['defect_rate_pct']}% defects","causal_claim":False})
    for x in capability[:4]:
        if x["status"] in {"RED","AMBER"}: early.append({"severity":"high" if x["status"]=="RED" else "medium","type":"capability","title":x["characteristic"],"detail":f"Cpk {x['cpk'] if x['cpk'] is not None else x['ppk']} · {x['trend']}","causal_claim":False})
    for x in assets[:3]: early.append({"severity":"high" if "calibration_expired" in x["reasons"] else "medium","type":"asset","title":x["code"],"detail":", ".join(x["reasons"]),"causal_claim":False})
    return {
        "series_health":{"status":status,"production":{"produced":produced},"product_quality":{"band":quality_band,"inspected":inspected,"defects":defects,"defect_rate_pct":rate},
                         "process_capability":{"band":capability_band,"red":red_cap,"amber":amber_cap},"supplier_quality":{"band":supplier_band,"lot_signals":len(supplier_lots)},
                         "traceability_pct":trace,"open_containments":open_contain,"field_claims":len(claims)},
        "capability":capability,"change_points":change_points,"supplier_lot_intelligence":supplier_lots,
        "suspect_population_hint":{"use_endpoint":"POST /series-intelligence/suspect-population","available_genealogy_builds":len(build_ids)},
        "containments":contain,"pfmea_control_defect":pfmea,"control_effectiveness":control,"asset_signals":assets,
        "shift_patterns":shifts,"station_patterns":stations,"field_feedback":{"claims":field[:50],"clusters":field_clusters},
        "copq":_copq(obs,claims),"early_series_signals":early[:12],
        "counts":{"observations":len(obs),"capability_records":len(caps),"process_defects":len(rows["defects"]),"containments":len(contain),"field_claims":len(claims)},
        "governance":{"advisory_only":True,"read_only_source_systems":True,"not_mes_qms_or_erp":True,"no_operator_blame":True,"causal_claims":False,"human_root_cause_containment_pfmea_release_required":True},
    }


def series_intelligence_answer(workspace: dict, query: str) -> dict:
    q=query.lower(); facts=[]
    if any(k in q for k in ("cpk","cp ","capability","способн","стабил")):
        for x in workspace.get("capability",[])[:5]: facts.append(f"{x['characteristic']}: Cpk={x['cpk']} status={x['status']} trend={x['trend']}")
    elif any(k in q for k in ("supplier","постав","lot","парт")):
        for x in workspace.get("supplier_lot_intelligence",[])[:5]: facts.append(f"{x['supplier_code']} lot {x['supplier_lot']} / {x['part_number']}: {x['defect_rate_pct']}%, correlation only")
    elif any(k in q for k in ("field","warranty","гарант","поле")):
        for x in workspace.get("field_feedback",{}).get("clusters",[])[:5]: facts.append(f"{x['failure_mode']} / {x['part_number']}: {x['claims']} field claims")
    elif any(k in q for k in ("pfmea","control plan","контрол")):
        for x in workspace.get("pfmea_control_defect",[])[:5]: facts.append(f"{x['failure_mode']}: actual defects={x['actual_defect_quantity']}, review_required={x['review_required']}")
    else:
        for x in workspace.get("change_points",[])[:4]: facts.append(f"{x['signal_key']}: {x['baseline_rate_pct']}% → {x['recent_rate_pct']}%, causal claim not established")
        for x in workspace.get("early_series_signals",[])[:4]: facts.append(f"{x['type']}: {x['title']} — {x['detail']}")
    return {"answer":"\n".join(facts) if facts else "В доступном series evidence нет достаточных данных для детерминированного ответа.",
            "facts":facts,"causal_claim":False,"human_investigation_required":True,"source":"deterministic_series_intelligence"}
