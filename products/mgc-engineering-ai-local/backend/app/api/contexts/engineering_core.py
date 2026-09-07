"""Engineering Core HTTP handlers — v6.2.2.

Extracted from the former 3k-line route monolith. Public paths are unchanged.
"""
from fastapi import APIRouter, Request
from app.api import context_shared as _shared

# Preserve the mature shared handler namespace without duplicating service imports.
globals().update({k: v for k, v in vars(_shared).items() if not k.startswith("__")})
from app.api.lazy_service import lazy_service

analyze_drawing = lazy_service("app.services.drawing_intelligence", "analyze_drawing")
architecture_impact = lazy_service("app.services.vehicle_architecture", "architecture_impact")
area_allowed = lazy_service("app.services.manufacturing_areas", "area_allowed")
build_evidence_pack = lazy_service("app.services.evidence_pack", "build_evidence_pack")
compare_revisions = lazy_service("app.services.revision_compare", "compare_revisions")
configuration_impact = lazy_service("app.services.configuration_management", "configuration_impact")
cost_economics_workspace = lazy_service("app.services.cost_economics", "cost_economics_workspace")
document_activity_history = lazy_service("app.services.audit", "document_activity_history")
ensure_project_areas = lazy_service("app.services.manufacturing_areas", "ensure_project_areas")
ingest_document = lazy_service("app.services.ingest", "ingest_document")
inspect_drawing = lazy_service("app.services.drawing_vision", "inspect_drawing")
interface_fingerprint = lazy_service("app.services.vehicle_architecture", "interface_fingerprint")
link_drawing_document = lazy_service("app.services.geometry_linking", "link_drawing_document")
list_bom_versions = lazy_service("app.services.release_baseline", "list_bom_versions")
log_document_activity = lazy_service("app.services.audit", "log_document_activity")
log_event = lazy_service("app.services.audit", "log_event")
part_graph = lazy_service("app.services.knowledge", "part_graph")
program_control_workspace = lazy_service("app.services.program_control", "program_control_workspace")
project_allowed = lazy_service("app.services.project_workspace", "project_allowed")
project_workspace = lazy_service("app.services.project_workspace", "project_workspace")
requirements_matrix = lazy_service("app.services.requirements_matrix", "requirements_matrix")
run_design_review = lazy_service("app.services.design_review", "run_design_review")
scan_inbox = lazy_service("app.services.scanner", "scan_inbox")
serialize_area = lazy_service("app.services.manufacturing_areas", "serialize_area")
serialize_dependency = lazy_service("app.services.program_control", "serialize_dependency")
serialize_milestone = lazy_service("app.services.project_workspace", "serialize_milestone")
serialize_node = lazy_service("app.services.vehicle_architecture", "serialize_node")
serialize_project = lazy_service("app.services.project_workspace", "serialize_project")
serialize_requirement = lazy_service("app.services.requirements_matrix", "serialize_requirement")
serialize_verification = lazy_service("app.services.requirements_matrix", "serialize_verification")
simulate_milestone_slip = lazy_service("app.services.program_control", "simulate_milestone_slip")
valid_area = lazy_service("app.services.manufacturing_areas", "valid_area")
validate_part = lazy_service("app.services.validation", "validate_part")
vehicle_architecture_workspace = lazy_service("app.services.vehicle_architecture", "vehicle_architecture_workspace")
visible_program_rows = lazy_service("app.services.program_control", "visible_program_rows")
visible_project_areas = lazy_service("app.services.manufacturing_areas", "visible_project_areas")

from app.services.data_lifecycle import enforce_upload_quota
from app.services.background_jobs import create_job as create_compute_job, dispatch_job as dispatch_compute_job

router = APIRouter(tags=["context:engineering_core"])

@router.get("/documents")
def documents(manufacturing_area: str | None = None, identity: Identity = Depends(get_identity), db: Session = Depends(get_db)):
    if not valid_area(manufacturing_area): raise HTTPException(400, "Unknown manufacturing area")
    docs = db.scalars(select(Document).order_by(Document.created_at.desc())).all()
    return [serialize_doc(d) for d in _visible_docs_for_area(db, identity, manufacturing_area)]

@router.get("/documents/{document_id}")
def document(document_id: str, identity: Identity = Depends(get_identity), db: Session = Depends(get_db)):
    doc = db.get(Document, document_id)
    if not doc or not _allowed(doc, identity): raise HTTPException(404)
    log_document_activity(db, doc.id, identity.user, "DOCUMENT_OPEN", "Открыт документ", {"filename": doc.filename})
    return serialize_doc(doc)



@router.get("/documents/{document_id}/content")
def document_content(document_id: str, inline: bool = False, identity: Identity = Depends(get_identity), db: Session = Depends(get_db)):
    doc = db.get(Document, document_id)
    if not doc or not _allowed(doc, identity):
        raise HTTPException(404)
    if doc.project_code:
        project = db.scalar(select(Project).where(Project.code == doc.project_code))
        if not project or not project_allowed(project, identity.groups):
            raise HTTPException(404)
        if doc.manufacturing_area:
            ensure_project_areas(db, project)
            area = db.scalar(select(ProjectArea).where(ProjectArea.project_code == project.code, ProjectArea.code == doc.manufacturing_area))
            if not area or not area_allowed(area, identity.groups):
                raise HTTPException(404)
    path = Path(doc.stored_path)
    if not path.exists():
        raise HTTPException(404)
    log_document_activity(db, doc.id, identity.user, "DOCUMENT_CONTENT_OPEN", "Открыт исходный файл", {"filename": doc.filename})
    return FileResponse(path, media_type=doc.mime_type or "application/octet-stream", headers={"Content-Disposition": "inline"}) if inline else FileResponse(path, media_type=doc.mime_type or "application/octet-stream", filename=doc.filename)

@router.post("/documents/upload")
def upload(
    file: UploadFile = File(...), part_number: str | None = Form(default=None), revision: str | None = Form(default=None),
    project_code: str | None = Form(default=None), manufacturing_area: str | None = Form(default=None), doc_type: str | None = Form(default=None),
    acl_groups: str = Form(default="all"),
    identity: Identity = Depends(get_identity), db: Session = Depends(get_db),
):
    if not valid_area(manufacturing_area): raise HTTPException(400, "Unknown manufacturing area")
    if project_code and manufacturing_area:
        project = db.scalar(select(Project).where(Project.code == project_code.upper()))
        if project and project_allowed(project, identity.groups):
            ensure_project_areas(db, project)
            area = db.scalar(select(ProjectArea).where(ProjectArea.project_code == project.code, ProjectArea.code == manufacturing_area))
            if not area or not area_allowed(area, identity.groups): raise HTTPException(403, "No access to manufacturing area")
    cfg = get_settings(); safe_name = Path(file.filename or "upload.bin").name; suffix = Path(safe_name).suffix.lower()
    target_dir = cfg.storage_dir / "uploads"; target_dir.mkdir(parents=True, exist_ok=True)
    temp = target_dir / ("incoming_" + safe_name); sha = hashlib.sha256(); size = 0
    with temp.open("wb") as out:
        while chunk := file.file.read(1024 * 1024):
            size += len(chunk)
            if size > cfg.max_upload_mb * 1024 * 1024:
                out.close(); temp.unlink(missing_ok=True); raise HTTPException(413, f"File exceeds {cfg.max_upload_mb} MB")
            sha.update(chunk); out.write(chunk)
    digest = sha.hexdigest()
    try:
        enforce_upload_quota(db, project_code=project_code, manufacturing_area=manufacturing_area, incoming_bytes=size)
    except PermissionError as exc:
        temp.unlink(missing_ok=True)
        raise HTTPException(507, str(exc))
    groups = sorted({g.strip() for g in acl_groups.split(",") if g.strip()} or {"all"})
    requested_pn = part_number.upper() if part_number else None
    requested_rev = revision.upper() if revision else None
    candidates = db.scalars(select(Document).where(Document.sha256 == digest).order_by(Document.created_at.desc())).all()
    duplicate = next((d for d in candidates if _allowed(d, identity) and sorted(d.acl_groups or ["all"]) == groups and (requested_pn is None or d.part_number == requested_pn) and (requested_rev is None or d.revision == requested_rev) and (project_code is None or d.project_code == project_code) and (manufacturing_area is None or d.manufacturing_area == manufacturing_area)), None)
    if duplicate:
        temp.unlink(missing_ok=True)
        return {**serialize_doc(duplicate), "duplicate": True}
    final = target_dir / f"{digest[:16]}_{safe_name}"
    if final.exists():
        temp.unlink(missing_ok=True)
    else:
        shutil.move(str(temp), str(final))
    doc = Document(filename=safe_name, stored_path=str(final), mime_type=file.content_type or mimetypes.guess_type(safe_name)[0] or "application/octet-stream",
                   extension=suffix, size_bytes=size, sha256=digest, part_number=requested_pn, doc_type=doc_type,
                   revision=requested_rev, project_code=project_code, manufacturing_area=manufacturing_area, acl_groups=groups)
    db.add(doc); db.commit(); db.refresh(doc)
    log_event(db, identity.user, "DOCUMENT_UPLOAD", "document", doc.id, {"filename": safe_name, "sha256": digest, "project": project_code, "manufacturing_area": manufacturing_area})
    log_document_activity(db, doc.id, identity.user, "DOCUMENT_UPLOAD", "Документ загружен", {"filename": safe_name, "sha256": digest, "project": project_code, "manufacturing_area": manufacturing_area})
    compute_job = None
    if cfg.async_ingest:
        try:
            compute_job = create_compute_job(
                db, user=identity.user, kind="document_ingest", project_code=doc.project_code,
                manufacturing_area=doc.manufacturing_area, request_json={"document_id": doc.id},
            )
            task = dispatch_compute_job(compute_job)
            compute_job.celery_task_id = task.id
            db.commit()
        except Exception:
            # Preserve legacy resilience: if the broker is unavailable, process synchronously.
            if compute_job:
                compute_job.status = "failure"
                compute_job.error = "Background dispatch unavailable; synchronous fallback used"
                db.commit()
            ingest_document(db, doc)
    else:
        ingest_document(db, doc)
    db.refresh(doc)
    payload = serialize_doc(doc)
    if compute_job:
        payload["compute_job_id"] = compute_job.id
    return payload

