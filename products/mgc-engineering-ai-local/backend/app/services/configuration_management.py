from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import (
    ArchitectureNode, ChangeRequest, ConfigurationApplicability, Document,
    EngineeringRequirement, InterfaceDefinition, VehicleVariant,
)
from app.services.vehicle_architecture import vehicle_architecture_workspace
from app.core.vehicle_applicability import VEHICLE_CLASSES, vehicle_profile
from app.services.requirements_matrix import requirements_matrix

TERMINAL_CHANGE = {"implemented", "rejected", "cancelled"}


def _dt(v): return v.isoformat() if v else None

def _in_area(area, requested, allowed):
    if area and allowed is not None and area not in allowed: return False
    if requested: return area in {None, requested}
    return True


def serialize_variant(x: VehicleVariant, visible_document_ids: set[str] | None = None):
    visible = visible_document_ids if visible_document_ids is not None else set(x.evidence_document_ids or [])
    profile = vehicle_profile(x.attributes_json)
    return {
        "id": x.id, "project_code": x.project_code, "manufacturing_area": x.manufacturing_area,
        "code": x.code, "name": x.name, "status": x.status, "model_year": x.model_year,
        "market": x.market, "body_style": x.body_style, "engine": x.engine,
        "transmission": x.transmission, "trim": x.trim, "supplier_strategy": x.supplier_strategy,
        "vehicle_class": profile.get("vehicle_class"), "configuration": profile,
        "attributes": x.attributes_json or {},
        "evidence_document_ids": [d for d in (x.evidence_document_ids or []) if d in visible],
        "notes": x.notes, "created_by": x.created_by, "created_at": _dt(x.created_at), "updated_at": _dt(x.updated_at),
    }


def serialize_applicability(x: ConfigurationApplicability, variant: VehicleVariant | None = None, visible_document_ids: set[str] | None = None):
    visible = visible_document_ids if visible_document_ids is not None else set(x.evidence_document_ids or [])
    return {
        "id": x.id, "project_code": x.project_code, "variant_id": x.variant_id,
        "variant_code": variant.code if variant else None, "manufacturing_area": x.manufacturing_area,
        "entity_type": x.entity_type, "entity_key": x.entity_key, "applicability": x.applicability,
        "source": x.source, "effectivity_from": x.effectivity_from, "effectivity_to": x.effectivity_to,
        "evidence_document_ids": [d for d in (x.evidence_document_ids or []) if d in visible],
        "notes": x.notes, "created_at": _dt(x.created_at), "updated_at": _dt(x.updated_at),
    }


def _entity_visible(db: Session, row: ConfigurationApplicability, visible_document_ids: set[str], visible_part_numbers: set[str], visible_arch_nodes: set[str], visible_interfaces: set[str], visible_requirements: set[str]) -> bool:
    k=row.entity_key
    if row.entity_type == "part": return k.upper() in visible_part_numbers
    if row.entity_type == "document": return k in visible_document_ids
    if row.entity_type == "architecture_node": return k in visible_arch_nodes
    if row.entity_type == "interface": return k in visible_interfaces
    if row.entity_type == "requirement": return k in visible_requirements
    if row.entity_type == "change":
        ch=db.get(ChangeRequest,k)
        return bool(ch and (not ch.part_number or ch.part_number in visible_part_numbers))
    return False


