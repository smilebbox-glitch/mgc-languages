from __future__ import annotations

import math
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from typing import Iterable

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import (
    BuildGenealogyItem,
    ChangeRequest,
    DesignFMEAItem,
    EngineeringRequirement,
    FieldQualityClaim,
    FieldReliabilityExposure,
    FieldServiceAction,
    Problem8D,
    RequirementVerification,
    VehicleBuild,
)


def _iso(v):
    return v.isoformat() if v else None


def _aware(v):
    if not v:
        return None
    return v if v.tzinfo else v.replace(tzinfo=timezone.utc)


def _evidence_ok(ids: Iterable[str] | None, visible_document_ids: set[str]) -> bool:
    values = set(ids or [])
    return not values or values.issubset(visible_document_ids)


def _area_ok(area: str | None, requested: str | None, allowed: set[str] | None) -> bool:
    if area and allowed is not None and area not in allowed:
        return False
    return not requested or area in {None, requested}


def _part_ok(part: str | None, visible_parts: set[str]) -> bool:
    if not part:
        return True
    return part.upper() in {x.upper() for x in visible_parts if x}


def _tokens(text: str | None) -> set[str]:
    if not text:
        return set()
    repl = {
        "leakage": "leak", "leaking": "leak", "leaked": "leak",
        "knocking": "knock", "clunk": "knock", "clunking": "knock",
        "трещины": "трещина", "течь": "утечка", "протечка": "утечка",
    }
    vals=[]
    for raw in re.findall(r"[a-zа-я0-9]+", text.lower()):
        raw=repl.get(raw,raw)
        if len(raw)>=3: vals.append(raw)
    return set(vals)


def normalize_failure_family(claim: FieldQualityClaim) -> str:
    if (claim.failure_family or "").strip():
        return claim.failure_family.strip().upper()
    toks=sorted(_tokens(claim.failure_mode))
    return " ".join(toks[:8]).upper() or claim.failure_mode.strip().upper()


def serialize_field_claim_v58(x: FieldQualityClaim) -> dict:
    detailed=float(x.part_cost or 0)+float(x.labor_cost or 0)+float(x.logistics_cost or 0)+float(x.dealer_handling_cost or 0)
    engineering_cost=detailed if detailed>0 else float(x.cost_estimate or 0)
    return {
        "id":x.id,"claim_reference":x.claim_reference,"vehicle_identifier":x.vehicle_identifier,
        "manufacturing_area":x.manufacturing_area,"part_number":x.part_number,"revision":x.revision,
        "supplier_code":x.supplier_code,"failure_mode":x.failure_mode,"failure_family":normalize_failure_family(x),
        "mileage_km":x.mileage_km,"in_service_at":_iso(x.in_service_at),"market":x.market,"climate_zone":x.climate_zone,
        "dealer_code":x.dealer_code,"repair_code":x.repair_code,"repair_method":x.repair_method,
        "no_trouble_found":bool(x.no_trouble_found),"repeat_repair":bool(x.repeat_repair),
        "severity":x.severity,"status":x.status,"claim_at":_iso(x.claim_at),"cost_estimate":float(x.cost_estimate or 0),
        "field_quality_cost_advisory":engineering_cost,"currency":x.currency,"linked_8d_id":x.linked_8d_id,
        "source_system":x.source_system,"evidence_document_ids":x.evidence_document_ids or [],"metadata":x.metadata_json or {},
    }


def serialize_exposure(x: FieldReliabilityExposure) -> dict:
    return {
        "id":x.id,"manufacturing_area":x.manufacturing_area,"part_number":x.part_number,"revision":x.revision,
        "supplier_code":x.supplier_code,"market":x.market,"climate_zone":x.climate_zone,"population_count":int(x.population_count or 0),
        "censored_count":int(x.censored_count or 0),"censor_mileage_km":x.censor_mileage_km,"total_exposure_km":x.total_exposure_km,
        "as_of_at":_iso(x.as_of_at),"source_system":x.source_system,"evidence_document_ids":x.evidence_document_ids or [],
        "metadata":x.metadata_json or {},
    }