@router.post("/documents/{document_id}/reindex")
def reindex(document_id: str, identity: Identity = Depends(get_identity), db: Session = Depends(get_db)):
    doc = db.get(Document, document_id)
    if not doc or not _allowed(doc, identity): raise HTTPException(404)
    ingest_document(db, doc); log_event(db, identity.user, "DOCUMENT_REINDEX", "document", doc.id)
    log_document_activity(db, doc.id, identity.user, "DOCUMENT_REINDEX", "Документ переиндексирован")
    return serialize_doc(doc)

@router.get("/documents/{document_id}/preview")
def preview(document_id: str, identity: Identity = Depends(get_identity), db: Session = Depends(get_db)):
    doc = db.get(Document, document_id)
    if not doc or not _allowed(doc, identity) or not doc.preview_path: raise HTTPException(404)
    path = Path(doc.preview_path)
    if not path.exists(): raise HTTPException(404)
    log_document_activity(db, doc.id, identity.user, "PREVIEW_OPEN", "Открыт 3D-просмотр")
    return FileResponse(path, media_type="model/stl", filename=path.name)

@router.get("/parts")
def parts(manufacturing_area: str | None = None, identity: Identity = Depends(get_identity), db: Session = Depends(get_db)):
    if not valid_area(manufacturing_area): raise HTTPException(400, "Unknown manufacturing area")
    visible_docs = _visible_docs_for_area(db, identity, manufacturing_area)
    by_part: dict[str, list[Document]] = {}
    for d in visible_docs:
        if d.part_number:
            by_part.setdefault(d.part_number, []).append(d)
    rows = db.scalars(select(Part).where(Part.part_number.in_(set(by_part))).order_by(Part.updated_at.desc())).all() if by_part else []
    result = []
    for p in rows:
        docs = by_part.get(p.part_number, [])
        visible_revs = [d.revision for d in docs if d.revision]
        result.append({"part_number": p.part_number, "name": p.name, "project_code": p.project_code,
                       "latest_revision": max(visible_revs) if visible_revs else None, "manufacturing_areas": sorted({d.manufacturing_area for d in docs if d.manufacturing_area}), "metadata": _merge_visible_metadata(docs)})
    return result

@router.get("/parts/{part_number}")
def part_360(part_number: str, manufacturing_area: str | None = None, identity: Identity = Depends(get_identity), db: Session = Depends(get_db)):
    pn = part_number.upper(); part = db.scalar(select(Part).where(Part.part_number == pn))
    if not part: raise HTTPException(404)
    docs = [d for d in db.scalars(select(Document).where(Document.part_number == pn).order_by(Document.created_at.desc())).all() if _allowed(d, identity)]
    if manufacturing_area:
        area_specific = [d for d in docs if d.manufacturing_area == manufacturing_area]
        if not area_specific: raise HTTPException(404)
        docs = area_specific + [d for d in docs if not d.manufacturing_area]
    if not docs: raise HTTPException(404)
    visible_doc_ids = {d.id for d in docs}
    rev_rows = db.scalars(select(PartRevision).where(PartRevision.part_number == pn).order_by(PartRevision.revision)).all()
    revisions = []
    for r in rev_rows:
        rdocs = [d for d in docs if d.revision == r.revision]
        if not rdocs:
            continue
        revisions.append({"revision": r.revision, "metadata": _merge_visible_metadata(rdocs), "document_ids": [d.id for d in rdocs]})
    bom = db.scalars(select(BOMItem).where(BOMItem.parent_part_number == pn)).all()
    bom = [x for x in bom if x.source_document_id in visible_doc_ids]
    issues = db.scalars(select(ValidationIssue).where(ValidationIssue.part_number == pn).order_by(ValidationIssue.created_at.desc())).all()
    issues = [i for i in issues if not i.document_ids or bool(set(i.document_ids) & visible_doc_ids)]
    changes = db.scalars(select(ChangeRequest).where(ChangeRequest.part_number == pn).order_by(ChangeRequest.updated_at.desc())).all()
    visible_revs = [d.revision for d in docs if d.revision]
    part_cost = cost_economics_workspace(db, part.project_code, visible_doc_ids, {pn}, manufacturing_area, {d.manufacturing_area for d in docs if d.manufacturing_area}) if part.project_code else {"configured": False}
    part_architecture = {"part_number": pn, "architecture_nodes": [], "connected_interfaces": [], "adjacent_nodes": [], "requirement_ids": [], "open_changes": [], "cost_line_ids": [], "localization_item_ids": [], "impact_count": 0, "advisory_only": True}
    part_configuration = {"part_number": pn, "affected_variants": [], "excluded_variants": [], "unknown_variants": [], "applicability_resolved": False, "advisory_only": True, "unknown_is_not_included": True}
    if part.project_code:
        try:
            ap, adoc_ids, aparts, aareas = _architecture_context(db, part.project_code, identity, manufacturing_area)
            if pn in aparts:
                part_architecture = architecture_impact(db, ap.code, pn, adoc_ids, aparts, manufacturing_area, aareas)
                part_configuration = configuration_impact(db, ap.code, pn, adoc_ids, aparts, manufacturing_area, aareas)
        except HTTPException:
            pass
    return {
        "part": {"part_number": part.part_number, "name": part.name, "latest_revision": max(visible_revs) if visible_revs else None, "project_code": part.project_code, "manufacturing_areas": sorted({d.manufacturing_area for d in docs if d.manufacturing_area}), "metadata": _merge_visible_metadata(docs)},
        "revisions": revisions,
        "documents": [serialize_doc(d) for d in docs],
        "bom": [{"child_part_number": x.child_part_number, "child_revision": x.child_revision, "quantity": x.quantity, "unit": x.unit, "description": x.description, "position": x.position, "supplier_code": x.supplier_code, "supplier_name": x.supplier_name, "unit_cost": x.unit_cost, "currency": x.currency, "source_document_id": x.source_document_id} for x in bom],
        "bom_versions": list_bom_versions(db, part.project_code, _visible_ids(db, identity), pn) if part.project_code else [],
        "issues": [{"id": i.id, "severity": i.severity.value, "status": i.status.value, "rule_code": i.rule_code, "title": i.title, "details": i.details} for i in issues],
        "changes": [{"id": c.id, "code": c.code, "eco_code": c.eco_code, "title": c.title, "from_revision": c.from_revision, "to_revision": c.to_revision, "status": c.status, "risk_level": c.risk_level, "updated_at": c.updated_at.isoformat()} for c in changes],
        "cost_economics": part_cost,
        "architecture_impact": part_architecture,
        "configuration_impact": part_configuration,
    }

@router.get("/parts/{part_number}/graph")
def graph(part_number: str, manufacturing_area: str | None = None, identity: Identity = Depends(get_identity), db: Session = Depends(get_db)):
    visible_doc_ids = {d.id for d in _visible_docs_for_area(db, identity, manufacturing_area)}
    return part_graph(db, part_number.upper(), visible_doc_ids)

@router.get("/parts/{part_number}/compare")
def compare(part_number: str, left: str, right: str, identity: Identity = Depends(get_identity), db: Session = Depends(get_db)):
    visible_doc_ids = _visible_ids(db, identity)
    result = compare_revisions(db, part_number.upper(), left.upper(), right.upper(), visible_doc_ids)
    log_event(db, identity.user, "REVISION_COMPARE", "part", part_number.upper(), {"left": left, "right": right})
    return result

