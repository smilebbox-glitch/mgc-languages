from __future__ import annotations

from datetime import datetime, timezone
from typing import Iterable

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import BOMItem, ChangeRequest, DesignReview, Document, Part, Project, ProjectArea, ProjectMilestone, ValidationIssue
from app.services.manufacturing_areas import document_in_area, ensure_project_areas, serialize_area
from app.services.quality_core_tools import quality_workspace
from app.services.process_digital_thread import process_digital_thread
from app.services.launch_readiness import launch_readiness
from app.services.requirements_matrix import requirements_matrix
from app.services.supplier_localization import supplier_localization_workspace
from app.services.cost_economics import cost_economics_workspace
from app.services.vehicle_architecture import vehicle_architecture_workspace
from app.services.configuration_management import configuration_workspace
from app.services.release_baseline import release_workspace


TERMINAL_CHANGE = {"implemented", "rejected", "cancelled"}
APPROVED_REVIEW = {"approved"}


def project_allowed(project: Project, groups: Iterable[str]) -> bool:
    return bool(set(project.acl_groups or ["all"]) & set(list(groups) + ["all"]))


def _status_value(value) -> str:
    return value.value if hasattr(value, "value") else str(value)


def serialize_project(project: Project) -> dict:
    return {
        "id": project.id,
        "code": project.code,
        "name": project.name,
        "description": project.description,
        "status": project.status,
        "phase": project.phase,
        "owner": project.owner,
        "root_part_number": project.root_part_number,
        "target_release_at": project.target_release_at.isoformat() if project.target_release_at else None,
        "acl_groups": project.acl_groups or [],
        "metadata": project.metadata_json or {},
        "created_at": project.created_at.isoformat(),
        "updated_at": project.updated_at.isoformat() if project.updated_at else project.created_at.isoformat(),
    }


def serialize_milestone(m: ProjectMilestone) -> dict:
    return {
        "id": m.id, "project_code": m.project_code, "code": m.code, "name": m.name,
        "due_at": m.due_at.isoformat() if m.due_at else None, "status": m.status,
        "owner": m.owner, "gate": m.gate, "manufacturing_area": m.manufacturing_area, "notes": m.notes,
        "created_at": m.created_at.isoformat(), "updated_at": m.updated_at.isoformat() if m.updated_at else m.created_at.isoformat(),
    }


def _assembly_tree(rows: list[BOMItem], root: str | None, part_names: dict[str, str | None]) -> dict | None:
    if not root:
        return None
    children: dict[str, list[BOMItem]] = {}
    for row in rows:
        children.setdefault(row.parent_part_number, []).append(row)

    def walk(pn: str, depth: int, seen: set[str]) -> dict:
        node = {"part_number": pn, "name": part_names.get(pn), "children": []}
        if depth >= 6 or pn in seen:
            node["truncated"] = True
            return node
        nxt = seen | {pn}
        for row in sorted(children.get(pn, []), key=lambda x: x.child_part_number):
            child = walk(row.child_part_number, depth + 1, nxt)
            child["quantity"] = row.quantity
            child["revision"] = row.child_revision
            node["children"].append(child)
        return node

    return walk(root, 0, set())


