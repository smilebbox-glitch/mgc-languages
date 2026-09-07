from __future__ import annotations

from datetime import timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import (
    ChangeRequest,
    DesignReview,
    Document,
    EngineeringRequirement,
    LaunchTrial,
    RequirementVerification,
    SpecialCharacteristic,
)

TERMINAL_CHANGE = {"implemented", "rejected", "cancelled"}
CRITICALITY = {"critical", "safety", "regulatory"}


def _dt(v):
    return v.isoformat() if v else None


def _in_area(area: str | None, requested: str | None, allowed: set[str] | None) -> bool:
    if area and allowed is not None and area not in allowed:
        return False
    if requested:
        return area in {None, requested}
    return True


def _aware(v):
    if v is None:
        return None
    return v if v.tzinfo else v.replace(tzinfo=timezone.utc)


def _visible_evidence(ids: list[str] | None, visible_document_ids: set[str]) -> list[str]:
    return [x for x in (ids or []) if x in visible_document_ids]


def serialize_requirement(req: EngineeringRequirement, visible_parts: set[str] | None = None, visible_characteristics: set[str] | None = None) -> dict:
    parts = list(req.part_numbers or [])
    chars = list(req.special_characteristic_ids or [])
    if visible_parts is not None:
        parts = [x for x in parts if x in visible_parts]
    if visible_characteristics is not None:
        chars = [x for x in chars if x in visible_characteristics]
    return {
        "id": req.id, "project_code": req.project_code, "manufacturing_area": req.manufacturing_area,
        "code": req.code, "category": req.category, "criticality": req.criticality, "title": req.title,
        "requirement_text": req.requirement_text, "source_document_id": req.source_document_id,
        "source_reference": req.source_reference or {}, "system_name": req.system_name, "function_name": req.function_name,
        "part_numbers": parts, "special_characteristic_ids": chars, "verification_method": req.verification_method,
        "acceptance_criteria": req.acceptance_criteria, "linked_change_ids": list(req.linked_change_ids or []),
        "status": req.status, "owner": req.owner, "created_by": req.created_by, "metadata": req.metadata_json or {},
        "created_at": _dt(req.created_at), "updated_at": _dt(req.updated_at),
    }


def _verification_proof(
    db: Session,
    verification: RequirementVerification,
    req: EngineeringRequirement,
    visible_document_ids: set[str],
    visible_parts: set[str],
) -> tuple[bool, bool, dict]:
    visible_evidence = _visible_evidence(verification.evidence_document_ids, visible_document_ids)
    launch_ok = False
    launch = None
    if verification.launch_trial_id:
        launch = db.get(LaunchTrial, verification.launch_trial_id)
        launch_ok = bool(
            launch and launch.project_code == req.project_code and launch.status == "passed"
            and (not launch.part_number or launch.part_number in visible_parts)
        )
    review_ok = False
    review = None
    if verification.design_review_id:
        review = db.get(DesignReview, verification.design_review_id)
        review_status = getattr(review.status, "value", review.status) if review else None
        review_ok = bool(review and review.part_number in visible_parts and review_status == "approved")

    proof_ok = bool(visible_evidence or launch_ok or review_ok)
    stale = False
    if verification.status == "passed":
        if not verification.requirement_updated_at_snapshot:
            stale = True
        elif _aware(req.updated_at) and _aware(verification.requirement_updated_at_snapshot) and _aware(req.updated_at) > _aware(verification.requirement_updated_at_snapshot):
            stale = True
        if req.source_document_id and verification.source_document_sha256_snapshot:
            source = db.get(Document, req.source_document_id)
            if not source or source.id not in visible_document_ids or source.sha256 != verification.source_document_sha256_snapshot:
                stale = True

    details = {
        "visible_evidence_document_ids": visible_evidence,
        "launch_trial_ok": launch_ok,
        "design_review_ok": review_ok,
        "proof_ok": proof_ok,
        "stale": stale,
    }
    return proof_ok, stale, details