@router.post("/parts/{part_number}/validate")
def validate(part_number: str, identity: Identity = Depends(get_identity), db: Session = Depends(get_db)):
    visible_doc_ids = _visible_ids(db, identity)
    issues = validate_part(db, part_number.upper(), visible_doc_ids)
    log_event(db, identity.user, "VALIDATE_PART", "part", part_number.upper(), {"issues": len(issues)})
    return [{"id": i.id, "severity": i.severity.value, "status": i.status.value, "rule_code": i.rule_code, "title": i.title, "details": i.details, "document_ids": i.document_ids} for i in issues]

@router.get("/issues")
def issues(manufacturing_area: str | None = None, identity: Identity = Depends(get_identity), db: Session = Depends(get_db)):
    if not valid_area(manufacturing_area): raise HTTPException(400, "Unknown manufacturing area")
    area_docs = _visible_docs_for_area(db, identity, manufacturing_area)
    visible_doc_ids = {d.id for d in area_docs}
    visible_parts = {d.part_number for d in area_docs if d.part_number}
    rows = db.scalars(select(ValidationIssue).order_by(ValidationIssue.created_at.desc())).all()
    rows = [i for i in rows if (i.document_ids and bool(set(i.document_ids) & visible_doc_ids)) or (not i.document_ids and (not manufacturing_area or i.part_number in visible_parts))]
    return [{"id": i.id, "part_number": i.part_number, "revision": i.revision, "severity": i.severity.value, "status": i.status.value, "rule_code": i.rule_code, "title": i.title, "details": i.details, "document_ids": i.document_ids, "created_at": i.created_at.isoformat()} for i in rows]

@router.patch("/issues/{issue_id}")
def update_issue(issue_id: str, req: IssueUpdate, identity: Identity = Depends(get_identity), db: Session = Depends(get_db)):
    issue = db.get(ValidationIssue, issue_id)
    if not issue: raise HTTPException(404)
    visible_doc_ids = _visible_ids(db, identity)
    if issue.document_ids and not bool(set(issue.document_ids) & visible_doc_ids):
        raise HTTPException(404)
    allowed = {"open", "acknowledged", "resolved"}
    if req.status not in allowed: raise HTTPException(400, f"status must be one of {sorted(allowed)}")
    issue.status = req.status; db.commit(); log_event(db, identity.user, "ISSUE_STATUS", "issue", issue.id, {"status": req.status})
    for document_id in issue.document_ids or []:
        if document_id in visible_doc_ids:
            log_document_activity(db, document_id, identity.user, "ISSUE_STATUS", f"Статус замечания изменён: {req.status}", {"issue_id": issue.id, "rule_code": issue.rule_code})
    return {"id": issue.id, "status": issue.status.value if hasattr(issue.status, "value") else issue.status}

@router.post("/scanner/run")
def scanner_run(project_code: str | None = None, identity: Identity = Depends(get_identity), db: Session = Depends(get_db)):
    if not _is_admin(identity): raise HTTPException(403, "Admin group required")
    result = scan_inbox(db, identity.groups, project_code)
    log_event(db, identity.user, "INBOX_SCAN", details=result)
    return result

@router.post("/design-reviews")
def create_design_review(req: DesignReviewRequest, identity: Identity = Depends(get_identity), db: Session = Depends(get_db)):
    try:
        review = run_design_review(db, req.part_number, req.revision, req.baseline_revision, identity.user, _visible_ids(db, identity))
    except ValueError as exc:
        raise HTTPException(404, str(exc))
    log_event(db, identity.user, "DESIGN_REVIEW", "part", req.part_number.upper(), {"review_id": review.id, "revision": req.revision})
    for document_id in review.evidence_document_ids or []:
        log_document_activity(db, document_id, identity.user, "DESIGN_REVIEW", "Документ использован в полной проверке конструкции", {"review_id": review.id, "part_number": review.part_number, "revision": review.revision, "risk_score": review.risk_score})
    return {"id": review.id, "part_number": review.part_number, "revision": review.revision, "baseline_revision": review.baseline_revision, "status": review.status.value, "risk_score": review.risk_score, "summary": review.summary, "findings": review.findings, "evidence_document_ids": review.evidence_document_ids, "report": review.report_json}

@router.post("/design-reviews/async")
def create_design_review_async(req: DesignReviewRequest, identity: Identity = Depends(get_identity), db: Session = Depends(get_db)):
    visible = sorted(_visible_ids(db, identity))
    target = db.scalar(select(PartRevision).where(PartRevision.part_number == req.part_number.upper(), PartRevision.revision == req.revision.upper()))
    if not target:
        raise HTTPException(404, "Target revision not found")
    visible_target = db.scalar(select(func.count(Document.id)).where(Document.id.in_(visible), Document.part_number == req.part_number.upper(), Document.revision == req.revision.upper())) if visible else 0
    if not visible_target:
        raise HTTPException(404, "Target revision is not visible to the current identity")
    target_docs = db.scalars(select(Document).where(
        Document.id.in_(visible), Document.part_number == req.part_number.upper(), Document.revision == req.revision.upper()
    )).all() if visible else []
    projects = sorted({d.project_code for d in target_docs if d.project_code})
    project_code = projects[0] if len(projects) == 1 else None
    job = create_compute_job(
        db, user=identity.user, kind="design_review", project_code=project_code,
        request_json={
            "part_number": req.part_number.upper(), "revision": req.revision.upper(),
            "baseline_revision": req.baseline_revision, "allowed_document_ids": visible,
        },
    )
    task = dispatch_compute_job(job)
    job.celery_task_id = task.id; db.commit()
    log_event(db, identity.user, "DESIGN_REVIEW_QUEUED", "part", req.part_number.upper(), {"job_id": job.id, "revision": req.revision, "resource_class": job.resource_class})
    return {"job_id": job.id, "state": "queued", "queue": job.queue, "resource_class": job.resource_class, "priority": job.priority, "message": "Полная проверка поставлена в очередь"}

@router.get("/design-reviews")
def list_design_reviews(identity: Identity = Depends(get_identity), db: Session = Depends(get_db)):
    visible_docs = _visible_docs(db, identity)
    visible = {d.part_number for d in visible_docs if d.part_number}
    visible_doc_ids = {d.id for d in visible_docs}
    rows = db.scalars(select(DesignReview).order_by(DesignReview.created_at.desc())).all()
    rows = [r for r in rows if r.part_number in visible and set(r.evidence_document_ids or []).issubset(visible_doc_ids)]
    return [{"id": r.id, "part_number": r.part_number, "revision": r.revision, "baseline_revision": r.baseline_revision, "status": r.status.value, "risk_score": r.risk_score, "summary": r.summary, "findings": r.findings, "report": r.report_json, "created_at": r.created_at.isoformat()} for r in rows]

@router.post("/design-reviews/{review_id}/approve")
def approve_design_review(review_id: str, req: ApprovalRequest, identity: Identity = Depends(get_identity), db: Session = Depends(get_db)):
    review = db.get(DesignReview, review_id)
    if not review:
        raise HTTPException(404)
    visible_doc_ids = _visible_ids(db, identity)
    if not set(review.evidence_document_ids or []).issubset(visible_doc_ids):
        raise HTTPException(404)
    if req.decision not in {"approved", "rejected"}:
        raise HTTPException(400, "decision must be approved or rejected")
    approval = ReviewApproval(review_id=review.id, approver=identity.user, decision=req.decision, comment=req.comment)
    review.status = ReviewStatus.approved if req.decision == "approved" else ReviewStatus.rejected
    db.add(approval); db.commit()
    log_event(db, identity.user, "DESIGN_REVIEW_DECISION", "design_review", review.id, {"decision": req.decision})
    for document_id in review.evidence_document_ids or []:
        if document_id in visible_doc_ids:
            log_document_activity(db, document_id, identity.user, "DESIGN_REVIEW_DECISION", f"Решение по Design Review: {req.decision}", {"review_id": review.id, "comment": req.comment})
    return {"review_id": review.id, "status": review.status.value, "approver": identity.user}

@router.post("/evidence-packs")
def evidence_pack(req: EvidencePackRequest, identity: Identity = Depends(get_identity), db: Session = Depends(get_db)):
    try:
        pack = build_evidence_pack(db, req.part_number, req.revision, identity.user, req.pack_type, _visible_ids(db, identity))
    except ValueError as exc:
        raise HTTPException(404, str(exc))
    log_event(db, identity.user, "EVIDENCE_PACK", "part", req.part_number.upper(), {"pack_id": pack.id, "type": req.pack_type})
    return {"id": pack.id, "pack_type": pack.pack_type, "part_number": pack.part_number, "revision": pack.revision, "status": pack.status, "manifest": pack.manifest, "created_at": pack.created_at.isoformat()}

@router.get("/evidence-packs/{pack_id}")
def get_evidence_pack(pack_id: str, identity: Identity = Depends(get_identity), db: Session = Depends(get_db)):
    pack = db.get(EvidencePack, pack_id)
    if not pack:
        raise HTTPException(404)
    visible_doc_ids = _visible_ids(db, identity)
    pack_doc_ids = {d.get("id") for d in (pack.manifest or {}).get("documents", []) if d.get("id")}
    if not pack_doc_ids.issubset(visible_doc_ids):
        raise HTTPException(404)
    return {"id": pack.id, "pack_type": pack.pack_type, "part_number": pack.part_number, "revision": pack.revision, "status": pack.status, "manifest": pack.manifest, "created_at": pack.created_at.isoformat()}