def serialize_dfmea(x: DesignFMEAItem) -> dict:
    return {
        "id":x.id,"manufacturing_area":x.manufacturing_area,"part_number":x.part_number,"function":x.function,
        "failure_mode":x.failure_mode,"effect":x.effect,"cause":x.cause,"prevention_control":x.prevention_control,
        "detection_control":x.detection_control,"severity":x.severity,"occurrence":x.occurrence,"detection":x.detection,
        "action_priority":x.action_priority,"status":x.status,"evidence_document_ids":x.evidence_document_ids or [],
        "metadata":x.metadata_json or {},"human_update_required":True,
    }


def serialize_service_action(x: FieldServiceAction) -> dict:
    suspect=len(x.suspect_vehicle_identifiers or [])
    inspected=int(x.inspected_quantity or 0); repaired=int(x.repaired_quantity or 0); no_defect=int(x.no_defect_quantity or 0)
    return {
        "id":x.id,"code":x.code,"action_type":x.action_type,"title":x.title,"status":x.status,
        "manufacturing_area":x.manufacturing_area,"part_number":x.part_number,"revision":x.revision,"supplier_code":x.supplier_code,
        "failure_mode":x.failure_mode,"severity":x.severity,"safety_relevance":x.safety_relevance,
        "applicability":x.applicability_json or {},"diagnosis":x.diagnosis,"repair":x.repair,
        "suspect_vehicle_identifiers":x.suspect_vehicle_identifiers or [],"suspect_quantity":suspect,"inspected_quantity":inspected,
        "repaired_quantity":repaired,"no_defect_quantity":no_defect,"remaining_quantity":max(suspect-inspected,0),
        "progress_pct":round(inspected*100/suspect,1) if suspect else None,"linked_8d_id":x.linked_8d_id,"linked_change_id":x.linked_change_id,
        "evidence_document_ids":x.evidence_document_ids or [],"notes":x.notes,"metadata":x.metadata_json or {},
        "human_approval_required":bool(x.human_approval_required),"approved_by":x.approved_by,"approved_at":_iso(x.approved_at),
        "automatic_recall_or_campaign_decision":False,
    }


def visible_field_rows(db: Session, project_code: str, visible_document_ids: set[str], visible_part_numbers: set[str], manufacturing_area: str | None=None, allowed_area_codes: set[str] | None=None) -> dict:
    claims=[x for x in db.scalars(select(FieldQualityClaim).where(FieldQualityClaim.project_code==project_code)).all()
            if _area_ok(x.manufacturing_area,manufacturing_area,allowed_area_codes) and _part_ok(x.part_number,visible_part_numbers)
            and _evidence_ok(x.evidence_document_ids,visible_document_ids)]
    exposures=[x for x in db.scalars(select(FieldReliabilityExposure).where(FieldReliabilityExposure.project_code==project_code)).all()
               if _area_ok(x.manufacturing_area,manufacturing_area,allowed_area_codes) and _part_ok(x.part_number,visible_part_numbers)
               and _evidence_ok(x.evidence_document_ids,visible_document_ids)]
    dfmea=[x for x in db.scalars(select(DesignFMEAItem).where(DesignFMEAItem.project_code==project_code)).all()
           if _area_ok(x.manufacturing_area,manufacturing_area,allowed_area_codes) and _part_ok(x.part_number,visible_part_numbers)
           and _evidence_ok(x.evidence_document_ids,visible_document_ids)]
    actions=[x for x in db.scalars(select(FieldServiceAction).where(FieldServiceAction.project_code==project_code)).all()
             if _area_ok(x.manufacturing_area,manufacturing_area,allowed_area_codes) and _part_ok(x.part_number,visible_part_numbers)
             and _evidence_ok(x.evidence_document_ids,visible_document_ids)]
    return {"claims":claims,"exposures":exposures,"dfmea":dfmea,"actions":actions}


def _latest_exposures(rows: list[FieldReliabilityExposure]) -> list[FieldReliabilityExposure]:
    latest={}
    for x in rows:
        key=(x.part_number,x.revision,x.supplier_code,x.market,x.climate_zone)
        prev=latest.get(key)
        if prev is None or (_aware(x.as_of_at) or datetime.min.replace(tzinfo=timezone.utc))>(_aware(prev.as_of_at) or datetime.min.replace(tzinfo=timezone.utc)):
            latest[key]=x
    return list(latest.values())