def project_workspace(db: Session, project: Project, visible_document_ids: set[str], manufacturing_area: str | None = None, identity_groups: Iterable[str] | None = None) -> dict:
    areas = ensure_project_areas(db, project)
    allowed_groups = list(identity_groups or ["all"])
    allowed_area_codes = {a.code for a in areas if set(a.acl_groups or ["all"]) & set(allowed_groups + ["all"])}
    all_project_docs = [d for d in db.scalars(select(Document).where(Document.project_code == project.code)).all() if d.id in visible_document_ids and (not d.manufacturing_area or d.manufacturing_area in allowed_area_codes)]
    if manufacturing_area:
        explicit_parts = {d.part_number for d in all_project_docs if d.manufacturing_area == manufacturing_area and d.part_number}
        docs = [d for d in all_project_docs if d.manufacturing_area == manufacturing_area or (not d.manufacturing_area and (not d.part_number or d.part_number in explicit_parts or d.doc_type == "bom"))]
    else:
        docs = all_project_docs
    all_parts = db.scalars(select(Part).where(Part.project_code == project.code).order_by(Part.part_number)).all()
    # Document ACL remains stronger than project membership: a workspace never promotes
    # hidden document-derived part facts merely because the caller can see the project shell.
    part_numbers = {d.part_number for d in docs if d.part_number}
    parts = [p for p in all_parts if p.part_number in part_numbers]

    issues = db.scalars(select(ValidationIssue).order_by(ValidationIssue.created_at.desc())).all()
    issues = [i for i in issues if ((not i.document_ids and i.part_number in part_numbers) or (i.document_ids and bool(set(i.document_ids) & visible_document_ids)))]
    open_issues = [i for i in issues if _status_value(i.status) != "resolved"]

    changes = db.scalars(select(ChangeRequest).order_by(ChangeRequest.updated_at.desc())).all()
    changes = [c for c in changes if c.part_number in part_numbers]
    active_changes = [c for c in changes if c.status not in TERMINAL_CHANGE]

    reviews = db.scalars(select(DesignReview).order_by(DesignReview.updated_at.desc())).all()
    reviews = [r for r in reviews if r.part_number in part_numbers]
    latest_review_by_part: dict[str, DesignReview] = {}
    for review in reviews:
        latest_review_by_part.setdefault(review.part_number, review)

    milestones = db.scalars(select(ProjectMilestone).where(ProjectMilestone.project_code == project.code).order_by(ProjectMilestone.due_at, ProjectMilestone.code)).all()
    milestones = [m for m in milestones if not m.manufacturing_area or m.manufacturing_area in allowed_area_codes]
    if manufacturing_area:
        milestones = [m for m in milestones if not m.manufacturing_area or m.manufacturing_area == manufacturing_area]
    bom_rows = db.scalars(select(BOMItem)).all()
    bom_rows = [b for b in bom_rows if b.source_document_id in visible_document_ids and (b.parent_part_number in part_numbers or b.child_part_number in part_numbers)]

    # Documentation gate: coverage of drawing + deterministic CAD for each known project part.
    by_part: dict[str, set[str]] = {pn: set() for pn in part_numbers}
    for d in docs:
        if d.part_number:
            by_part.setdefault(d.part_number, set()).add(d.doc_type or "document")
    expected_pairs = max(len(part_numbers) * 2, 1)
    covered = sum((1 if "drawing" in kinds else 0) + (1 if "cad" in kinds else 0) for kinds in by_part.values())
    documentation_score = round(min(100.0, 100.0 * covered / expected_pairs), 1) if part_numbers else (100.0 if docs else 0.0)
    failed_docs = [d for d in docs if _status_value(d.status) == "failed"]

    critical = [i for i in open_issues if _status_value(i.severity) == "critical"]
    warnings = [i for i in open_issues if _status_value(i.severity) == "warning"]
    validation_quality_score = max(0.0, 100.0 - 30.0 * len(critical) - 5.0 * len(warnings))
    core_quality = quality_workspace(db, project.code, visible_document_ids, part_numbers, manufacturing_area, allowed_area_codes)
    process_thread = process_digital_thread(db, project.code, visible_document_ids, part_numbers, manufacturing_area, allowed_area_codes)
    launch = launch_readiness(db, project.code, visible_document_ids, part_numbers, manufacturing_area, allowed_area_codes, quality=core_quality, process=process_thread)
    requirements = requirements_matrix(db, project.code, visible_document_ids, part_numbers, manufacturing_area, allowed_area_codes)
    supplier_localization = supplier_localization_workspace(db, project.code, visible_document_ids, part_numbers, manufacturing_area, allowed_area_codes)
    cost_economics = cost_economics_workspace(db, project.code, visible_document_ids, part_numbers, manufacturing_area, allowed_area_codes)
    vehicle_architecture = vehicle_architecture_workspace(db, project.code, visible_document_ids, part_numbers, manufacturing_area, allowed_area_codes)
    configurations = configuration_workspace(db, project.code, visible_document_ids, part_numbers, manufacturing_area, allowed_area_codes)
    release_traceability = release_workspace(db, project.code, visible_document_ids, project.root_part_number, manufacturing_area)
    # Core Tools, Process Digital Thread and Launch Readiness are advisory and do not replace deterministic validation issues.
    quality_score = round(validation_quality_score * 0.45 + float(core_quality.get("score", 100.0)) * 0.55, 1)

    urgent = [c for c in active_changes if c.priority == "urgent" or c.risk_level == "critical"]
    high = [c for c in active_changes if c.priority == "high" or c.risk_level == "high"]
    change_score = max(0.0, 100.0 - 35.0 * len(urgent) - 15.0 * len(high) - 5.0 * max(0, len(active_changes) - len(urgent) - len(high)))

    review_candidates = [pn for pn in part_numbers if pn in by_part and by_part[pn] & {"cad", "drawing"}]
    approved_reviews = sum(1 for pn in review_candidates if pn in latest_review_by_part and _status_value(latest_review_by_part[pn].status) in APPROVED_REVIEW)
    review_score = round(100.0 * approved_reviews / max(len(review_candidates), 1), 1) if review_candidates else 100.0

    now = datetime.now(timezone.utc)
    overdue = [m for m in milestones if m.due_at and m.due_at.replace(tzinfo=m.due_at.tzinfo or timezone.utc) < now and m.status not in {"done", "waived"}]
    done = [m for m in milestones if m.status in {"done", "waived"}]
    milestone_score = round(100.0 * len(done) / max(len(milestones), 1), 1) if milestones else 100.0

    if requirements.get("configured") and launch.get("configured") and process_thread.get("configured"):
        score = round(
            documentation_score * 0.22 + quality_score * 0.18 + change_score * 0.13 + review_score * 0.07 + milestone_score * 0.06
            + float(process_thread.get("score", 0.0)) * 0.09 + float(launch.get("score", 0.0)) * 0.13 + float(requirements.get("score", 0.0)) * 0.12,
            1,
        )
    elif requirements.get("configured") and launch.get("configured"):
        score = round(
            documentation_score * 0.27 + quality_score * 0.18 + change_score * 0.14 + review_score * 0.08 + milestone_score * 0.08
            + float(launch.get("score", 0.0)) * 0.13 + float(requirements.get("score", 0.0)) * 0.12,
            1,
        )
    elif requirements.get("configured") and process_thread.get("configured"):
        score = round(
            documentation_score * 0.27 + quality_score * 0.20 + change_score * 0.15 + review_score * 0.08 + milestone_score * 0.08
            + float(process_thread.get("score", 0.0)) * 0.10 + float(requirements.get("score", 0.0)) * 0.12,
            1,
        )
    elif requirements.get("configured"):
        score = round(
            documentation_score * 0.31 + quality_score * 0.22 + change_score * 0.17 + review_score * 0.09 + milestone_score * 0.09
            + float(requirements.get("score", 0.0)) * 0.12,
            1,
        )
    elif launch.get("configured") and process_thread.get("configured"):
        score = round(
            documentation_score * 0.25 + quality_score * 0.20 + change_score * 0.15 + review_score * 0.08 + milestone_score * 0.07
            + float(process_thread.get("score", 0.0)) * 0.10 + float(launch.get("score", 0.0)) * 0.15,
            1,
        )
    elif launch.get("configured"):
        score = round(
            documentation_score * 0.30 + quality_score * 0.20 + change_score * 0.15 + review_score * 0.10 + milestone_score * 0.10
            + float(launch.get("score", 0.0)) * 0.15,
            1,
        )
    elif process_thread.get("configured"):
        score = round(
            documentation_score * 0.30 + quality_score * 0.23 + change_score * 0.18 + review_score * 0.10 + milestone_score * 0.09 + float(process_thread.get("score", 0.0)) * 0.10,
            1,
        )
    else:
        score = round(
            documentation_score * 0.35 + quality_score * 0.25 + change_score * 0.20 + review_score * 0.10 + milestone_score * 0.10,
            1,
        )

    # Supplier/localization readiness is advisory and enters the project score only after the team configures it.
    if supplier_localization.get("configured"):
        score = round(score * 0.90 + float(supplier_localization.get("score", 0.0)) * 0.10, 1)

    # Architecture/interface integrity is a technical advisory gate only after the team configures the architecture.
    if vehicle_architecture.get("configured"):
        score = round(score * 0.92 + float(vehicle_architecture.get("score", 0.0)) * 0.08, 1)

    # Variant/configuration coverage is advisory and only affects readiness after explicitly configured.
    if configurations.get("configured"):
        score = round(score * 0.95 + float(configurations.get("score", 0.0)) * 0.05, 1)

    blockers: list[dict] = []
    for i in critical[:20]:
        blockers.append({"type": "issue", "severity": "critical", "id": i.id, "part_number": i.part_number, "title": i.title})
    for d in failed_docs[:20]:
        blockers.append({"type": "document", "severity": "critical", "id": d.id, "part_number": d.part_number, "title": f"Ошибка обработки: {d.filename}"})
    for c in urgent[:20]:
        blockers.append({"type": "change", "severity": "critical", "id": c.id, "part_number": c.part_number, "title": f"Активное изменение {c.eco_code or c.code}: {c.title}"})
    for m in overdue[:20]:
        blockers.append({"type": "milestone", "severity": "warning", "id": m.id, "title": f"Просрочен этап: {m.name}"})
    for gap in core_quality.get("gaps", [])[:30]:
        blockers.append({"type": "quality", "severity": gap.get("severity", "warning"), "id": gap.get("id"), "part_number": gap.get("part_number"), "title": gap.get("title", "Quality Core Tools gap")})
    for gap in process_thread.get("gaps", [])[:30]:
        blockers.append({"type": "process", "severity": gap.get("severity", "warning"), "id": gap.get("id"), "part_number": gap.get("part_number"), "title": gap.get("title", "Process Digital Thread gap")})
    for gap in launch.get("gaps", [])[:30]:
        blockers.append({"type": "launch", "severity": gap.get("severity", "warning"), "id": gap.get("id"), "part_number": gap.get("part_number"), "title": gap.get("title", "Launch Readiness gap")})
    for gap in requirements.get("gaps", [])[:30]:
        blockers.append({"type": "requirement", "severity": gap.get("severity", "warning"), "id": gap.get("id"), "title": gap.get("title", "Requirements verification gap")})
    for gap in supplier_localization.get("gaps", [])[:30]:
        blockers.append({"type": "supplier", "severity": gap.get("severity", "warning"), "id": gap.get("id"), "part_number": gap.get("part_number"), "title": gap.get("title", "Supplier/localization gap")})
    for gap in vehicle_architecture.get("gaps", [])[:30]:
        blockers.append({"type": "architecture", "severity": gap.get("severity", "warning"), "id": gap.get("id"), "title": gap.get("title", "Vehicle/interface architecture gap")})
    for gap in configurations.get("gaps", [])[:30]:
        blockers.append({"type": "configuration", "severity": gap.get("severity", "warning"), "id": gap.get("id"), "title": gap.get("title", "Vehicle configuration gap")})
    if project.root_part_number and project.root_part_number not in part_numbers:
        blockers.append({"type": "project", "severity": "critical", "id": project.id, "title": "Корневая сборка проекта не найдена"})

    if any(b["severity"] == "critical" for b in blockers):
        readiness = "blocked"
    elif score < 85 or blockers:
        readiness = "needs_review"
    else:
        readiness = "candidate"

    # v6.3.34 Pilot Readiness: a bounded, evidence-backed action read-model.
    # It introduces no new authority or persistence; every item points back to
    # an existing engineering object and remains advisory/human-controlled.
    action_priority = {"critical": 0, "warning": 1, "high": 1, "medium": 2, "info": 3}
    action_route = {
        "issue": "checks", "document": "documents", "change": "changes",
        "milestone": "projects", "quality": "projects", "process": "projects",
        "launch": "projects", "requirement": "projects", "supplier": "projects",
        "architecture": "projects", "configuration": "projects", "project": "projects",
    }
    action_center = []
    for blocker in blockers:
        severity = str(blocker.get("severity") or "warning").lower()
        action_center.append({
            "id": f"{blocker.get('type','project')}:{blocker.get('id') or blocker.get('title','')}",
            "kind": blocker.get("type") or "project",
            "title": blocker.get("title") or "Требуется инженерная проверка",
            "reason": "Подтверждено текущим engineering readiness evidence",
            "severity": severity,
            "priority": action_priority.get(severity, 2),
            "part_number": blocker.get("part_number"),
            "object_id": blocker.get("id"),
            "route": action_route.get(blocker.get("type"), "projects"),
            "advisory_only": True,
            "human_decision_required": True,
        })
    # Stable ordering keeps the Action Center predictable between refreshes.
    action_center.sort(key=lambda x: (x["priority"], x["kind"], str(x["title"]), str(x["id"])))
    action_center = action_center[:12]

    area_summaries = []
    for area in areas:
        if not (set(area.acl_groups or ["all"]) & set(allowed_groups + ["all"])):
            continue
        explicit_parts = {d.part_number for d in all_project_docs if d.manufacturing_area == area.code and d.part_number}
        area_docs = [d for d in all_project_docs if d.manufacturing_area == area.code or (not d.manufacturing_area and (not d.part_number or d.part_number in explicit_parts or d.doc_type == "bom"))]
        area_doc_ids = {d.id for d in area_docs}
        area_parts = explicit_parts
        area_issues = [i for i in issues if ((i.part_number in area_parts) or (i.document_ids and bool(set(i.document_ids) & area_doc_ids))) and _status_value(i.status) != "resolved"]
        area_changes = [c for c in active_changes if c.part_number in area_parts]
        crit = sum(_status_value(i.severity) == "critical" for i in area_issues)
        warn = sum(_status_value(i.severity) == "warning" for i in area_issues)
        area_score = max(0.0, min(100.0, 100.0 - crit * 25.0 - warn * 4.0 - len(area_changes) * 5.0))
        item = serialize_area(area, allowed_groups)
        item["counts"] = {"documents": len(area_docs), "parts": len(area_parts), "open_issues": len(area_issues), "active_changes": len(area_changes)}
        item["health_score"] = round(area_score, 1)
        area_summaries.append(item)

    timeline = []
    for d in docs[:40]:
        timeline.append({"kind": "document", "at": d.updated_at.isoformat(), "title": d.filename, "status": _status_value(d.status), "id": d.id})
    for c in changes[:30]:
        timeline.append({"kind": "change", "at": c.updated_at.isoformat(), "title": c.eco_code or c.code, "status": c.status, "id": c.id})
    for r in reviews[:20]:
        timeline.append({"kind": "review", "at": r.updated_at.isoformat(), "title": f"Design Review {r.part_number} Rev {r.revision}", "status": _status_value(r.status), "id": r.id})
    for m in milestones:
        timeline.append({"kind": "milestone", "at": (m.updated_at or m.created_at).isoformat(), "title": m.name, "status": m.status, "id": m.id})
    for x in core_quality.get("apqp", [])[:20]:
        timeline.append({"kind": "quality", "at": x.get("updated_at") or x.get("created_at"), "title": f"APQP · {x.get('title')}", "status": x.get("status"), "id": x.get("id")})
    for x in core_quality.get("ppap", [])[:20]:
        timeline.append({"kind": "quality", "at": x.get("updated_at") or x.get("created_at"), "title": f"PPAP · {x.get('part_number')}", "status": x.get("status"), "id": x.get("id")})
    for x in core_quality.get("problems_8d", [])[:20]:
        timeline.append({"kind": "quality", "at": x.get("updated_at") or x.get("created_at"), "title": f"8D · {x.get('title')}", "status": x.get("status"), "id": x.get("id")})
    for x in process_thread.get("defects", [])[:20]:
        timeline.append({"kind": "process", "at": x.get("updated_at") or x.get("occurred_at"), "title": f"Процесс · {x.get('title')}", "status": x.get("status"), "id": x.get("id")})
    for x in launch.get("checks", [])[:20]:
        timeline.append({"kind": "launch", "at": x.get("updated_at") or x.get("created_at"), "title": f"Launch · {x.get('title')}", "status": x.get("status"), "id": x.get("id")})
    for x in launch.get("trials", [])[:20]:
        timeline.append({"kind": "launch", "at": x.get("updated_at") or x.get("planned_at"), "title": f"{x.get('trial_type')} · {x.get('title')}", "status": x.get("status"), "id": x.get("id")})
    for x in requirements.get("requirements", [])[:30]:
        timeline.append({"kind": "requirement", "at": x.get("updated_at") or x.get("created_at"), "title": f"Требование · {x.get('code')} · {x.get('title')}", "status": x.get("verification_state"), "id": x.get("id")})
        for v in (x.get("verifications") or [])[:5]:
            timeline.append({"kind": "requirement", "at": v.get("updated_at") or v.get("created_at"), "title": f"Verification · {v.get('code')} · {v.get('title')}", "status": v.get("status"), "id": v.get("id")})
    for x in supplier_localization.get("items", [])[:30]:
        timeline.append({"kind": "supplier", "at": x.get("updated_at") or x.get("created_at"), "title": f"Локализация · {x.get('part_number')} · {x.get('supplier_name')}", "status": x.get("status"), "id": x.get("id")})
    for x in supplier_localization.get("incoming_quality", [])[:20]:
        timeline.append({"kind": "supplier", "at": x.get("updated_at") or x.get("occurred_at"), "title": f"Входное качество · {x.get('code')} · {x.get('part_number')}", "status": x.get("status"), "id": x.get("id")})
    for x in cost_economics.get("baselines", [])[:20]:
        timeline.append({"kind": "cost", "at": x.get("updated_at") or x.get("created_at"), "title": f"Cost · {x.get('code')} · {x.get('name')}", "status": x.get("status"), "id": x.get("id")})
    for x in cost_economics.get("quotes", [])[:20]:
        timeline.append({"kind": "cost", "at": x.get("updated_at") or x.get("created_at"), "title": f"Quotation · {x.get('code')} · {x.get('part_number')}", "status": x.get("status"), "id": x.get("id")})
    for x in vehicle_architecture.get("interfaces", [])[:30]:
        timeline.append({"kind": "architecture", "at": x.get("updated_at") or x.get("created_at"), "title": f"Interface · {x.get('code')} · {x.get('name')}", "status": x.get("verification_state"), "id": x.get("id")})
    for x in configurations.get("variants", [])[:30]:
        timeline.append({"kind": "configuration", "at": x.get("updated_at") or x.get("created_at"), "title": f"Variant · {x.get('code')} · {x.get('name')}", "status": x.get("status"), "id": x.get("id")})
    for x in release_traceability.get("baselines", [])[:20]:
        timeline.append({"kind":"release","at":x.get("frozen_at"),"title":f"Baseline · {x.get('code')} · {x.get('name')}","status":"candidate" if x.get("release_candidate") else "needs_review","id":x.get("id")})
    timeline = [x for x in timeline if x.get("at")]
    timeline.sort(key=lambda x: x["at"], reverse=True)

    return {
        "project": serialize_project(project),
        "manufacturing_area": manufacturing_area,
        "readiness": {
            "score": score,
            "status": readiness,
            "advisory_only": True,
            "human_release_approval_required": True,
            "gates": {
                "documentation": documentation_score,
                "quality": round(quality_score, 1),
                "changes": round(change_score, 1),
                "design_reviews": review_score,
                "milestones": milestone_score,
                "process": round(float(process_thread.get("score", 0.0)), 1) if process_thread.get("configured") else None,
                "launch": round(float(launch.get("score", 0.0)), 1) if launch.get("configured") else None,
                "requirements": round(float(requirements.get("score", 0.0)), 1) if requirements.get("configured") else None,
                "suppliers": round(float(supplier_localization.get("score", 0.0)), 1) if supplier_localization.get("configured") else None,
                "architecture": round(float(vehicle_architecture.get("score", 0.0)), 1) if vehicle_architecture.get("configured") else None,
                "configurations": round(float(configurations.get("score", 0.0)), 1) if configurations.get("configured") else None,
            },
            "blockers": blockers,
            "quality_core_tools": {"score": core_quality.get("score"), "gates": core_quality.get("gates", {}), "counts": core_quality.get("counts", {})},
        },
        "action_center": {
            "items": action_center,
            "count": len(action_center),
            "critical_count": sum(x["severity"] == "critical" for x in action_center),
            "advisory_only": True,
            "human_decision_required": True,
            "source": "project_readiness_evidence",
        },
        "counts": {
            "parts": len(part_numbers), "documents": len(docs), "open_issues": len(open_issues),
            "critical_issues": len(critical), "active_changes": len(active_changes), "milestones": len(milestones),
            "process_operations": int(process_thread.get("counts", {}).get("operations", 0)),
            "launch_checks": int(launch.get("counts", {}).get("checks", 0)),
            "requirements": int(requirements.get("counts", {}).get("requirements", 0)),
            "localization_items": int(supplier_localization.get("counts", {}).get("localization_items", 0)),
            "suppliers": int(supplier_localization.get("counts", {}).get("suppliers", 0)),
            "cost_baselines": int(cost_economics.get("counts", {}).get("baselines", 0)),
            "cost_lines": int(cost_economics.get("counts", {}).get("lines", 0)),
            "architecture_nodes": int(vehicle_architecture.get("counts", {}).get("nodes", 0)),
            "interfaces": int(vehicle_architecture.get("counts", {}).get("interfaces", 0)),
            "vehicle_variants": int(configurations.get("counts", {}).get("variants", 0)),
            "configuration_links": int(configurations.get("counts", {}).get("applicability", 0)),
            "release_baselines": int(release_traceability.get("counts", {}).get("baselines", 0)),
            "bom_versions": int(release_traceability.get("counts", {}).get("bom_versions", 0)),
        },
        "parts": [{"part_number": p.part_number, "name": p.name, "latest_revision": p.latest_revision} for p in parts],
        "documents": [{"id": d.id, "filename": d.filename, "part_number": d.part_number, "revision": d.revision, "doc_type": d.doc_type, "status": _status_value(d.status), "updated_at": d.updated_at.isoformat()} for d in sorted(docs, key=lambda x: x.updated_at, reverse=True)[:100]],
        "issues": [{"id": i.id, "part_number": i.part_number, "severity": _status_value(i.severity), "status": _status_value(i.status), "title": i.title, "rule_code": i.rule_code} for i in open_issues[:100]],
        "changes": [{"id": c.id, "code": c.code, "eco_code": c.eco_code, "part_number": c.part_number, "title": c.title, "status": c.status, "priority": c.priority, "risk_level": c.risk_level} for c in active_changes[:100]],
        "milestones": [serialize_milestone(m) for m in milestones],
        "assembly_tree": _assembly_tree(bom_rows, project.root_part_number, {p.part_number: p.name for p in all_parts}),
        "timeline": timeline[:100],
        "areas": area_summaries,
        "area_focus": next((x.get("focus", []) for x in area_summaries if x.get("code") == manufacturing_area), []),
        "quality": core_quality,
        "process_thread": process_thread,
        "launch_readiness": launch,
        "requirements_matrix": requirements,
        "supplier_localization": supplier_localization,
        "cost_economics": cost_economics,
        "vehicle_architecture": vehicle_architecture,
        "configurations": configurations,
        "release_traceability": release_traceability,
    }