@router.get("/documents/{document_id}/history")
def document_history(document_id: str, limit: int = 200, identity: Identity = Depends(get_identity), db: Session = Depends(get_db)):
    doc = db.get(Document, document_id)
    if not doc or not _allowed(doc, identity):
        raise HTTPException(404)
    rows, integrity_valid = document_activity_history(db, doc.id, limit)
    return {
        "document_id": doc.id,
        "filename": doc.filename,
        "integrity_valid": integrity_valid,
        "events": [{
            "id": x.id, "user": x.user, "action": x.action, "summary": x.summary, "details": x.details,
            "previous_hash": x.previous_hash, "event_hash": x.event_hash, "created_at": x.created_at.isoformat(),
        } for x in rows],
    }

@router.post("/documents/{document_id}/history/note")
def add_document_history_note(document_id: str, req: DocumentActivityNoteRequest, identity: Identity = Depends(get_identity), db: Session = Depends(get_db)):
    doc = db.get(Document, document_id)
    if not doc or not _allowed(doc, identity):
        raise HTTPException(404)
    row = log_document_activity(db, doc.id, identity.user, "ENGINEER_NOTE", req.summary, {"category": req.category, **(req.details or {})})
    return {"id": row.id, "user": row.user, "action": row.action, "summary": row.summary, "details": row.details, "event_hash": row.event_hash, "created_at": row.created_at.isoformat()}

@router.get("/documents/{document_id}/engineering-analysis")
def engineering_analysis(document_id: str, identity: Identity = Depends(get_identity), db: Session = Depends(get_db)):
    doc = db.get(Document, document_id)
    if not doc or not _allowed(doc, identity):
        raise HTTPException(404)
    meta = doc.extracted_metadata or {}
    return {
        "document_id": doc.id,
        "filename": doc.filename,
        "doc_type": doc.doc_type,
        "geometry": {k: v for k, v in meta.items() if k in {
            "cad_kernel", "geometry_authority", "units", "solid_count", "shell_count", "wire_count",
            "face_count", "edge_count", "vertex_count", "volume_mm3", "surface_area_mm2", "center_of_mass_mm",
            "bounding_box_mm", "surface_types", "edge_types", "cylindrical_radii_mm", "cylindrical_diameters_mm",
            "candidate_cylindrical_feature_diameters_mm", "bbox_ratios", "compactness", "thin_part_candidate",
            "bbox_min_thickness_candidate_mm", "step_semantics", "geometry_features", "geometry_edge_features",
        }},
        "drawing": meta.get("engineering_drawing"),
        "vision": meta.get("vision_inspection"),
        "geometry_links": meta.get("geometry_links"),
    }

@router.post("/documents/{document_id}/engineering-analyze")
def rerun_engineering_analysis(document_id: str, identity: Identity = Depends(get_identity), db: Session = Depends(get_db)):
    doc = db.get(Document, document_id)
    if not doc or not _allowed(doc, identity):
        raise HTTPException(404)
    path = Path(doc.stored_path)
    if path.suffix.lower() not in {".pdf", ".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tif", ".tiff"}:
        raise HTTPException(400, "Deterministic drawing analysis supports PDF and image drawings")
    from app.services.document_parser import parse_document
    try:
        text, _ = parse_document(path)
        analysis = analyze_drawing(path, text, max_pages=get_settings().drawing_max_pages)
    except Exception as exc:
        raise HTTPException(422, f"Engineering analysis failed: {type(exc).__name__}: {exc}")
    doc.extracted_metadata = {**(doc.extracted_metadata or {}), "engineering_drawing": analysis}
    db.commit(); db.refresh(doc)
    log_event(db, identity.user, "ENGINEERING_DRAWING_ANALYSIS", "document", doc.id, {"entities": len(analysis.get("entities", []))})
    log_document_activity(db, doc.id, identity.user, "DRAWING_ANALYSIS", "Чертёж разобран: извлечены размеры и обозначения", {"entities": len(analysis.get("entities", [])), "method": analysis.get("source_method")})
    return analysis

@router.get("/documents/{document_id}/geometry-links")
def geometry_links(document_id: str, identity: Identity = Depends(get_identity), db: Session = Depends(get_db)):
    doc = db.get(Document, document_id)
    if not doc or not _allowed(doc, identity):
        raise HTTPException(404)
    return (doc.extracted_metadata or {}).get("geometry_links") or {
        "status": "not_run", "drawing_document_id": doc.id, "links": []
    }

@router.post("/documents/{document_id}/link-geometry")
def link_geometry(document_id: str, cad_document_id: str | None = None, identity: Identity = Depends(get_identity), db: Session = Depends(get_db)):
    doc = db.get(Document, document_id)
    if not doc or not _allowed(doc, identity):
        raise HTTPException(404)
    result = link_drawing_document(
        db, doc, cad_document_id=cad_document_id, allowed_document_ids=_visible_ids(db, identity), persist=True
    )
    event_details = {
        "status": result.get("status"),
        "cad_document_id": result.get("cad_document_id"),
        "linked_unique": result.get("linked_unique", 0),
        "linked_multiple": result.get("linked_multiple", 0),
        "unmatched": result.get("unmatched", 0),
    }
    log_event(db, identity.user, "DRAWING_CAD_LINK", "document", doc.id, event_details)
    log_document_activity(db, doc.id, identity.user, "DRAWING_CAD_LINK", "Размеры чертежа сопоставлены с 3D-геометрией", event_details)
    return result

@router.post("/documents/{document_id}/visual-inspect")
async def visual_inspect(document_id: str, max_pages: int = 3, identity: Identity = Depends(get_identity), db: Session = Depends(get_db)):
    doc = db.get(Document, document_id)
    if not doc or not _allowed(doc, identity):
        raise HTTPException(404)
    deterministic = (doc.extracted_metadata or {}).get("engineering_drawing") or {}
    try:
        result = await inspect_drawing(Path(doc.stored_path), max_pages=max_pages, deterministic_analysis=deterministic)
    except Exception as exc:
        raise HTTPException(502, f"Visual inspection failed: {type(exc).__name__}: {exc}")
    if result.get("pages"):
        doc.extracted_metadata = {**(doc.extracted_metadata or {}), "vision_inspection": result}
        db.commit()
    event_details = {
        "pages": len(result.get("pages", [])),
        "confirmed_entities": len((result.get("consensus") or {}).get("confirmed", [])),
        "disagreements": len((result.get("consensus") or {}).get("disagreements", [])),
    }
    log_event(db, identity.user, "VISUAL_INSPECTION", "document", doc.id, event_details)
    log_document_activity(db, doc.id, identity.user, "VISUAL_INSPECTION", "Выполнена локальная AI-проверка изображения чертежа", event_details)
    return result

@router.get("/projects")
def list_projects(identity: Identity = Depends(get_identity), db: Session = Depends(get_db)):
    rows = db.scalars(select(Project).order_by(Project.updated_at.desc(), Project.code)).all()
    result = []
    visible_ids = _visible_ids(db, identity)
    for project in rows:
        if not project_allowed(project, identity.groups):
            continue
        workspace = project_workspace(db, project, visible_ids, identity_groups=identity.groups)
        item = serialize_project(project)
        item["readiness"] = workspace["readiness"]
        item["counts"] = workspace["counts"]
        result.append(item)
    return result

@router.post("/projects")
def create_project(req: ProjectCreateRequest, identity: Identity = Depends(get_identity), db: Session = Depends(get_db)):
    if not _is_admin(identity):
        raise HTTPException(403, "Engineering admin required to create projects")
    code = req.code.upper()
    if db.scalar(select(Project).where(Project.code == code)):
        raise HTTPException(409, "Project code already exists")
    groups = sorted({g for g in (req.acl_groups or list(get_settings().engineer_access_group_set)) if g and g != "all"}) or ["all"]
    project = Project(
        code=code, name=req.name.strip(), description=req.description, phase=req.phase.strip() or "development",
        owner=req.owner, root_part_number=req.root_part_number.upper() if req.root_part_number else None,
        target_release_at=_parse_iso_datetime(req.target_release_at), acl_groups=groups,
        metadata_json={"release_decision_policy": "human_approval_required"},
    )
    db.add(project); db.commit(); db.refresh(project)
    ensure_project_areas(db, project)
    log_event(db, identity.user, "PROJECT_CREATED", "project", project.code, {"name": project.name, "acl_groups": groups})
    return serialize_project(project)

