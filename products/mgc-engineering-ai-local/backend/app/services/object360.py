from __future__ import annotations

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.core.runtime_contract import OBJECT_TYPE_CAPABILITIES, available_object_types
from app.db.models import (
    BOMItem, BuildDefectLink, BuildGenealogyItem, ChangeRequest, Document,
    EngineeringRequirement, FieldQualityClaim, IncomingQualityRecord, Part,
    ProcessDefect, Project, RequirementVerification, ValidationIssue, VehicleBuild,
)
from app.platform.actions import normalize_action
from app.platform.evidence import EvidenceRef, evidence_bundle
from app.services.project_workspace import project_allowed

OBJECT360_SCHEMA = "mgc-object360-v1"
SUPPORTED_OBJECT_TYPES = set(OBJECT_TYPE_CAPABILITIES)


def _iso(value):
    return value.isoformat() if value is not None and hasattr(value, "isoformat") else value


def _project_visible(db: Session, project_code: str | None, groups: list[str]) -> bool:
    if not project_code:
        return True
    project = db.scalar(select(Project).where(Project.code == project_code))
    return bool(project and project_allowed(project, groups))


def _all_evidence_visible(ids: list[str] | None, visible_document_ids: set[str]) -> bool:
    ids = [str(x) for x in (ids or []) if x]
    return not ids or set(ids).issubset(visible_document_ids)


def _part(db: Session, key: str, visible_document_ids: set[str], groups: list[str]) -> dict | None:
    pn = key.upper()
    part = db.scalar(select(Part).where(Part.part_number == pn))
    if not part or not _project_visible(db, part.project_code, groups):
        return None
    docs = db.scalars(select(Document).where(Document.part_number == pn).order_by(Document.created_at.desc())).all()
    docs = [d for d in docs if d.id in visible_document_ids]
    if not docs:
        return None
    doc_ids = {d.id for d in docs}
    bom = [x for x in db.scalars(select(BOMItem).where(BOMItem.parent_part_number == pn)).all() if x.source_document_id in doc_ids]
    issues = [x for x in db.scalars(select(ValidationIssue).where(ValidationIssue.part_number == pn)).all() if not x.document_ids or set(x.document_ids).issubset(doc_ids)]
    changes = [x for x in db.scalars(select(ChangeRequest).where(ChangeRequest.part_number == pn).order_by(ChangeRequest.updated_at.desc())).all() if _all_evidence_visible(x.affected_document_ids, visible_document_ids)]
    evidence = evidence_bundle([EvidenceRef("document", d.id, document_id=d.id, revision=d.revision) for d in docs], require_document_visibility=visible_document_ids)
    actions = [normalize_action({"id": i.id, "domain": "manufacturing_quality", "type": "validation_issue", "title": i.title, "reason": i.rule_code, "priority": getattr(i.severity, "value", str(i.severity)), "entity": {"type": "part", "id": pn}}) for i in issues if getattr(i.status, "value", str(i.status)) != "closed"]
    actions += [normalize_action({"id": c.id, "domain": "configuration_change", "type": "change", "title": c.title, "reason": c.status, "priority": "high" if c.risk_level in {"high","critical"} else "medium", "decision_required": c.status in {"review","approval","review_required"}, "entity": {"type": "change", "id": c.id}}) for c in changes if c.status not in {"implemented","rejected","cancelled"}]
    return {
        "identity": {"type": "part", "id": pn, "label": part.name or pn, "project_code": part.project_code, "revision": part.latest_revision},
        "summary": {"documents": len(docs), "bom_children": len(bom), "open_issues": len(actions), "changes": len(changes)},
        "sections": {
            "documents": [{"id": d.id, "filename": d.filename, "revision": d.revision, "doc_type": d.doc_type, "manufacturing_area": d.manufacturing_area} for d in docs[:50]],
            "bom": [{"part_number": x.child_part_number, "revision": x.child_revision, "quantity": x.quantity, "unit": x.unit, "supplier_code": x.supplier_code, "position": x.position} for x in bom[:200]],
            "changes": [{"id": c.id, "code": c.code, "title": c.title, "status": c.status, "from_revision": c.from_revision, "to_revision": c.to_revision, "risk_level": c.risk_level} for c in changes[:50]],
        },
        "evidence": evidence,
        "actions": actions[:20],
    }