def configuration_workspace(db: Session, project_code: str, visible_document_ids: set[str], visible_part_numbers: set[str], manufacturing_area: str | None = None, allowed_area_codes: set[str] | None = None):
    arch=vehicle_architecture_workspace(db,project_code,visible_document_ids,visible_part_numbers,manufacturing_area,allowed_area_codes)
    req=requirements_matrix(db,project_code,visible_document_ids,visible_part_numbers,manufacturing_area,allowed_area_codes)
    visible_arch_nodes={x["id"] for x in arch.get("nodes",[])}
    visible_interfaces={x["id"] for x in arch.get("interfaces",[])}
    visible_requirements={x["id"] for x in req.get("requirements",[])}

    variants=[]
    for x in db.scalars(select(VehicleVariant).where(VehicleVariant.project_code==project_code).order_by(VehicleVariant.code)).all():
        if not _in_area(x.manufacturing_area,manufacturing_area,allowed_area_codes): continue
        if x.evidence_document_ids and not set(x.evidence_document_ids).issubset(visible_document_ids): continue
        variants.append(x)
    variant_map={x.id:x for x in variants}

    mappings=[]
    for x in db.scalars(select(ConfigurationApplicability).where(ConfigurationApplicability.project_code==project_code).order_by(ConfigurationApplicability.entity_type,ConfigurationApplicability.entity_key)).all():
        if x.variant_id not in variant_map: continue
        if not _in_area(x.manufacturing_area,manufacturing_area,allowed_area_codes): continue
        if x.evidence_document_ids and not set(x.evidence_document_ids).issubset(visible_document_ids): continue
        if not _entity_visible(db,x,visible_document_ids,visible_part_numbers,visible_arch_nodes,visible_interfaces,visible_requirements): continue
        mappings.append(x)

    by_variant={x.id:[] for x in variants}
    by_entity={}
    for x in mappings:
        by_variant.setdefault(x.variant_id,[]).append(x)
        by_entity.setdefault((x.entity_type,x.entity_key),[]).append(x)

    gaps=[]
    for v in variants:
        rows=by_variant.get(v.id,[])
        if v.status in {"active","released"} and not rows:
            gaps.append({"type":"variant_unmapped","severity":"warning","id":v.id,"title":f"{v.code}: применимость ещё не настроена"})
        if v.status=="released" and not v.evidence_document_ids:
            gaps.append({"type":"variant_evidence","severity":"warning","id":v.id,"title":f"{v.code}: released-вариант без evidence конфигурации"})
    # Conflicting rows are prevented by uniqueness, but invalid references/imports remain visible as gaps via validation below.
    mapped_parts={x.entity_key.upper() for x in mappings if x.entity_type=="part" and x.applicability=="included"}
    scoped_parts={x.entity_key.upper() for x in mappings if x.entity_type=="part"}
    unresolved_parts=sorted(scoped_parts-mapped_parts)
    for pn in unresolved_parts[:50]:
        gaps.append({"type":"part_excluded_all","severity":"warning","id":pn,"title":f"{pn}: деталь исключена из всех явно настроенных вариантов"})

    configured=bool(variants or mappings)
    active=[v for v in variants if v.status in {"active","released"}]
    mapped_active=sum(bool(by_variant.get(v.id)) for v in active)
    score=100.0 if configured and not active else (round(100* mapped_active/max(len(active),1),1) if configured else 0.0)
    if any(g["severity"]=="critical" for g in gaps): status="blocked"
    elif gaps or score<85: status="needs_review"
    else: status="candidate"

    views=[]
    for v in variants:
        vv=serialize_variant(v,visible_document_ids)
        rows=by_variant.get(v.id,[])
        vv["applicability_count"]=len(rows)
        vv["included_parts"]=sorted({r.entity_key.upper() for r in rows if r.entity_type=="part" and r.applicability=="included"})
        views.append(vv)
    app_views=[serialize_applicability(x,variant_map.get(x.variant_id),visible_document_ids) for x in mappings]
    class_counts = {}
    for v in views:
        key = v.get("vehicle_class") or "unspecified"
        class_counts[key] = class_counts.get(key, 0) + 1
    return {
        "configured": configured, "score": score, "status": status, "advisory_only": True,
        "unknown_is_not_included": True,
        "vehicle_scope": {"supported_classes": list(VEHICLE_CLASSES), "class_counts": class_counts, "multi_vehicle": len([k for k,v in class_counts.items() if k != "unspecified" and v]) > 1},
        "counts": {"variants":len(variants),"active_variants":len(active),"applicability":len(mappings),"mapped_parts":len(mapped_parts),"gaps":len(gaps)},
        "variants": views, "applicability": app_views, "gaps": gaps,
        "recommended_checks": [
            "Не считать UNKNOWN применимостью ко всем вариантам",
            "Проверить двигатель/КПП/рынок/кузов/комплектацию перед ECR/ECO",
            "Подтверждать released-конфигурации evidence из PLM/BOM/продуктовой документации",
            "При изменении интерфейса проверить все затронутые vehicle variants",
        ],
    }


def configuration_impact(db: Session, project_code: str, part_number: str, visible_document_ids: set[str], visible_part_numbers: set[str], manufacturing_area: str | None = None, allowed_area_codes: set[str] | None = None):
    pn=part_number.upper()
    ws=configuration_workspace(db,project_code,visible_document_ids,visible_part_numbers,manufacturing_area,allowed_area_codes)
    variants={v["id"]:v for v in ws.get("variants",[])}
    direct=[x for x in ws.get("applicability",[]) if x["entity_type"]=="part" and x["entity_key"].upper()==pn]
    included=[variants[x["variant_id"]] for x in direct if x["applicability"]=="included" and x["variant_id"] in variants]
    excluded=[variants[x["variant_id"]] for x in direct if x["applicability"]=="excluded" and x["variant_id"] in variants]
    configured_variant_ids={x["variant_id"] for x in direct}

    arch=vehicle_architecture_workspace(db,project_code,visible_document_ids,visible_part_numbers,manufacturing_area,allowed_area_codes)
    part_node_ids={x["id"] for x in arch.get("nodes",[]) if x.get("part_number")==pn}
    related_interfaces=[x for x in arch.get("interfaces",[]) if x.get("source_node_id") in part_node_ids or x.get("target_node_id") in part_node_ids]
    interface_ids={x["id"] for x in related_interfaces}
    indirect=[]
    for x in ws.get("applicability",[]):
        if x["entity_type"]=="interface" and x["entity_key"] in interface_ids and x["applicability"]=="included" and x["variant_id"] in variants:
            indirect.append(variants[x["variant_id"]])
    # Explicit part applicability has precedence over interface-derived applicability.
    direct_excluded_ids={x["id"] for x in excluded}
    merged={x["id"]:x for x in included}
    for x in indirect:
        if x["id"] not in configured_variant_ids and x["id"] not in direct_excluded_ids:
            merged[x["id"]]=x
    resolved_variant_ids=configured_variant_ids | set(merged)
    unknown=[v for vid,v in variants.items() if vid not in resolved_variant_ids and v.get("status") in {"active","released"}]
    changes=[c for c in db.scalars(select(ChangeRequest).where(ChangeRequest.part_number==pn)).all() if c.status not in TERMINAL_CHANGE]
    return {
        "part_number":pn,"affected_variants":list(merged.values()),"direct_included_variants":included,"indirect_interface_variants":indirect,
        "excluded_variants":excluded,"unknown_variants":unknown,"applicability_resolved":bool(direct),
        "related_interfaces":[{"id":x["id"],"code":x["code"],"name":x["name"]} for x in related_interfaces],
        "open_changes":[{"id":c.id,"code":c.eco_code or c.code,"status":c.status} for c in changes],
        "advisory_only":True,"unknown_is_not_included":True,
    }