def _claim_matches_exposure(c: FieldQualityClaim, e: FieldReliabilityExposure) -> bool:
    if c.part_number!=e.part_number: return False
    if e.revision and c.revision!=e.revision: return False
    if e.supplier_code and c.supplier_code!=e.supplier_code: return False
    if e.market and c.market!=e.market: return False
    if e.climate_zone and c.climate_zone!=e.climate_zone: return False
    return True


def _weibull_grouped(failure_mileages: list[float], censored_count: int, censor_mileage_km: float | None) -> dict:
    t=[float(x) for x in failure_mileages if x and x>0]
    if len(t)<3 or censored_count<1 or not censor_mileage_km or censor_mileage_km<=0:
        return {"status":"INSUFFICIENT_DATA","method":"two_parameter_weibull_grouped_right_censoring","failures_with_mileage":len(t),"censored_count":int(censored_count or 0)}
    c=max(int(censored_count),0); tc=float(censor_mileage_km); r=len(t); sum_log=sum(math.log(x) for x in t)
    best=None
    for i in range(286):
        beta=0.30+i*0.02
        total=sum(x**beta for x in t)+c*(tc**beta)
        if total<=0: continue
        eta=(total/r)**(1.0/beta)
        ll=r*math.log(beta)-r*beta*math.log(eta)+(beta-1)*sum_log-sum((x/eta)**beta for x in t)-c*((tc/eta)**beta)
        if best is None or ll>best[0]: best=(ll,beta,eta)
    if not best:
        return {"status":"INSUFFICIENT_DATA","method":"two_parameter_weibull_grouped_right_censoring"}
    _,beta,eta=best
    survival={str(k):round(math.exp(-((k/eta)**beta))*100,2) for k in (10000,30000,50000)}
    pattern="EARLY_FAILURE" if beta<1 else ("RANDOM" if beta<=1.2 else "WEAR_OUT")
    return {"status":"ESTIMATED","method":"two_parameter_weibull_grouped_right_censoring","beta":round(beta,3),"eta_km":round(eta,1),
            "mean_distance_to_failure_km":round(eta*math.gamma(1+1/beta),1),"pattern":pattern,"survival_pct":survival,
            "failures_with_mileage":r,"censored_count":c,"censor_mileage_km":tc,"advisory_only":True,"causal_claim":False}