@router.patch("/projects/{project_code}")
def update_project(project_code: str, req: ProjectUpdateRequest, identity: Identity = Depends(get_identity), db: Session = Depends(get_db)):
    if not _is_admin(identity):
        raise HTTPException(403, "Engineering admin required to change project settings")
    project = _get_visible_project(db, project_code, identity)
    values = req.model_dump(exclude_unset=True)
    if "target_release_at" in values:
        values["target_release_at"] = _parse_iso_datetime(values["target_release_at"])
    if values.get("root_part_number"):
        values["root_part_number"] = values["root_part_number"].upper()
    if "acl_groups" in values and values["acl_groups"] is not None:
        values["acl_groups"] = sorted({g for g in values["acl_groups"] if g and g != "all"}) or ["all"]
    for key, value in values.items():
        setattr(project, key, value)
    db.commit(); db.refresh(project)
    log_event(db, identity.user, "PROJECT_UPDATED", "project", project.code, {"fields": sorted(values)})
    return serialize_project(project)

@router.get("/projects/{project_code}/workspace")
def get_project_workspace(project_code: str, request: Request, response: Response, manufacturing_area: str | None = None, identity: Identity = Depends(get_identity), db: Session = Depends(get_db)):
    from app.services.read_models import acl_fingerprint, cache_key, etag_for_payload, pending_read_model_invalidation, redis_cache_get, redis_cache_set
    project = _get_visible_project(db, project_code, identity)
    ensure_project_areas(db, project)
    if manufacturing_area:
        area = db.scalar(select(ProjectArea).where(ProjectArea.project_code == project.code, ProjectArea.code == manufacturing_area))
        if not area or not area_allowed(area, identity.groups):
            raise HTTPException(404, "Manufacturing area not found")
    visible = _visible_ids(db, identity)
    cfg = get_settings(); pending = pending_read_model_invalidation(db)
    identity_key = acl_fingerprint(visible, identity.groups)
    key = cache_key("project_workspace", identity_key, project.code, manufacturing_area or "all")
    payload = None if pending else redis_cache_get(key, surface="project_workspace")
    cache_state = "redis_hit" if payload is not None else ("bypass_pending_invalidation" if pending else "miss")
    if payload is None:
        payload = project_workspace(db, project, visible, manufacturing_area=manufacturing_area, identity_groups=identity.groups)
        if not pending: redis_cache_set(key, payload, ttl=cfg.read_model_cache_ttl_seconds, surface="project_workspace")
    etag = etag_for_payload(payload); headers={"ETag":etag,"Cache-Control":"private, no-cache","X-MGC-Cache":cache_state}
    if request.headers.get("if-none-match") == etag: return Response(status_code=304, headers=headers)
    response.headers.update(headers)
    return payload

@router.get("/projects/{project_code}/areas")
def project_areas(project_code: str, identity: Identity = Depends(get_identity), db: Session = Depends(get_db)):
    project = _get_visible_project(db, project_code, identity)
    rows = visible_project_areas(db, project, identity.groups)
    return [serialize_area(x, identity.groups) for x in rows]

@router.patch("/projects/{project_code}/areas/{area_code}")
def update_project_area(project_code: str, area_code: str, req: ProjectAreaUpdateRequest, identity: Identity = Depends(get_identity), db: Session = Depends(get_db)):
    if not _is_admin(identity):
        raise HTTPException(403, "Engineering admin required to change area settings")
    project = _get_visible_project(db, project_code, identity)
    ensure_project_areas(db, project)
    area = db.scalar(select(ProjectArea).where(ProjectArea.project_code == project.code, ProjectArea.code == area_code))
    if not area:
        raise HTTPException(404, "Manufacturing area not found")
    values = req.model_dump(exclude_unset=True)
    if "acl_groups" in values and values["acl_groups"] is not None:
        values["acl_groups"] = sorted({g for g in values["acl_groups"] if g}) or list(project.acl_groups or ["all"])
    for key, value in values.items(): setattr(area, key, value)
    db.commit(); db.refresh(area)
    log_event(db, identity.user, "PROJECT_AREA_UPDATED", "project", project.code, {"area": area.code, "fields": sorted(values)})
    return serialize_area(area, identity.groups)

@router.patch("/documents/{document_id}/manufacturing-area")
def update_document_area(document_id: str, req: DocumentAreaUpdateRequest, identity: Identity = Depends(get_identity), db: Session = Depends(get_db)):
    if not valid_area(req.manufacturing_area): raise HTTPException(400, "Unknown manufacturing area")
    doc = db.get(Document, document_id)
    if not doc or not _allowed(doc, identity): raise HTTPException(404)
    if doc.project_code and req.manufacturing_area:
        project = db.scalar(select(Project).where(Project.code == doc.project_code))
        if project:
            ensure_project_areas(db, project)
            area = db.scalar(select(ProjectArea).where(ProjectArea.project_code == project.code, ProjectArea.code == req.manufacturing_area))
            if not area or not area_allowed(area, identity.groups): raise HTTPException(403, "No access to manufacturing area")
    old = doc.manufacturing_area; doc.manufacturing_area = req.manufacturing_area
    db.commit(); db.refresh(doc)
    log_document_activity(db, doc.id, identity.user, "MANUFACTURING_AREA_CHANGED", "Изменена производственная зона документа", {"from": old, "to": req.manufacturing_area})
    return serialize_doc(doc)

@router.post("/projects/{project_code}/milestones")
def create_project_milestone(project_code: str, req: MilestoneCreateRequest, identity: Identity = Depends(get_identity), db: Session = Depends(get_db)):
    project = _get_visible_project(db, project_code, identity)
    if not valid_area(req.manufacturing_area): raise HTTPException(400, "Unknown manufacturing area")
    code = req.code.upper()
    if db.scalar(select(ProjectMilestone).where(ProjectMilestone.project_code == project.code, ProjectMilestone.code == code)):
        raise HTTPException(409, "Milestone code already exists in this project")
    milestone = ProjectMilestone(
        project_code=project.code, code=code, name=req.name.strip(), due_at=_parse_iso_datetime(req.due_at),
        owner=req.owner or identity.user, gate=req.gate, manufacturing_area=req.manufacturing_area, notes=req.notes,
    )
    db.add(milestone); db.commit(); db.refresh(milestone)
    log_event(db, identity.user, "PROJECT_MILESTONE_CREATED", "project", project.code, {"milestone": code, "name": milestone.name})
    return serialize_milestone(milestone)

@router.patch("/projects/{project_code}/milestones/{milestone_id}")
def update_project_milestone(project_code: str, milestone_id: str, req: MilestoneUpdateRequest, identity: Identity = Depends(get_identity), db: Session = Depends(get_db)):
    project = _get_visible_project(db, project_code, identity)
    milestone = db.get(ProjectMilestone, milestone_id)
    if not milestone or milestone.project_code != project.code:
        raise HTTPException(404, "Milestone not found")
    values = req.model_dump(exclude_unset=True)
    if "due_at" in values:
        values["due_at"] = _parse_iso_datetime(values["due_at"])
    if "manufacturing_area" in values and not valid_area(values["manufacturing_area"]):
        raise HTTPException(400, "Unknown manufacturing area")
    for key, value in values.items():
        setattr(milestone, key, value)
    db.commit(); db.refresh(milestone)
    log_event(db, identity.user, "PROJECT_MILESTONE_UPDATED", "project", project.code, {"milestone": milestone.code, "fields": sorted(values), "status": milestone.status})
    return serialize_milestone(milestone)

@router.get("/projects/{project_code}/requirements-matrix")
def get_requirements_matrix(project_code: str, manufacturing_area: str | None = None, identity: Identity = Depends(get_identity), db: Session = Depends(get_db)):
    project, visible_doc_ids, visible_parts, allowed_areas = _requirement_context(db, project_code, identity, manufacturing_area)
    return requirements_matrix(db, project.code, visible_doc_ids, visible_parts, manufacturing_area, allowed_areas)

@router.post("/projects/{project_code}/requirements")
def create_requirement(project_code: str, req: EngineeringRequirementCreateRequest, identity: Identity = Depends(get_identity), db: Session = Depends(get_db)):
    project, visible_doc_ids, visible_parts, _ = _requirement_context(db, project_code, identity)
    _validate_quality_area(db, project, identity, req.manufacturing_area)
    source_document_id = None
    if req.source_document_id:
        source_document_id = _validate_quality_evidence(db, project, visible_doc_ids, [req.source_document_id])[0]
    parts = _validate_requirement_parts(req.part_numbers, visible_parts)
    _validate_characteristic_refs(db, project.code, req.special_characteristic_ids, visible_parts)
    changes = _validate_requirement_changes(db, req.linked_change_ids, visible_parts)
    code=req.code.upper()
    if db.scalar(select(EngineeringRequirement).where(EngineeringRequirement.project_code==project.code, EngineeringRequirement.code==code)):
        raise HTTPException(409,"Requirement code already exists")
    row=EngineeringRequirement(project_code=project.code, manufacturing_area=req.manufacturing_area, code=code, category=req.category,
        criticality=req.criticality, title=req.title.strip(), requirement_text=req.requirement_text.strip(), source_document_id=source_document_id,
        source_reference=req.source_reference, system_name=req.system_name, function_name=req.function_name, part_numbers=parts,
        special_characteristic_ids=sorted(set(req.special_characteristic_ids)), verification_method=req.verification_method,
        acceptance_criteria=req.acceptance_criteria, linked_change_ids=changes, owner=req.owner or identity.user, created_by=identity.user)
    db.add(row); db.commit(); db.refresh(row)
    log_event(db, identity.user, "REQUIREMENT_CREATED", "project", project.code, {"id":row.id,"code":row.code,"criticality":row.criticality,"area":row.manufacturing_area})
    return serialize_requirement(row, visible_parts, set(req.special_characteristic_ids))