def _vin(db: Session, key: str, visible_document_ids: set[str], groups: list[str], *, include_supplier_field: bool = True) -> dict | None:
    build = db.scalar(select(VehicleBuild).where(VehicleBuild.vehicle_identifier == key))
    if not build or not _project_visible(db, build.project_code, groups) or not _all_evidence_visible(build.evidence_document_ids, visible_document_ids):
        return None
    genealogy = [x for x in db.scalars(select(BuildGenealogyItem).where(BuildGenealogyItem.build_id == build.id)).all() if _all_evidence_visible(x.evidence_document_ids, visible_document_ids)]
    defects = db.scalars(select(BuildDefectLink).where(BuildDefectLink.build_id == build.id)).all()
    field = db.scalars(select(FieldQualityClaim).where(FieldQualityClaim.vehicle_identifier == key)).all() if include_supplier_field else []
    field = [x for x in field if _project_visible(db, x.project_code, groups) and _all_evidence_visible(x.evidence_document_ids, visible_document_ids)]
    evid_ids = list(build.evidence_document_ids or []) + [i for x in genealogy for i in (x.evidence_document_ids or [])] + [i for x in field for i in (x.evidence_document_ids or [])]
    evidence = evidence_bundle([EvidenceRef("document", x, document_id=x) for x in evid_ids], require_document_visibility=visible_document_ids)
    actions=[]
    for x in field:
        if x.status not in {"closed","resolved"}:
            actions.append(normalize_action({"id": x.id, "domain":"supplier_field", "type":"field_claim", "title":x.failure_mode, "reason":x.status, "priority":x.severity, "entity":{"type":"vin","id":key}}))
    return {
        "identity": {"type":"vin", "id":key, "label":key, "project_code":build.project_code, "status":build.status},
        "summary": {"genealogy_items":len(genealogy), "build_defects":len(defects), "field_claims":len(field)},
        "sections": {
            "build": {"id":build.id, "code":build.code, "status":build.status, "plant":build.plant, "build_type":build.build_type, "completed_at":_iso(build.completed_at)},
            "genealogy": [{"part_number":x.part_number,"revision":x.revision,"supplier_code":x.supplier_code,"lot_number":x.lot_number,"serial_number":x.serial_number,"source_system":x.source_system} for x in genealogy[:500]],
            "field_claims": [{"id":x.id,"claim_reference":x.claim_reference,"part_number":x.part_number,"revision":x.revision,"supplier_code":x.supplier_code,"failure_mode":x.failure_mode,"status":x.status,"severity":x.severity} for x in field[:100]],
        },
        "evidence": evidence,
        "actions": actions[:20],
    }


def _change(db: Session, key: str, visible_document_ids: set[str], groups: list[str]) -> dict | None:
    row = db.scalar(select(ChangeRequest).where(or_(ChangeRequest.id == key, ChangeRequest.code == key, ChangeRequest.eco_code == key)))
    if not row or not _all_evidence_visible(row.affected_document_ids, visible_document_ids):
        return None
    docs = db.scalars(select(Document).where(Document.id.in_(row.affected_document_ids or []))).all() if row.affected_document_ids else []
    project_codes={d.project_code for d in docs if d.project_code}
    if any(not _project_visible(db,p,groups) for p in project_codes): return None
    evidence=evidence_bundle([EvidenceRef("document",d.id,document_id=d.id,revision=d.revision) for d in docs], require_document_visibility=visible_document_ids)
    action=normalize_action({"id":row.id,"domain":"configuration_change","type":"change","title":row.title,"reason":row.status,"priority":"high" if row.risk_level in {"high","critical"} else "medium","decision_required":row.status in {"review","approval","review_required"},"entity":{"type":"change","id":row.id}})
    return {"identity":{"type":"change","id":row.id,"label":row.code,"status":row.status,"part_number":row.part_number},"summary":{"risk_level":row.risk_level,"affected_parts":len(row.affected_parts or []),"affected_documents":len(docs)},"sections":{"change":{"code":row.code,"eco_code":row.eco_code,"title":row.title,"description":row.description,"reason":row.reason,"from_revision":row.from_revision,"to_revision":row.to_revision,"owner":row.owner},"affected_parts":row.affected_parts or []},"evidence":evidence,"actions":[] if row.status in {"implemented","rejected","cancelled"} else [action]}


def _defect(db: Session, key: str, visible_document_ids: set[str], groups: list[str]) -> dict | None:
    row = db.scalar(select(ProcessDefect).where(or_(ProcessDefect.id == key, ProcessDefect.defect_code == key)))
    if not row or not _project_visible(db,row.project_code,groups) or not _all_evidence_visible(row.evidence_document_ids,visible_document_ids): return None
    evidence=evidence_bundle([EvidenceRef("document",x,document_id=x) for x in (row.evidence_document_ids or [])], require_document_visibility=visible_document_ids)
    action=normalize_action({"id":row.id,"domain":"manufacturing_quality","type":"defect","title":row.title,"reason":row.status,"priority":row.severity,"entity":{"type":"defect","id":row.id}})
    return {"identity":{"type":"defect","id":row.id,"label":row.defect_code or row.title,"project_code":row.project_code,"status":row.status},"summary":{"severity":row.severity,"quantity":row.quantity,"part_number":row.part_number},"sections":{"defect":{"title":row.title,"manufacturing_area":row.manufacturing_area,"part_number":row.part_number,"linked_8d_id":row.linked_8d_id,"occurred_at":_iso(row.occurred_at)}},"evidence":evidence,"actions":[] if row.status in {"closed","resolved"} else [action]}