def _reliability_metrics(claims: list[FieldQualityClaim], exposures: list[FieldReliabilityExposure]) -> list[dict]:
    out=[]
    for e in _latest_exposures(exposures):
        cs=[c for c in claims if _claim_matches_exposure(c,e)]
        failures=len(cs); pop=int(e.population_count or 0); rate=failures*100/pop if pop else None
        mileage=[float(c.mileage_km) for c in cs if c.mileage_km and c.mileage_km>0]
        censored=int(e.censored_count or 0) or max(pop-failures,0)
        wb=_weibull_grouped(mileage,censored,e.censor_mileage_km)
        total_km=float(e.total_exposure_km or 0)
        out.append({"part_number":e.part_number,"revision":e.revision,"supplier_code":e.supplier_code,"market":e.market,"climate_zone":e.climate_zone,
                    "population":pop,"failures":failures,"failure_rate_pct":round(rate,4) if rate is not None else None,
                    "failures_per_1000":round(failures*1000/pop,3) if pop else None,
                    "failures_per_million_km":round(failures*1_000_000/total_km,3) if total_km else None,
                    "median_failure_mileage_km":round(sorted(mileage)[len(mileage)//2],1) if mileage else None,
                    "weibull":wb,"as_of_at":_iso(e.as_of_at),"source_system":e.source_system})
    return sorted(out,key=lambda x:(x["failure_rate_pct"] if x["failure_rate_pct"] is not None else -1,x["failures"]),reverse=True)


def _failure_clusters(claims: list[FieldQualityClaim], metrics: list[dict]) -> list[dict]:
    groups=defaultdict(list)
    for c in claims:
        groups[(normalize_failure_family(c),c.part_number,c.revision,c.supplier_code,c.market,c.climate_zone)].append(c)
    out=[]
    for (fam,part,rev,supplier,market,climate),rows in groups.items():
        if len(rows)<2: continue
        severity=Counter((x.severity or "medium") for x in rows).most_common(1)[0][0]
        matching=[m for m in metrics if m["part_number"]==part and (not rev or m["revision"]==rev) and (not supplier or m["supplier_code"]==supplier)
                  and (not market or m["market"]==market) and (not climate or m["climate_zone"]==climate)]
        rate=matching[0]["failure_rate_pct"] if matching else None
        out.append({"failure_family":fam,"part_number":part,"revision":rev,"supplier_code":supplier,"market":market,"climate_zone":climate,
                    "claims":len(rows),"severity":severity,"failure_rate_pct":rate,"mileage_min":min([x.mileage_km for x in rows if x.mileage_km] or [None]),
                    "mileage_max":max([x.mileage_km for x in rows if x.mileage_km] or [None]),
                    "vehicle_identifiers":[x.vehicle_identifier for x in rows if x.vehicle_identifier][:100],"investigation_cluster":True,"causal_claim":False})
    return sorted(out,key=lambda x:(x["claims"],x["failure_rate_pct"] or 0),reverse=True)


def _dfmea_feedback(dfmea: list[DesignFMEAItem], clusters: list[dict]) -> list[dict]:
    out=[]
    for cl in clusters:
        ct=_tokens(cl["failure_family"])
        matches=[d for d in dfmea if (not d.part_number or d.part_number==cl["part_number"]) and (_tokens(d.failure_mode)&ct)]
        if not matches:
            out.append({"failure_family":cl["failure_family"],"part_number":cl["part_number"],"status":"DFMEA_REVIEW_REQUIRED",
                        "reason":"field_failure_not_linked_to_dfmea","field_claims":cl["claims"],"human_dfmea_update_required":True})
            continue
        for d in matches:
            rate=cl.get("failure_rate_pct")
            review=(int(d.occurrence or 1)<=2 and cl["claims"]>=3) or (rate is not None and rate>=0.5 and int(d.occurrence or 1)<=3)
            out.append({"dfmea_id":d.id,"failure_mode":d.failure_mode,"part_number":d.part_number,"dfmea_occurrence":d.occurrence,
                        "field_claims":cl["claims"],"field_failure_rate_pct":rate,"status":"DFMEA_REVIEW_REQUIRED" if review else "MONITOR",
                        "reason":"observed_field_occurrence_may_exceed_assumption" if review else "field_evidence_linked",
                        "human_dfmea_update_required":True})
    return sorted(out,key=lambda x:(x["status"]=="DFMEA_REVIEW_REQUIRED",x.get("field_claims",0)),reverse=True)


def _validation_effectiveness(db: Session, project_code: str, claims: list[FieldQualityClaim], clusters: list[dict], visible_document_ids: set[str]) -> list[dict]:
    reqs=[x for x in db.scalars(select(EngineeringRequirement).where(EngineeringRequirement.project_code==project_code)).all()
          if not x.source_document_id or x.source_document_id in visible_document_ids]
    req_by_id={x.id:x for x in reqs}
    vv=[x for x in db.scalars(select(RequirementVerification).where(RequirementVerification.project_code==project_code)).all()
        if x.requirement_id in req_by_id and _evidence_ok(x.evidence_document_ids,visible_document_ids)]
    out=[]
    for cl in clusters:
        part=cl.get("part_number"); ct=_tokens(cl["failure_family"])
        rqs=[r for r in reqs if (not part or part in (r.part_numbers or [])) and (_tokens((r.title or "")+" "+(r.requirement_text or ""))&ct)]
        vids=[v for v in vv if v.requirement_id in {r.id for r in rqs} and v.status.lower() in {"passed","pass","verified","complete","completed"}]
        field_miles=[float(c.mileage_km) for c in claims if c.part_number==part and (_tokens(normalize_failure_family(c))&ct) and c.mileage_km]
        observed=min(field_miles) if field_miles else None
        validated=[]
        for v in vids:
            md=v.metadata_json or {}; mr=v.measured_result_json or {}
            val=md.get("validated_mileage_km",mr.get("validated_mileage_km"))
            if isinstance(val,(int,float)) and val>0: validated.append(float(val))
        max_valid=max(validated) if validated else None
        gap=not vids or (observed is not None and max_valid is not None and observed>max_valid)
        out.append({"failure_family":cl["failure_family"],"part_number":part,"matched_requirements":len(rqs),"passed_verifications":len(vids),
                    "observed_failure_mileage_km":observed,"validated_mileage_km":max_valid,"status":"VALIDATION_COVERAGE_GAP" if gap else "COVERED",
                    "reason":"no_matching_passed_verification" if not vids else ("field_failure_beyond_validated_exposure" if gap else "field_failure_within_recorded_validation_exposure"),
                    "human_validation_scope_review_required":gap})
    return out


def _revision_effectiveness(metrics: list[dict]) -> list[dict]:
    groups=defaultdict(list)
    for m in metrics:
        if m["part_number"] and m["revision"] and m["population"]:
            groups[m["part_number"]].append(m)
    out=[]
    for part,rows in groups.items():
        by_rev={}
        for r in rows:
            rev=r["revision"]
            agg=by_rev.setdefault(rev,{"population":0,"failures":0})
            agg["population"]+=r["population"]; agg["failures"]+=r["failures"]
        if len(by_rev)<2: continue
        revs=[]
        for rev,a in by_rev.items():
            rate=a["failures"]*100/a["population"] if a["population"] else None
            revs.append({"revision":rev,**a,"failure_rate_pct":round(rate,4) if rate is not None else None})
        revs=sorted(revs,key=lambda x:x["revision"])
        best=min(revs,key=lambda x:x["failure_rate_pct"] if x["failure_rate_pct"] is not None else 1e9)
        worst=max(revs,key=lambda x:x["failure_rate_pct"] if x["failure_rate_pct"] is not None else -1)
        improvement=None
        if worst["failure_rate_pct"] and best["failure_rate_pct"] is not None:
            improvement=round((worst["failure_rate_pct"]-best["failure_rate_pct"])*100/worst["failure_rate_pct"],1)
        out.append({"part_number":part,"revisions":revs,"best_observed_revision":best["revision"],"worst_observed_revision":worst["revision"],
                    "observed_improvement_pct":improvement,"positive_signal":bool(improvement is not None and improvement>=20),
                    "human_effectiveness_confirmation_required":True,"causal_claim":False})
    return out


def _repair_patterns(claims: list[FieldQualityClaim]) -> list[dict]:
    groups=defaultdict(list)
    for c in claims:
        if c.repair_method or c.repair_code:
            groups[c.repair_method or c.repair_code].append(c)
    out=[]
    for method,rows in groups.items():
        repeat=sum(1 for x in rows if x.repeat_repair); ntf=sum(1 for x in rows if x.no_trouble_found)
        out.append({"repair_method":method,"claims":len(rows),"repeat_repairs":repeat,"repeat_repair_rate_pct":round(repeat*100/len(rows),2),
                    "no_trouble_found":ntf,"ntf_rate_pct":round(ntf*100/len(rows),2),"technical_pattern_only":True,"dealer_performance_rating":False})
    return sorted(out,key=lambda x:(x["repeat_repair_rate_pct"],x["claims"]),reverse=True)


def _field_cost(claims: list[FieldQualityClaim]) -> list[dict]:
    by=defaultdict(lambda:{"parts":0.0,"labor":0.0,"logistics":0.0,"dealer_handling":0.0,"legacy_estimate":0.0})
    for c in claims:
        cur=c.currency or "RUB"; detailed=float(c.part_cost or 0)+float(c.labor_cost or 0)+float(c.logistics_cost or 0)+float(c.dealer_handling_cost or 0)
        by[cur]["parts"]+=float(c.part_cost or 0);by[cur]["labor"]+=float(c.labor_cost or 0);by[cur]["logistics"]+=float(c.logistics_cost or 0);by[cur]["dealer_handling"]+=float(c.dealer_handling_cost or 0)
        if detailed<=0: by[cur]["legacy_estimate"]+=float(c.cost_estimate or 0)
    out=[]
    for cur,v in by.items():
        total=sum(v.values()); out.append({"currency":cur,**{k:round(x,2) for k,x in v.items()},"total":round(total,2),"advisory_only":True,"erp_warranty_finance_system_of_record":True})
    return out


def _campaign_candidates(clusters: list[dict]) -> list[dict]:
    out=[]
    for c in clusters:
        sev=(c.get("severity") or "medium").lower(); rate=c.get("failure_rate_pct")
        if sev in {"critical","high"} and (c["claims"]>=3 or (rate is not None and rate>=0.5)):
            out.append({"failure_family":c["failure_family"],"part_number":c["part_number"],"revision":c["revision"],"claims":c["claims"],
                        "failure_rate_pct":rate,"severity":sev,"status":"REVIEW_REQUIRED","campaign_or_recall_decision":False,
                        "required_authorities":["Quality","Engineering","Legal/Homologation","Management"],"advisory_only":True})
    return out


def _action_applicability(action: FieldServiceAction, vehicle_identifier: str, genealogy: list[BuildGenealogyItem]) -> str:
    if vehicle_identifier in set(action.suspect_vehicle_identifiers or []): return "APPLICABLE"
    app=action.applicability_json or {}
    vf=app.get("vin_from"); vt=app.get("vin_to")
    if vf and vehicle_identifier<str(vf): return "NOT_APPLICABLE"
    if vt and vehicle_identifier>str(vt): return "NOT_APPLICABLE"
    candidates=genealogy
    if action.part_number: candidates=[g for g in candidates if g.part_number==action.part_number]
    if action.revision: candidates=[g for g in candidates if g.revision==action.revision]
    if action.supplier_code: candidates=[g for g in candidates if g.supplier_code==action.supplier_code]
    if action.part_number or action.revision or action.supplier_code:
        return "APPLICABLE" if candidates else "NOT_APPLICABLE"
    return "UNKNOWN"


def vin_field_trace(db: Session, project_code: str, vehicle_identifier: str, visible_document_ids: set[str], visible_part_numbers: set[str], allowed_area_codes: set[str] | None=None) -> dict:
    builds=[b for b in db.scalars(select(VehicleBuild).where(VehicleBuild.project_code==project_code,VehicleBuild.vehicle_identifier==vehicle_identifier)).all()
            if _area_ok(b.manufacturing_area,None,allowed_area_codes) and _evidence_ok(b.evidence_document_ids,visible_document_ids)]
    build=sorted(builds,key=lambda x:_aware(x.completed_at or x.started_at) or datetime.min.replace(tzinfo=timezone.utc),reverse=True)[0] if builds else None
    genealogy=[]
    if build:
        genealogy=[g for g in db.scalars(select(BuildGenealogyItem).where(BuildGenealogyItem.build_id==build.id)).all()
                   if _part_ok(g.part_number,visible_part_numbers) and _evidence_ok(g.evidence_document_ids,visible_document_ids)]
    claims=[c for c in db.scalars(select(FieldQualityClaim).where(FieldQualityClaim.project_code==project_code,FieldQualityClaim.vehicle_identifier==vehicle_identifier)).all()
            if _part_ok(c.part_number,visible_part_numbers) and _evidence_ok(c.evidence_document_ids,visible_document_ids)]
    actions=[a for a in db.scalars(select(FieldServiceAction).where(FieldServiceAction.project_code==project_code)).all()
             if _part_ok(a.part_number,visible_part_numbers) and _evidence_ok(a.evidence_document_ids,visible_document_ids)]
    applicable=[{**serialize_service_action(a),"vin_applicability":_action_applicability(a,vehicle_identifier,genealogy)} for a in actions]
    return {"vehicle_identifier":vehicle_identifier,"build":{"id":build.id,"code":build.code,"variant_id":build.variant_id,"plant":build.plant,"completed_at":_iso(build.completed_at)} if build else None,
            "genealogy":[{"part_number":g.part_number,"revision":g.revision,"supplier_code":g.supplier_code,"lot_number":g.lot_number,"serial_number":g.serial_number} for g in genealogy],
            "field_claims":[serialize_field_claim_v58(c) for c in claims],"service_actions":applicable,"traceability_status":"FOUND" if build or claims else "NOT_FOUND",
            "customer_profile_inference":False}


def field_reliability_workspace(db: Session, project_code: str, visible_document_ids: set[str], visible_part_numbers: set[str], manufacturing_area: str | None=None, allowed_area_codes: set[str] | None=None, vehicle_identifier: str | None=None) -> dict:
    rows=visible_field_rows(db,project_code,visible_document_ids,visible_part_numbers,manufacturing_area,allowed_area_codes)
    claims=rows["claims"]; exposures=rows["exposures"]; dfmea=rows["dfmea"]; actions=rows["actions"]
    metrics=_reliability_metrics(claims,exposures); clusters=_failure_clusters(claims,metrics)
    dfmea_fb=_dfmea_feedback(dfmea,clusters); vv=_validation_effectiveness(db,project_code,claims,clusters,visible_document_ids)
    rev_eff=_revision_effectiveness(metrics); repair=_repair_patterns(claims); costs=_field_cost(claims); campaign=_campaign_candidates(clusters)
    trace=vin_field_trace(db,project_code,vehicle_identifier,visible_document_ids,visible_part_numbers,allowed_area_codes) if vehicle_identifier else None
    severity_counts=Counter((x.severity or "medium").lower() for x in claims)
    open_claims=sum(1 for x in claims if x.status not in {"closed","cancelled"})
    high_reviews=sum(1 for x in dfmea_fb if x["status"]=="DFMEA_REVIEW_REQUIRED")+sum(1 for x in vv if x["status"]=="VALIDATION_COVERAGE_GAP")
    health="RED" if severity_counts.get("critical",0)>0 or campaign else ("AMBER" if severity_counts.get("high",0)>0 or high_reviews else ("GREEN" if claims or exposures else "NOT_CONFIGURED"))
    return {
        "schema_version":"mgc-field-reliability-v1","project_code":project_code,"manufacturing_area":manufacturing_area,
        "field_health":{"band":health,"open_claims":open_claims,"critical_claims":severity_counts.get("critical",0),"high_claims":severity_counts.get("high",0),"review_gaps":high_reviews},
        "counts":{"claims":len(claims),"exposure_snapshots":len(exposures),"dfmea_items":len(dfmea),"service_actions":len(actions)},
        "reliability":metrics,"failure_clusters":clusters,"dfmea_feedback":dfmea_fb,"validation_effectiveness":vv,"revision_effectiveness":rev_eff,
        "repair_patterns":repair,"field_quality_cost":costs,"campaign_candidates":campaign,
        "service_actions":[serialize_service_action(x) for x in sorted(actions,key=lambda x:_aware(x.updated_at) or datetime.min.replace(tzinfo=timezone.utc),reverse=True)],
        "recent_claims":[serialize_field_claim_v58(x) for x in sorted(claims,key=lambda x:_aware(x.claim_at) or datetime.min.replace(tzinfo=timezone.utc),reverse=True)[:50]],
        "vin_trace":trace,
        "governance":{"advisory_only":True,"causal_claim":False,"human_root_cause_confirmation_required":True,"human_dfmea_and_validation_updates_required":True,
                      "no_automatic_recall_or_campaign":True,"dms_warranty_system_of_record":True,"no_driver_profiling":True,"cpu_only_deterministic_core":True},
    }


def field_intelligence_answer(workspace: dict, query: str) -> dict:
    q=query.lower(); lines=[]
    if any(k in q for k in ["надеж", "reliab", "weibull", "ресурс", "отказ"]):
        for r in workspace.get("reliability",[])[:5]:
            lines.append(f"{r['part_number']} {r.get('revision') or '—'}: {r['failures']}/{r['population']} failures, {r.get('failure_rate_pct')}%, Weibull {r['weibull'].get('status')}")
    elif any(k in q for k in ["dfmea","fmea","валидац","validation"]):
        for x in (workspace.get("dfmea_feedback",[])+workspace.get("validation_effectiveness",[]))[:8]:
            lines.append(f"{x.get('part_number') or '—'} · {x.get('failure_family') or x.get('failure_mode')}: {x.get('status')}")
    elif any(k in q for k in ["campaign","кампан","recall","отзыв"]):
        for x in workspace.get("campaign_candidates",[])[:8]: lines.append(f"{x['part_number']} · {x['failure_family']}: {x['status']} ({x['claims']} claims)")
        if not lines: lines.append("No campaign-review candidate is produced by current accessible evidence.")
    elif any(k in q for k in ["repair","ремонт","ntf","повтор"]):
        for x in workspace.get("repair_patterns",[])[:8]: lines.append(f"{x['repair_method']}: repeat {x['repeat_repair_rate_pct']}%, NTF {x['ntf_rate_pct']}%")
    else:
        for x in workspace.get("failure_clusters",[])[:8]: lines.append(f"{x['failure_family']} · {x.get('part_number') or '—'}: {x['claims']} claims, observed rate {x.get('failure_rate_pct')}%")
    if not lines: lines=["Недостаточно доступных field/reliability evidence для детерминированного ответа."]
    return {"answer":"\n".join(lines),"generated":False,"causal_claim":False,"human_investigation_required":True,"sources":"controlled_field_reliability_records"}