@router.patch("/projects/{project_code}/requirements/{requirement_id}")
def update_requirement(project_code: str, requirement_id: str, req: EngineeringRequirementUpdateRequest, identity: Identity = Depends(get_identity), db: Session = Depends(get_db)):
    project, visible_doc_ids, visible_parts, _ = _requirement_context(db, project_code, identity)
    row=_get_visible_requirement(db,project,requirement_id,visible_doc_ids,visible_parts,identity)
    values=req.model_dump(exclude_unset=True)
    if "manufacturing_area" in values: _validate_quality_area(db,project,identity,values["manufacturing_area"])
    if "source_document_id" in values:
        values["source_document_id"] = _validate_quality_evidence(db,project,visible_doc_ids,[values["source_document_id"]])[0] if values["source_document_id"] else None
    if "part_numbers" in values: values["part_numbers"]=_validate_requirement_parts(values["part_numbers"],visible_parts)
    if "special_characteristic_ids" in values:
        _validate_characteristic_refs(db,project.code,values["special_characteristic_ids"],visible_parts); values["special_characteristic_ids"]=sorted(set(values["special_characteristic_ids"]))
    if "linked_change_ids" in values: values["linked_change_ids"]=_validate_requirement_changes(db,values["linked_change_ids"],visible_parts)
    for key,value in values.items(): setattr(row,key,value)
    db.commit(); db.refresh(row)
    log_event(db,identity.user,"REQUIREMENT_UPDATED","project",project.code,{"id":row.id,"fields":sorted(values)})
    return serialize_requirement(row,visible_parts)

@router.post("/projects/{project_code}/requirements/{requirement_id}/verifications")
def create_requirement_verification(project_code: str, requirement_id: str, req: RequirementVerificationCreateRequest, identity: Identity = Depends(get_identity), db: Session = Depends(get_db)):
    project, visible_doc_ids, visible_parts, _ = _requirement_context(db, project_code, identity)
    requirement=_get_visible_requirement(db,project,requirement_id,visible_doc_ids,visible_parts,identity)
    area=req.manufacturing_area if req.manufacturing_area is not None else requirement.manufacturing_area
    _validate_quality_area(db,project,identity,area)
    evidence=_validate_quality_evidence(db,project,visible_doc_ids,req.evidence_document_ids)
    launch,review,_=_validate_verification_links(db,project,visible_parts,req.launch_trial_id,req.design_review_id,req.linked_change_id)
    if req.status=="passed" and not (req.result_summary or "").strip(): raise HTTPException(400,"Passed verification requires result summary")
    if not _verification_has_proof(req.status,evidence,launch,review): raise HTTPException(400,"Passed verification requires visible evidence, passed Launch Trial, or approved Design Review")
    code=req.code.upper()
    if db.scalar(select(RequirementVerification).where(RequirementVerification.project_code==project.code, RequirementVerification.code==code)):
        raise HTTPException(409,"Verification code already exists")
    source=db.get(Document,requirement.source_document_id) if requirement.source_document_id else None
    snapshots={d.id:d.sha256 for d in db.scalars(select(Document).where(Document.id.in_(evidence))).all()} if evidence else {}
    row=RequirementVerification(project_code=project.code,requirement_id=requirement.id,manufacturing_area=area,code=code,
        verification_type=req.verification_type,phase=req.phase,title=req.title.strip(),status=req.status,result_summary=req.result_summary,
        measured_result_json=req.measured_result,evidence_document_ids=evidence,launch_trial_id=req.launch_trial_id,design_review_id=req.design_review_id,
        linked_change_id=req.linked_change_id,performed_by=identity.user if req.status in {"passed","failed"} else None,
        performed_at=datetime.now().astimezone() if req.status in {"passed","failed"} else None,
        requirement_updated_at_snapshot=requirement.updated_at if req.status=="passed" else None,
        source_document_sha256_snapshot=source.sha256 if req.status=="passed" and source else None,
        evidence_snapshot_json=snapshots if req.status=="passed" else {},notes=req.notes,created_by=identity.user)
    db.add(row); db.commit(); db.refresh(row)
    log_event(db,identity.user,"REQUIREMENT_VERIFICATION_CREATED","project",project.code,{"id":row.id,"requirement":requirement.code,"status":row.status})
    return serialize_verification(db,row,requirement,visible_doc_ids,visible_parts)

@router.patch("/projects/{project_code}/requirements/verifications/{verification_id}")
def update_requirement_verification(project_code: str, verification_id: str, req: RequirementVerificationUpdateRequest, identity: Identity = Depends(get_identity), db: Session = Depends(get_db)):
    project, visible_doc_ids, visible_parts, _ = _requirement_context(db, project_code, identity)
    row=db.get(RequirementVerification,verification_id)
    if not row or row.project_code!=project.code: raise HTTPException(404,"Verification not found")
    requirement=_get_visible_requirement(db,project,row.requirement_id,visible_doc_ids,visible_parts,identity)
    values=req.model_dump(exclude_unset=True)
    if "manufacturing_area" in values: _validate_quality_area(db,project,identity,values["manufacturing_area"])
    evidence=values.get("evidence_document_ids",row.evidence_document_ids or [])
    if "evidence_document_ids" in values:
        evidence=_validate_quality_evidence(db,project,visible_doc_ids,evidence); values["evidence_document_ids"]=evidence
    launch_id=values.get("launch_trial_id",row.launch_trial_id); review_id=values.get("design_review_id",row.design_review_id); change_id=values.get("linked_change_id",row.linked_change_id)
    launch,review,_=_validate_verification_links(db,project,visible_parts,launch_id,review_id,change_id)
    new_status=values.get("status",row.status); result_summary=values.get("result_summary",row.result_summary)
    if new_status=="passed" and not (result_summary or "").strip(): raise HTTPException(400,"Passed verification requires result summary")
    if not _verification_has_proof(new_status,evidence,launch,review): raise HTTPException(400,"Passed verification requires visible evidence, passed Launch Trial, or approved Design Review")
    if "measured_result" in values: values["measured_result_json"]=values.pop("measured_result")
    if new_status in {"passed","failed"}:
        values["performed_by"]=identity.user; values["performed_at"]=datetime.now().astimezone()
    if new_status=="passed":
        source=db.get(Document,requirement.source_document_id) if requirement.source_document_id else None
        snapshots={d.id:d.sha256 for d in db.scalars(select(Document).where(Document.id.in_(evidence))).all()} if evidence else {}
        values["requirement_updated_at_snapshot"]=requirement.updated_at
        values["source_document_sha256_snapshot"]=source.sha256 if source else None
        values["evidence_snapshot_json"]=snapshots
    elif "status" in values:
        values["requirement_updated_at_snapshot"]=None; values["source_document_sha256_snapshot"]=None; values["evidence_snapshot_json"]={}
    for key,value in values.items(): setattr(row,key,value)
    db.commit(); db.refresh(row)
    log_event(db,identity.user,"REQUIREMENT_VERIFICATION_UPDATED","project",project.code,{"id":row.id,"fields":sorted(values),"status":row.status})
    return serialize_verification(db,row,requirement,visible_doc_ids,visible_parts)

@router.get("/projects/{project_code}/vehicle-architecture")
def get_vehicle_architecture(project_code: str, manufacturing_area: str | None = None, identity: Identity = Depends(get_identity), db: Session = Depends(get_db)):
    project, visible_doc_ids, visible_parts, allowed_areas = _architecture_context(db, project_code, identity, manufacturing_area)
    return vehicle_architecture_workspace(db, project.code, visible_doc_ids, visible_parts, manufacturing_area, allowed_areas)

@router.get("/projects/{project_code}/vehicle-architecture/impact")
def get_vehicle_architecture_impact(project_code: str, part_number: str, manufacturing_area: str | None = None, identity: Identity = Depends(get_identity), db: Session = Depends(get_db)):
    project, visible_doc_ids, visible_parts, allowed_areas = _architecture_context(db, project_code, identity, manufacturing_area)
    pn=part_number.strip().upper()
    if pn not in visible_parts: raise HTTPException(404,"Part not found")
    return architecture_impact(db, project.code, pn, visible_doc_ids, visible_parts, manufacturing_area, allowed_areas)