def serialize_verification(
    db: Session,
    verification: RequirementVerification,
    req: EngineeringRequirement,
    visible_document_ids: set[str],
    visible_parts: set[str],
) -> dict:
    proof_ok, stale, details = _verification_proof(db, verification, req, visible_document_ids, visible_parts)
    effective_pass = verification.status == "passed" and proof_ok and not stale
    return {
        "id": verification.id, "project_code": verification.project_code, "requirement_id": verification.requirement_id,
        "manufacturing_area": verification.manufacturing_area, "code": verification.code,
        "verification_type": verification.verification_type, "phase": verification.phase, "title": verification.title,
        "status": verification.status, "effective_pass": effective_pass, "stale": stale,
        "result_summary": verification.result_summary, "measured_result": verification.measured_result_json or {},
        "evidence_document_ids": details["visible_evidence_document_ids"], "launch_trial_id": verification.launch_trial_id,
        "design_review_id": verification.design_review_id, "linked_change_id": verification.linked_change_id,
        "performed_by": verification.performed_by, "performed_at": _dt(verification.performed_at),
        "notes": verification.notes, "created_by": verification.created_by, "metadata": verification.metadata_json or {},
        "proof": details, "created_at": _dt(verification.created_at), "updated_at": _dt(verification.updated_at),
    }