def _requirement(db: Session, key: str, visible_document_ids: set[str], groups: list[str]) -> dict | None:
    row=db.scalar(select(EngineeringRequirement).where(or_(EngineeringRequirement.id==key,EngineeringRequirement.code==key)))
    if not row or not _project_visible(db,row.project_code,groups): return None
    if row.source_document_id and row.source_document_id not in visible_document_ids: return None
    vv=db.scalars(select(RequirementVerification).where(RequirementVerification.requirement_id==row.id)).all()
    vv=[x for x in vv if _all_evidence_visible(x.evidence_document_ids,visible_document_ids)]
    evid=[]
    if row.source_document_id: evid.append(EvidenceRef("document",row.source_document_id,document_id=row.source_document_id))
    for x in vv:
        evid += [EvidenceRef("document",i,document_id=i) for i in (x.evidence_document_ids or [])]
    return {"identity":{"type":"requirement","id":row.id,"label":row.code,"project_code":row.project_code,"status":row.status},"summary":{"criticality":row.criticality,"verifications":len(vv),"parts":len(row.part_numbers or [])},"sections":{"requirement":{"title":row.title,"text":row.requirement_text,"verification_method":row.verification_method,"acceptance_criteria":row.acceptance_criteria,"owner":row.owner},"verifications":[{"id":x.id,"code":x.code,"title":x.title,"status":x.status,"phase":x.phase,"result_summary":x.result_summary} for x in vv]},"evidence":evidence_bundle(evid,require_document_visibility=visible_document_ids),"actions":[]}


def _supplier(db: Session, key: str, visible_document_ids: set[str], groups: list[str]) -> dict | None:
    incoming=db.scalars(select(IncomingQualityRecord).where(IncomingQualityRecord.supplier_code==key).order_by(IncomingQualityRecord.occurred_at.desc())).all()
    incoming=[x for x in incoming if _project_visible(db,x.project_code,groups) and _all_evidence_visible(x.evidence_document_ids,visible_document_ids)]
    field=db.scalars(select(FieldQualityClaim).where(FieldQualityClaim.supplier_code==key).order_by(FieldQualityClaim.claim_at.desc())).all()
    field=[x for x in field if _project_visible(db,x.project_code,groups) and _all_evidence_visible(x.evidence_document_ids,visible_document_ids)]
    if not incoming and not field: return None
    evid=[EvidenceRef("document",i,document_id=i) for x in incoming for i in (x.evidence_document_ids or [])]+[EvidenceRef("document",i,document_id=i) for x in field for i in (x.evidence_document_ids or [])]
    open_count=sum(x.status not in {"closed","resolved"} for x in incoming)+sum(x.status not in {"closed","resolved"} for x in field)
    actions=[normalize_action({"id":x.id,"domain":"supplier_field","type":"incoming_quality","title":f"{x.part_number}: {x.defect_code or 'incoming quality'}","reason":x.status,"priority":x.severity,"entity":{"type":"supplier","id":key}}) for x in incoming if x.status not in {"closed","resolved"}]
    return {"identity":{"type":"supplier","id":key,"label":next((x.supplier_name for x in incoming if x.supplier_name),key)},"summary":{"incoming_quality_records":len(incoming),"field_claims":len(field),"open_items":open_count},"sections":{"incoming_quality":[{"id":x.id,"code":x.code,"part_number":x.part_number,"revision":x.revision,"status":x.status,"severity":x.severity,"rejected_quantity":x.rejected_quantity} for x in incoming[:100]],"field_claims":[{"id":x.id,"claim_reference":x.claim_reference,"part_number":x.part_number,"failure_mode":x.failure_mode,"status":x.status,"severity":x.severity} for x in field[:100]]},"evidence":evidence_bundle(evid,require_document_visibility=visible_document_ids),"actions":actions[:20]}


def object360(
    db: Session,
    object_type: str,
    object_id: str,
    visible_document_ids: set[str],
    groups: list[str],
    runtime_features: set[str] | None = None,
) -> dict | None:
    kind=(object_type or "").strip().lower()
    if kind not in SUPPORTED_OBJECT_TYPES: return None
    if runtime_features is not None and kind not in set(available_object_types(runtime_features)):
        return None
    if kind == "vin":
        payload=_vin(db, object_id.strip(), visible_document_ids, groups, include_supplier_field=runtime_features is None or "supplier_field" in runtime_features)
    else:
        fn={"part":_part,"change":_change,"defect":_defect,"requirement":_requirement,"supplier":_supplier}[kind]
        payload=fn(db,object_id.strip(),visible_document_ids,groups)
    if payload is None: return None
    return {"schema":OBJECT360_SCHEMA,**payload,"governance":{"read_only_view":True,"acl_fail_closed":True,"profile_aware":runtime_features is not None,"source_systems_remain_authoritative":True}}