@router.post("/projects/{project_code}/vehicle-architecture/nodes")
def create_architecture_node(project_code: str, req: ArchitectureNodeCreateRequest, identity: Identity = Depends(get_identity), db: Session = Depends(get_db)):
    project, visible_doc_ids, visible_parts, _ = _architecture_context(db, project_code, identity)
    _validate_quality_area(db,project,identity,req.manufacturing_area)
    pn=_validate_quality_part(req.part_number,visible_parts)
    evidence=_arch_evidence(db,project,visible_doc_ids,req.evidence_document_ids)
    parent=None
    if req.parent_node_id:
        parent=_get_arch_node(db,project,req.parent_node_id,identity,visible_parts)
        if parent.node_type=="component": raise HTTPException(400,"Component cannot contain child architecture nodes")
    code=req.code.upper()
    if db.scalar(select(ArchitectureNode).where(ArchitectureNode.project_code==project.code,ArchitectureNode.code==code)):
        raise HTTPException(409,"Architecture node code already exists")
    row=ArchitectureNode(project_code=project.code,manufacturing_area=req.manufacturing_area,code=code,name=req.name.strip(),node_type=req.node_type,parent_node_id=parent.id if parent else None,part_number=pn,status=req.status,owner=req.owner or identity.user,description=req.description,evidence_document_ids=evidence,created_by=identity.user)
    db.add(row);db.commit();db.refresh(row)
    log_event(db,identity.user,"ARCHITECTURE_NODE_CREATED","project",project.code,{"id":row.id,"code":row.code,"node_type":row.node_type,"part_number":row.part_number})
    return serialize_node(row,visible_doc_ids)

@router.patch("/projects/{project_code}/vehicle-architecture/nodes/{node_id}")
def update_architecture_node(project_code: str, node_id: str, req: ArchitectureNodeUpdateRequest, identity: Identity = Depends(get_identity), db: Session = Depends(get_db)):
    project, visible_doc_ids, visible_parts, _ = _architecture_context(db, project_code, identity)
    row=_get_arch_node(db,project,node_id,identity,visible_parts)
    values=req.model_dump(exclude_unset=True)
    if "manufacturing_area" in values: _validate_quality_area(db,project,identity,values["manufacturing_area"])
    if "part_number" in values: values["part_number"]=_validate_quality_part(values["part_number"],visible_parts)
    if "evidence_document_ids" in values: values["evidence_document_ids"]=_arch_evidence(db,project,visible_doc_ids,values["evidence_document_ids"])
    if "parent_node_id" in values and values["parent_node_id"]:
        if values["parent_node_id"]==row.id: raise HTTPException(400,"Architecture node cannot be its own parent")
        parent=_get_arch_node(db,project,values["parent_node_id"],identity,visible_parts)
        values["parent_node_id"]=parent.id
    for k,v in values.items(): setattr(row,k,v)
    db.commit();db.refresh(row)
    log_event(db,identity.user,"ARCHITECTURE_NODE_UPDATED","project",project.code,{"id":row.id,"fields":sorted(values)})
    return serialize_node(row,visible_doc_ids)

@router.post("/projects/{project_code}/vehicle-architecture/interfaces")
def create_interface(project_code: str, req: InterfaceCreateRequest, identity: Identity = Depends(get_identity), db: Session = Depends(get_db)):
    project, visible_doc_ids, visible_parts, _ = _architecture_context(db, project_code, identity)
    _validate_quality_area(db,project,identity,req.manufacturing_area)
    source=_get_arch_node(db,project,req.source_node_id,identity,visible_parts);target=_get_arch_node(db,project,req.target_node_id,identity,visible_parts)
    if source.id==target.id: raise HTTPException(400,"Interface endpoints must be different")
    requirements=_arch_requirements(db,project,req.requirement_ids,visible_doc_ids,visible_parts,identity)
    changes=_arch_changes(db,req.linked_change_ids,visible_parts)
    evidence=_arch_evidence(db,project,visible_doc_ids,req.evidence_document_ids)
    code=req.code.upper()
    if db.scalar(select(InterfaceDefinition).where(InterfaceDefinition.project_code==project.code,InterfaceDefinition.code==code)):
        raise HTTPException(409,"Interface code already exists")
    row=InterfaceDefinition(project_code=project.code,manufacturing_area=req.manufacturing_area,code=code,name=req.name.strip(),interface_type=req.interface_type,source_node_id=source.id,target_node_id=target.id,criticality=req.criticality,status=req.status,owner=req.owner or identity.user,requirement_ids=requirements,linked_change_ids=changes,specifications_json=req.specifications,evidence_document_ids=evidence,notes=req.notes,created_by=identity.user)
    db.add(row);db.commit();db.refresh(row)
    log_event(db,identity.user,"INTERFACE_CREATED","project",project.code,{"id":row.id,"code":row.code,"source":source.code,"target":target.code,"criticality":row.criticality})
    project, visible_doc_ids, visible_parts, allowed_areas = _architecture_context(db, project_code, identity, row.manufacturing_area)
    return next(x for x in vehicle_architecture_workspace(db,project.code,visible_doc_ids,visible_parts,row.manufacturing_area,allowed_areas)["interfaces"] if x["id"]==row.id)

@router.patch("/projects/{project_code}/vehicle-architecture/interfaces/{interface_id}")
def update_interface(project_code: str, interface_id: str, req: InterfaceUpdateRequest, identity: Identity = Depends(get_identity), db: Session = Depends(get_db)):
    project, visible_doc_ids, visible_parts, _ = _architecture_context(db, project_code, identity)
    row=_get_interface(db,project,interface_id,identity,visible_parts);values=req.model_dump(exclude_unset=True)
    if "manufacturing_area" in values: _validate_quality_area(db,project,identity,values["manufacturing_area"])
    if "source_node_id" in values and values["source_node_id"]: values["source_node_id"]=_get_arch_node(db,project,values["source_node_id"],identity,visible_parts).id
    if "target_node_id" in values and values["target_node_id"]: values["target_node_id"]=_get_arch_node(db,project,values["target_node_id"],identity,visible_parts).id
    if values.get("source_node_id",row.source_node_id)==values.get("target_node_id",row.target_node_id): raise HTTPException(400,"Interface endpoints must be different")
    if "requirement_ids" in values: values["requirement_ids"]=_arch_requirements(db,project,values["requirement_ids"],visible_doc_ids,visible_parts,identity)
    if "linked_change_ids" in values: values["linked_change_ids"]=_arch_changes(db,values["linked_change_ids"],visible_parts)
    if "evidence_document_ids" in values: values["evidence_document_ids"]=_arch_evidence(db,project,visible_doc_ids,values["evidence_document_ids"])
    if "specifications" in values: values["specifications_json"]=values.pop("specifications")
    for k,v in values.items(): setattr(row,k,v)
    db.commit();db.refresh(row)
    log_event(db,identity.user,"INTERFACE_UPDATED","project",project.code,{"id":row.id,"fields":sorted(values)})
    project, visible_doc_ids, visible_parts, allowed_areas = _architecture_context(db, project_code, identity, row.manufacturing_area)
    return next(x for x in vehicle_architecture_workspace(db,project.code,visible_doc_ids,visible_parts,row.manufacturing_area,allowed_areas)["interfaces"] if x["id"]==row.id)

@router.post("/projects/{project_code}/vehicle-architecture/interfaces/{interface_id}/verifications")
def create_interface_verification(project_code: str, interface_id: str, req: InterfaceVerificationCreateRequest, identity: Identity = Depends(get_identity), db: Session = Depends(get_db)):
    project, visible_doc_ids, visible_parts, _ = _architecture_context(db, project_code, identity)
    interface=_get_interface(db,project,interface_id,identity,visible_parts)
    evidence=_arch_evidence(db,project,visible_doc_ids,req.evidence_document_ids)
    linked=_validate_linked_req_verification(db,project,req.linked_requirement_verification_id,visible_doc_ids,visible_parts,identity)
    linked_effective=False
    if linked:
        linked_req=_get_visible_requirement(db,project,linked.requirement_id,visible_doc_ids,visible_parts,identity)
        linked_effective=bool(serialize_verification(db,linked,linked_req,visible_doc_ids,visible_parts).get("effective_pass"))
    if req.status=="passed" and not (evidence or linked_effective): raise HTTPException(400,"PASSED interface verification requires evidence or an effective linked requirement verification")
    code=req.code.upper()
    if db.scalar(select(InterfaceVerification).where(InterfaceVerification.project_code==project.code,InterfaceVerification.code==code)): raise HTTPException(409,"Interface verification code already exists")
    nodes={n.id:n for n in db.scalars(select(ArchitectureNode).where(ArchitectureNode.project_code==project.code)).all()}
    row=InterfaceVerification(project_code=project.code,interface_id=interface.id,manufacturing_area=interface.manufacturing_area,code=code,verification_type=req.verification_type,title=req.title.strip(),status=req.status,result_summary=req.result_summary,measured_result_json=req.measured_result,evidence_document_ids=evidence,linked_requirement_verification_id=linked.id if linked else None,interface_fingerprint_snapshot=interface_fingerprint(interface,nodes) if req.status=="passed" else None,performed_by=identity.user if req.status in {"passed","failed","waived"} else None,performed_at=_parse_iso_datetime(req.performed_at),notes=req.notes,created_by=identity.user)
    db.add(row);db.commit();db.refresh(row)
    log_event(db,identity.user,"INTERFACE_VERIFICATION_CREATED","project",project.code,{"id":row.id,"interface_id":interface.id,"status":row.status})
    project, visible_doc_ids, visible_parts, allowed_areas = _architecture_context(db, project_code, identity, interface.manufacturing_area)
    return next(v for x in vehicle_architecture_workspace(db,project.code,visible_doc_ids,visible_parts,interface.manufacturing_area,allowed_areas)["interfaces"] if x["id"]==interface.id for v in x["verifications"] if v["id"]==row.id)