def requirements_matrix(
    db: Session,
    project_code: str,
    visible_document_ids: set[str],
    visible_part_numbers: set[str],
    manufacturing_area: str | None = None,
    allowed_area_codes: set[str] | None = None,
) -> dict:
    chars = db.scalars(select(SpecialCharacteristic).where(SpecialCharacteristic.project_code == project_code)).all()
    visible_chars = {
        x.id for x in chars
        if _in_area(x.manufacturing_area, manufacturing_area, allowed_area_codes)
        and (not x.part_number or x.part_number in visible_part_numbers)
        and (not x.source_document_id or x.source_document_id in visible_document_ids)
    }

    all_requirements = db.scalars(select(EngineeringRequirement).where(EngineeringRequirement.project_code == project_code).order_by(EngineeringRequirement.code)).all()
    requirements: list[EngineeringRequirement] = []
    for req in all_requirements:
        if not _in_area(req.manufacturing_area, manufacturing_area, allowed_area_codes):
            continue
        if req.source_document_id and req.source_document_id not in visible_document_ids:
            continue
        req_parts = set(req.part_numbers or [])
        if req_parts and not (req_parts & visible_part_numbers):
            continue
        requirements.append(req)

    requirement_ids = {x.id for x in requirements}
    verifications = [
        x for x in db.scalars(select(RequirementVerification).where(RequirementVerification.project_code == project_code).order_by(RequirementVerification.code)).all()
        if x.requirement_id in requirement_ids and _in_area(x.manufacturing_area, manufacturing_area, allowed_area_codes)
    ]
    by_req: dict[str, list[RequirementVerification]] = {}
    for v in verifications:
        by_req.setdefault(v.requirement_id, []).append(v)

    rows = []
    gaps: list[dict] = []
    active = [r for r in requirements if r.status == "active"]
    source_ok_count = trace_ok_count = plan_ok_count = verified_count = 0

    for req in requirements:
        req_vs = by_req.get(req.id, [])
        serialized_vs = [serialize_verification(db, v, req, visible_document_ids, visible_part_numbers) for v in req_vs]
        effective = [v for v in serialized_vs if v["effective_pass"]]
        has_source = bool(req.source_document_id or (req.source_reference or {}))
        visible_parts = [x for x in (req.part_numbers or []) if x in visible_part_numbers]
        visible_req_chars = [x for x in (req.special_characteristic_ids or []) if x in visible_chars]
        has_trace = bool(req.system_name or req.function_name or visible_parts or visible_req_chars)
        has_plan = bool(req_vs)
        linked_changes = []
        for cid in req.linked_change_ids or []:
            c = db.get(ChangeRequest, cid)
            if c and c.part_number in visible_part_numbers:
                linked_changes.append({"id": c.id, "code": c.eco_code or c.code, "status": c.status, "part_number": c.part_number})
        open_changes = [x for x in linked_changes if x["status"] not in TERMINAL_CHANGE]

        if req.status == "active":
            source_ok_count += int(has_source)
            trace_ok_count += int(has_trace)
            plan_ok_count += int(has_plan)
            verified_count += int(bool(effective))
            sev = "critical" if req.criticality in CRITICALITY else "warning"
            if not has_source:
                gaps.append({"type": "requirement_source", "severity": sev, "id": req.id, "title": f"{req.code}: нет подтверждённого источника требования"})
            if not has_trace:
                gaps.append({"type": "requirement_trace", "severity": "warning", "id": req.id, "title": f"{req.code}: требование не связано с системой, функцией, деталью или характеристикой"})
            if not has_plan:
                gaps.append({"type": "verification_missing", "severity": sev, "id": req.id, "title": f"{req.code}: не задан способ подтверждения"})
            if has_plan and not effective:
                failed = any(v["status"] == "failed" for v in serialized_vs)
                stale = any(v["stale"] for v in serialized_vs if v["status"] == "passed")
                no_proof = any(v["status"] == "passed" and not v["proof"]["proof_ok"] for v in serialized_vs)
                if failed:
                    gaps.append({"type": "verification_failed", "severity": "critical", "id": req.id, "title": f"{req.code}: verification завершена с результатом FAILED"})
                elif stale:
                    gaps.append({"type": "verification_stale", "severity": sev, "id": req.id, "title": f"{req.code}: подтверждение устарело после изменения требования/источника"})
                elif no_proof:
                    gaps.append({"type": "verification_evidence", "severity": sev, "id": req.id, "title": f"{req.code}: статус PASSED не подтверждён доступным evidence"})
                else:
                    gaps.append({"type": "verification_pending", "severity": sev, "id": req.id, "title": f"{req.code}: требование ещё не подтверждено"})
            if open_changes:
                gaps.append({"type": "requirement_change", "severity": "warning", "id": req.id, "title": f"{req.code}: есть незавершённое связанное ECR/ECO"})

        rows.append({
            **serialize_requirement(req, visible_part_numbers, visible_chars),
            "verification_state": "verified" if effective else ("planned" if has_plan else "missing"),
            "verifications": serialized_vs,
            "linked_changes": linked_changes,
        })

    n = max(len(active), 1)
    source_score = round(100.0 * source_ok_count / n, 1) if active else 100.0
    trace_score = round(100.0 * trace_ok_count / n, 1) if active else 100.0
    plan_score = round(100.0 * plan_ok_count / n, 1) if active else 100.0
    verified_score = round(100.0 * verified_count / n, 1) if active else 100.0
    active_open_change_reqs = sum(1 for r in rows if r["status"] == "active" and any(c["status"] not in TERMINAL_CHANGE for c in r["linked_changes"]))
    change_score = max(0.0, 100.0 - 20.0 * active_open_change_reqs) if active else 100.0
    configured = bool(requirements)
    score = round(source_score * 0.15 + trace_score * 0.25 + plan_score * 0.20 + verified_score * 0.35 + change_score * 0.05, 1) if configured else 0.0
    status = "blocked" if any(x["severity"] == "critical" for x in gaps) else ("needs_review" if gaps or score < 90 else "verified")

    return {
        "configured": configured,
        "score": score,
        "status": status,
        "advisory_only": True,
        "compliance_certification": False,
        "gates": {
            "source": source_score if configured else None,
            "traceability": trace_score if configured else None,
            "verification_plan": plan_score if configured else None,
            "verification_result": verified_score if configured else None,
            "change_closure": change_score if configured else None,
        },
        "counts": {
            "requirements": len(requirements), "active": len(active), "verifications": len(verifications),
            "verified": verified_count, "gaps": len(gaps),
        },
        "requirements": rows,
        "gaps": gaps,
        "recommended_checks": [
            "У каждого требования есть источник и ссылка на конкретный раздел/пункт.",
            "Критические/регуляторные требования связаны с деталями, характеристиками и verification evidence.",
            "DV/PV или другой verification имеет фактический результат и доступное evidence.",
            "После ECR/ECO или изменения требования старое подтверждение пересмотрено.",
            "Матрица используется как traceability/evidence, а не как автоматический сертификат соответствия.",
        ],
    }