@router.patch("/projects/{project_code}/vehicle-architecture/verifications/{verification_id}")
def update_interface_verification(project_code: str, verification_id: str, req: InterfaceVerificationUpdateRequest, identity: Identity = Depends(get_identity), db: Session = Depends(get_db)):
    project, visible_doc_ids, visible_parts, _ = _architecture_context(db, project_code, identity)
    row=db.get(InterfaceVerification,verification_id)
    if not row or row.project_code!=project.code: raise HTTPException(404,"Interface verification not found")
    interface=_get_interface(db,project,row.interface_id,identity,visible_parts);values=req.model_dump(exclude_unset=True)
    if "evidence_document_ids" in values: values["evidence_document_ids"]=_arch_evidence(db,project,visible_doc_ids,values["evidence_document_ids"])
    linked=None
    if "linked_requirement_verification_id" in values:
        linked=_validate_linked_req_verification(db,project,values["linked_requirement_verification_id"],visible_doc_ids,visible_parts,identity)
        values["linked_requirement_verification_id"]=linked.id if linked else None
    status=values.get("status",row.status);evidence=values.get("evidence_document_ids",row.evidence_document_ids);linked_id=values.get("linked_requirement_verification_id",row.linked_requirement_verification_id)
    linked_effective=False
    if linked_id:
        linked_row=db.get(RequirementVerification,linked_id)
        if linked_row and linked_row.project_code==project.code:
            linked_req=_get_visible_requirement(db,project,linked_row.requirement_id,visible_doc_ids,visible_parts,identity)
            linked_effective=bool(serialize_verification(db,linked_row,linked_req,visible_doc_ids,visible_parts).get("effective_pass"))
    if status=="passed" and not (evidence or linked_effective): raise HTTPException(400,"PASSED interface verification requires evidence or an effective linked requirement verification")
    if "measured_result" in values: values["measured_result_json"]=values.pop("measured_result")
    if "performed_at" in values: values["performed_at"]=_parse_iso_datetime(values["performed_at"])
    for k,v in values.items(): setattr(row,k,v)
    if status=="passed":
        nodes={n.id:n for n in db.scalars(select(ArchitectureNode).where(ArchitectureNode.project_code==project.code)).all()};row.interface_fingerprint_snapshot=interface_fingerprint(interface,nodes);row.performed_by=row.performed_by or identity.user
    db.commit();db.refresh(row)
    log_event(db,identity.user,"INTERFACE_VERIFICATION_UPDATED","project",project.code,{"id":row.id,"status":row.status,"fields":sorted(values)})
    project, visible_doc_ids, visible_parts, allowed_areas = _architecture_context(db, project_code, identity, interface.manufacturing_area)
    return next(v for x in vehicle_architecture_workspace(db,project.code,visible_doc_ids,visible_parts,interface.manufacturing_area,allowed_areas)["interfaces"] if x["id"]==interface.id for v in x["verifications"] if v["id"]==row.id)

@router.get("/projects/{project_code}/program-control")
def get_program_control(project_code: str, manufacturing_area: str | None = None, identity: Identity = Depends(get_identity), db: Session = Depends(get_db)):
    project, visible_doc_ids, visible_parts, allowed_areas = _program_context(db, project_code, identity, manufacturing_area)
    return program_control_workspace(db, project, visible_doc_ids, visible_parts, manufacturing_area, allowed_areas)

@router.post("/projects/{project_code}/program-control/dependencies")
def create_program_dependency(project_code: str, req: ProgramDependencyCreateRequest, identity: Identity = Depends(get_identity), db: Session = Depends(get_db)):
    project, visible_doc_ids, visible_parts, allowed_areas = _program_context(db, project_code, identity, req.manufacturing_area)
    pred = _program_visible_milestone(db, project.code, req.predecessor_milestone_id, allowed_areas, req.manufacturing_area)
    succ = _program_visible_milestone(db, project.code, req.successor_milestone_id, allowed_areas, req.manufacturing_area)
    if pred.id == succ.id:
        raise HTTPException(400, "A milestone cannot depend on itself")
    existing = db.scalar(select(ProgramDependency).where(ProgramDependency.project_code == project.code, ProgramDependency.predecessor_milestone_id == pred.id, ProgramDependency.successor_milestone_id == succ.id))
    if existing:
        raise HTTPException(409, "Program dependency already exists")
    row = ProgramDependency(project_code=project.code, manufacturing_area=req.manufacturing_area, predecessor_milestone_id=pred.id, successor_milestone_id=succ.id, dependency_type=req.dependency_type, lag_days=req.lag_days, criticality=req.criticality, owner=req.owner or identity.user, notes=req.notes, created_by=identity.user, metadata_json=req.metadata)
    db.add(row); db.flush()
    context = visible_program_rows(db, project.code, visible_doc_ids, visible_parts, req.manufacturing_area, allowed_areas)
    # Reject cycles deterministically by checking whether the new successor can already reach predecessor.
    graph = {}
    for e in context["dependencies"]:
        graph.setdefault(e.predecessor_milestone_id, set()).add(e.successor_milestone_id)
    stack=[succ.id]; seen=set()
    while stack:
        node=stack.pop()
        if node==pred.id:
            db.rollback(); raise HTTPException(400, "Program dependency would create a cycle")
        if node in seen: continue
        seen.add(node); stack.extend(graph.get(node,set()))
    db.commit(); db.refresh(row)
    milestones={x.id:x for x in context["milestones"]}
    log_event(db, identity.user, "PROGRAM_DEPENDENCY_CREATED", "project", project.code, {"dependency_id":row.id,"from":pred.code,"to":succ.code,"lag_days":row.lag_days})
    return serialize_dependency(row, milestones | {pred.id:pred, succ.id:succ})

@router.patch("/projects/{project_code}/program-control/dependencies/{dependency_id}")
def update_program_dependency(project_code: str, dependency_id: str, req: ProgramDependencyUpdateRequest, identity: Identity = Depends(get_identity), db: Session = Depends(get_db)):
    project, _, _, allowed_areas = _program_context(db, project_code, identity, None)
    row=db.get(ProgramDependency, dependency_id)
    if not row or row.project_code != project.code or (row.manufacturing_area and row.manufacturing_area not in allowed_areas):
        raise HTTPException(404, "Program dependency not found")
    values=req.model_dump(exclude_unset=True)
    for key,value in values.items(): setattr(row,key,value)
    db.commit(); db.refresh(row)
    pred=_program_visible_milestone(db,project.code,row.predecessor_milestone_id,allowed_areas)
    succ=_program_visible_milestone(db,project.code,row.successor_milestone_id,allowed_areas)
    log_event(db, identity.user, "PROGRAM_DEPENDENCY_UPDATED", "project", project.code, {"dependency_id":row.id,"fields":sorted(values)})
    return serialize_dependency(row,{pred.id:pred,succ.id:succ})

@router.delete("/projects/{project_code}/program-control/dependencies/{dependency_id}")
def delete_program_dependency(project_code: str, dependency_id: str, identity: Identity = Depends(get_identity), db: Session = Depends(get_db)):
    project, _, _, allowed_areas = _program_context(db, project_code, identity, None)
    row=db.get(ProgramDependency, dependency_id)
    if not row or row.project_code != project.code or (row.manufacturing_area and row.manufacturing_area not in allowed_areas):
        raise HTTPException(404, "Program dependency not found")
    dep_id=row.id; db.delete(row); db.commit()
    log_event(db, identity.user, "PROGRAM_DEPENDENCY_DELETED", "project", project.code, {"dependency_id":dep_id})
    return {"ok": True, "dependency_id": dep_id}

@router.post("/projects/{project_code}/program-control/slip-simulation")
def simulate_program_slip(project_code: str, req: ProgramSlipSimulationRequest, manufacturing_area: str | None = None, identity: Identity = Depends(get_identity), db: Session = Depends(get_db)):
    project, visible_doc_ids, visible_parts, allowed_areas = _program_context(db, project_code, identity, manufacturing_area)
    context = visible_program_rows(db, project.code, visible_doc_ids, visible_parts, manufacturing_area, allowed_areas)
    if req.milestone_id not in {x.id for x in context["milestones"]}:
        raise HTTPException(404, "Milestone not found")
    try:
        return simulate_milestone_slip(context["milestones"], context["dependencies"], req.milestone_id, req.slip_days)
    except LookupError as exc:
        raise HTTPException(404, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc

