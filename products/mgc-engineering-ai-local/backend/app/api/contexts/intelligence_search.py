"""Intelligence Search HTTP handlers — v6.2.2.

Extracted from the former 3k-line route monolith. Public paths are unchanged.
"""
from fastapi import APIRouter
from app.api import context_shared as _shared

# Preserve the mature shared handler namespace without duplicating service imports.
globals().update({k: v for k, v in vars(_shared).items() if not k.startswith("__")})
from app.api.lazy_service import lazy_service

advance_workflow_case = lazy_service("app.services.engineering_intelligence_os", "advance_workflow_case")
analyze_change_impact = lazy_service("app.services.change_impact", "analyze_change_impact")
ask = lazy_service("app.services.rag", "ask")
build_memory_answer = lazy_service("app.services.engineering_knowledge_memory", "build_memory_answer")
change_intelligence_workspace = lazy_service("app.services.change_intelligence", "change_intelligence_workspace")
collect_project_cases = lazy_service("app.services.engineering_knowledge_memory", "collect_project_cases")
create_lesson_from_case = lazy_service("app.services.engineering_knowledge_memory", "create_lesson_from_case")
deterministic_thread_facts = lazy_service("app.services.change_intelligence", "deterministic_thread_facts")
engineering_digital_thread = lazy_service("app.services.engineering_digital_thread", "engineering_digital_thread")
engineering_os_answer = lazy_service("app.services.engineering_intelligence_os", "engineering_os_answer")
execute_engineering_workflow = lazy_service("app.services.agent", "execute_engineering_workflow")
graph_neighborhood = lazy_service("app.services.infrastructure_ports", "graph_neighborhood")
graph_sync_part = lazy_service("app.services.infrastructure_ports", "graph_sync_part")
initialize_workflow_state = lazy_service("app.services.engineering_intelligence_os", "initialize_workflow_state")
knowledge_memory_workspace = lazy_service("app.services.engineering_knowledge_memory", "knowledge_memory_workspace")
local_ai_status = lazy_service("app.services.local_ai", "local_ai_status")
log_document_activity = lazy_service("app.services.audit", "log_document_activity")
log_event = lazy_service("app.services.audit", "log_event")
operating_system_workspace = lazy_service("app.services.engineering_intelligence_os", "operating_system_workspace")
search = lazy_service("app.services.infrastructure_ports", "search")
serialize_lesson = lazy_service("app.services.engineering_knowledge_memory", "serialize_lesson")
serialize_workflow = lazy_service("app.services.engineering_intelligence_os", "serialize_workflow")
similar_cad = lazy_service("app.services.geometry_similarity", "similar_cad")
simulate_change_impact = lazy_service("app.services.change_intelligence", "simulate_change_impact")
validate_lesson = lazy_service("app.services.engineering_knowledge_memory", "validate_lesson")
workflow_template = lazy_service("app.services.engineering_intelligence_os", "workflow_template")

router = APIRouter(tags=["context:intelligence_search"])

@router.get("/local-ai/health")
async def local_ai_health(identity: Identity = Depends(get_identity)):
    return await local_ai_status()

@router.post("/search", response_model=list[SearchHit])
def search_api(req: SearchRequest, identity: Identity = Depends(get_identity), db: Session = Depends(get_db)):
    hits = search(req.query, req.limit, identity.groups, req.part_number, req.revision, req.doc_type, req.project_code, req.manufacturing_area)
    log_event(db, identity.user, "SEARCH", details={"query": req.query, "results": len(hits)})
    return hits

@router.post("/ask", response_model=AskResponse)
async def ask_api(req: AskRequest, identity: Identity = Depends(get_identity), db: Session = Depends(get_db)):
    answer, sources, generated, plan, confidence = await ask(req.query, req.limit, identity.groups, req.part_number, req.revision, req.doc_type, req.project_code, req.manufacturing_area, req.conversation)
    source_ids = [s["document_id"] for s in sources]
    log_event(db, identity.user, "ASK", details={"query": req.query, "source_ids": source_ids, "generated": generated, "plan": plan})
    for document_id in sorted(set(source_ids)):
        doc = db.get(Document, document_id)
        if doc and _allowed(doc, identity):
            log_document_activity(db, doc.id, identity.user, "AI_QUESTION", "Документ использован в ответе ИИ", {
                "query": req.query, "generated": generated, "confidence": confidence, "answer_excerpt": answer[:500],
            })
    return AskResponse(answer=answer, sources=sources, generated=generated, query_plan=plan, confidence=confidence)

@router.post("/agent/run")
def agent_run(req: AgentRequest, identity: Identity = Depends(get_identity), db: Session = Depends(get_db)):
    result = execute_engineering_workflow(db, req.instruction, identity.user, _visible_ids(db, identity))
    log_event(db, identity.user, "AGENT_WORKFLOW", details={"instruction": req.instruction, "action": result.get("action")})
    return result

@router.post("/impact")
def impact(req: ImpactRequest, identity: Identity = Depends(get_identity), db: Session = Depends(get_db)):
    result = analyze_change_impact(db, req.part_number, req.from_revision, req.to_revision, req.max_depth, _visible_ids(db, identity))
    log_event(db, identity.user, "CHANGE_IMPACT", "part", req.part_number.upper(), {"from": req.from_revision, "to": req.to_revision, "risk": result.get("risk_score")})
    return result

@router.get("/documents/{document_id}/similar")
def similar(document_id: str, limit: int = 10, identity: Identity = Depends(get_identity), db: Session = Depends(get_db)):
    source = db.get(Document, document_id)
    if not source or not _allowed(source, identity):
        raise HTTPException(404)
    hits = similar_cad(db, document_id, min(max(limit, 1), 50))
    visible = {d.id for d in _visible_docs(db, identity)}
    result = [x for x in hits if x["document_id"] in visible]
    log_document_activity(db, source.id, identity.user, "SIMILARITY_SEARCH", "Выполнен поиск похожих 3D-моделей", {"results": len(result)})
    return result

@router.post("/graph/{part_number}/sync")
def graph_sync(part_number: str, identity: Identity = Depends(get_identity), db: Session = Depends(get_db)):
    if not _is_admin(identity):
        raise HTTPException(403, "Admin group required")
    result = graph_sync_part(db, part_number)
    log_event(db, identity.user, "GRAPH_SYNC", "part", part_number.upper(), result)
    return result

@router.get("/graph/{part_number}/neighborhood")
def graph_neighborhood_api(part_number: str, depth: int = 3, identity: Identity = Depends(get_identity), db: Session = Depends(get_db)):
    # ACL gate requires at least one visible document for the requested part.
    docs = [d for d in db.scalars(select(Document).where(Document.part_number == part_number.upper())).all() if _allowed(d, identity)]
    if not docs:
        raise HTTPException(404)
    return graph_neighborhood(part_number, depth, {d.id for d in docs})

@router.get("/projects/{project_code}/digital-thread")
def project_digital_thread(project_code: str, manufacturing_area: str | None = None, focus_part: str | None = None, depth: int = 3, max_nodes: int = 280, identity: Identity = Depends(get_identity), db: Session = Depends(get_db)):
    project, visible_doc_ids, visible_parts, allowed_areas = _architecture_context(db, project_code, identity, manufacturing_area)
    try:
        return engineering_digital_thread(db, project.code, visible_doc_ids, visible_parts, manufacturing_area, allowed_areas, focus_part, depth, max_nodes)
    except LookupError as exc:
        raise HTTPException(404, str(exc)) from exc

@router.get("/projects/{project_code}/change-intelligence")
def project_change_intelligence(project_code: str, manufacturing_area: str | None = None, identity: Identity = Depends(get_identity), db: Session = Depends(get_db)):
    project, visible_doc_ids, visible_parts, allowed_areas = _architecture_context(db, project_code, identity, manufacturing_area)
    return change_intelligence_workspace(db, project.code, visible_doc_ids, visible_parts, manufacturing_area, allowed_areas)

@router.post("/projects/{project_code}/change-impact-simulate")
def project_change_impact_simulate(project_code: str, req: ChangeSimulationRequest, manufacturing_area: str | None = None, identity: Identity = Depends(get_identity), db: Session = Depends(get_db)):
    project, visible_doc_ids, visible_parts, allowed_areas = _architecture_context(db, project_code, identity, manufacturing_area)
    try:
        result = simulate_change_impact(db, project.code, visible_doc_ids, visible_parts, req.model_dump(), manufacturing_area, allowed_areas)
    except LookupError as exc:
        raise HTTPException(404, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    log_event(db, identity.user, "CHANGE_IMPACT_SIMULATED", "project", project.code, {"part_number": req.part_number.upper(), "changed_fields": result.get("changed_fields", []), "simulation_only": True})
    return result

@router.post("/projects/{project_code}/digital-thread/ask")
async def ask_digital_thread_api(project_code: str, req: DigitalThreadAskRequest, manufacturing_area: str | None = None, identity: Identity = Depends(get_identity), db: Session = Depends(get_db)):
    project, visible_doc_ids, visible_parts, allowed_areas = _architecture_context(db, project_code, identity, manufacturing_area)
    focus = req.focus_part.strip().upper() if req.focus_part else None
    try:
        thread = engineering_digital_thread(db, project.code, visible_doc_ids, visible_parts, manufacturing_area, allowed_areas, focus, 4, 350)
    except LookupError as exc:
        raise HTTPException(404, str(exc)) from exc
    workspace = change_intelligence_workspace(db, project.code, visible_doc_ids, visible_parts, manufacturing_area, allowed_areas)
    answer, sources, generated, plan, confidence = await ask(req.query, req.limit, identity.groups, focus, None, None, project.code, manufacturing_area, req.conversation)
    facts = deterministic_thread_facts(thread, workspace, focus)
    combined = "Engineering Digital Thread (детерминированные факты):\n- " + "\n- ".join(facts) + "\n\nRAG по доступной документации:\n" + answer
    source_ids = [x.get("document_id") for x in sources if x.get("document_id")]
    log_event(db, identity.user, "ASK_DIGITAL_THREAD", "project", project.code, {"query": req.query, "focus_part": focus, "source_ids": source_ids, "generated": generated})
    return {"answer": combined, "sources": sources, "generated": generated, "query_plan": plan, "confidence": confidence, "digital_thread_facts": facts, "focus_part": focus, "advisory_only": True}

@router.get("/projects/{project_code}/engineering-memory")
def project_engineering_memory(project_code: str, q: str = "", part_number: str | None = None, manufacturing_area: str | None = None, scope: str = "project", source_type: str | None = None, limit: int = 12, identity: Identity = Depends(get_identity), db: Session = Depends(get_db)):
    project=_get_visible_project(db,project_code,identity)
    cases=_knowledge_cases(db,project,identity,manufacturing_area,scope)
    source_types=[x.strip() for x in (source_type or "").split(",") if x.strip()]
    return knowledge_memory_workspace(cases,q,part_number,manufacturing_area,source_types,limit) | {"scope":scope,"project_code":project.code,"portfolio_projects":sorted({c["project_code"] for c in cases})}

@router.post("/projects/{project_code}/engineering-memory/ask")
def ask_engineering_memory(project_code: str, req: KnowledgeMemoryAskRequest, manufacturing_area: str | None = None, identity: Identity = Depends(get_identity), db: Session = Depends(get_db)):
    project=_get_visible_project(db,project_code,identity)
    cases=_knowledge_cases(db,project,identity,manufacturing_area,req.scope)
    out=knowledge_memory_workspace(cases,req.query,req.part_number,manufacturing_area,req.source_types,req.limit)
    answer=build_memory_answer(req.query,out["matches"])
    log_event(db,identity.user,"ASK_ENGINEERING_MEMORY","project",project.code,{"query":req.query,"scope":req.scope,"part_number":req.part_number,"case_ids":[x["case_id"] for x in out["matches"][:10]]})
    return {"answer":answer,"matches":out["matches"],"metrics":out["metrics"],"scope":req.scope,"deterministic_similarity":True,"advisory_only":True}

@router.post("/projects/{project_code}/engineering-memory/lessons/promote")
def promote_engineering_lesson(project_code: str, req: KnowledgeLessonPromoteRequest, identity: Identity = Depends(get_identity), db: Session = Depends(get_db)):
    project, visible_doc_ids, visible_parts, allowed_areas=_architecture_context(db,project_code,identity,None)
    cases=collect_project_cases(db,project.code,visible_doc_ids,visible_parts,None,allowed_areas,True)
    case=next((c for c in cases if c["case_id"]==req.case_id and c["source_type"]!="lesson"),None)
    if not case: raise HTTPException(404,"Historical case not found")
    try:
        row=create_lesson_from_case(db,case,created_by=identity.user,title=req.title,problem=req.problem,decision=req.decision,outcome=req.outcome,effectiveness=req.effectiveness,tags=req.tags)
    except ValueError as exc:
        raise HTTPException(400,str(exc)) from exc
    log_event(db,identity.user,"ENGINEERING_LESSON_CREATED","project",project.code,{"lesson_id":row.id,"source_case_id":req.case_id})
    return serialize_lesson(row)

@router.patch("/projects/{project_code}/engineering-memory/lessons/{lesson_id}")
def update_engineering_lesson(project_code: str, lesson_id: str, req: KnowledgeLessonUpdateRequest, identity: Identity = Depends(get_identity), db: Session = Depends(get_db)):
    project, visible_doc_ids, visible_parts, allowed_areas=_architecture_context(db,project_code,identity,None)
    row=db.get(EngineeringLesson,lesson_id)
    if not row or row.project_code!=project.code or (row.part_number and row.part_number not in visible_parts) or not set(row.evidence_document_ids or []).issubset(visible_doc_ids):
        raise HTTPException(404,"Engineering lesson not found")
    target_status=req.status or row.status
    if (row.status=="validated" or target_status in {"validated","archived"}) and not _is_admin(identity):
        raise HTTPException(403,"Engineering admin required to validate/archive Lessons Learned")
    try:
        row=validate_lesson(db,row,validator=identity.user,status=target_status,outcome=req.outcome,effectiveness=req.effectiveness)
    except ValueError as exc:
        raise HTTPException(400,str(exc)) from exc
    log_event(db,identity.user,"ENGINEERING_LESSON_UPDATED","project",project.code,{"lesson_id":row.id,"status":row.status,"effectiveness":row.effectiveness})
    return serialize_lesson(row)

@router.get("/projects/{project_code}/engineering-os")
def get_engineering_os(project_code: str, role: str = "engineering", manufacturing_area: str | None = None, identity: Identity = Depends(get_identity), db: Session = Depends(get_db)):
    project, visible_doc_ids, visible_parts, allowed_areas = _launch_project_context(db, project_code, identity, manufacturing_area)
    return operating_system_workspace(db, project, visible_doc_ids, visible_parts, manufacturing_area, allowed_areas, identity.user, role)

@router.post("/projects/{project_code}/engineering-os/ask")
def ask_engineering_os(project_code: str, req: EngineeringOSAskRequest, identity: Identity = Depends(get_identity), db: Session = Depends(get_db)):
    project, visible_doc_ids, visible_parts, allowed_areas = _launch_project_context(db, project_code, identity, req.manufacturing_area)
    ws = operating_system_workspace(db, project, visible_doc_ids, visible_parts, req.manufacturing_area, allowed_areas, identity.user, req.role)
    return engineering_os_answer(ws, req.query)

@router.post("/projects/{project_code}/engineering-os/workflows")
def create_engineering_workflow(project_code: str, req: EngineeringWorkflowCreateRequest, identity: Identity = Depends(get_identity), db: Session = Depends(get_db)):
    project, visible_doc_ids, _, allowed_areas = _launch_project_context(db, project_code, identity, req.manufacturing_area)
    if req.manufacturing_area:
        _validate_quality_area(db, project, identity, req.manufacturing_area)
    if not set(req.evidence_document_ids or []).issubset(visible_doc_ids):
        raise HTTPException(400, "Evidence document is unavailable or outside current ACL context")
    if (req.trigger_id or req.source_object_refs) and not req.evidence_document_ids:
        raise HTTPException(400, "Triggered/source-linked workflow requires visible evidence")
    try:
        state = initialize_workflow_state(req.workflow_type)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    code = req.code.strip().upper()
    if db.scalar(select(EngineeringWorkflowCase).where(EngineeringWorkflowCase.project_code == project.code, EngineeringWorkflowCase.code == code)):
        raise HTTPException(409, "Workflow code already exists")
    steps = workflow_template(req.workflow_type)
    row = EngineeringWorkflowCase(project_code=project.code, manufacturing_area=req.manufacturing_area, code=code,
                                  workflow_type=req.workflow_type, title=req.title.strip(), status="active", priority=req.priority.lower(),
                                  owner=req.owner or identity.user, current_stage=steps[0][0] if steps else None,
                                  trigger_type=req.trigger_type, trigger_id=req.trigger_id, target_gate=req.target_gate,
                                  due_at=_parse_iso_datetime(req.due_at), workflow_state_json=state, source_object_refs=req.source_object_refs,
                                  evidence_document_ids=list(dict.fromkeys(req.evidence_document_ids)), notes=req.notes,
                                  metadata_json=req.metadata, human_approval_required=True, created_by=identity.user)
    db.add(row); db.commit(); db.refresh(row)
    log_event(db, identity.user, "ENGINEERING_OS_WORKFLOW_CREATED", "project", project.code,
              {"workflow_id": row.id, "code": row.code, "workflow_type": row.workflow_type, "trigger_type": row.trigger_type, "trigger_id": row.trigger_id})
    return serialize_workflow(row)

@router.patch("/projects/{project_code}/engineering-os/workflows/{workflow_id}")
def update_engineering_workflow(project_code: str, workflow_id: str, req: EngineeringWorkflowUpdateRequest, identity: Identity = Depends(get_identity), db: Session = Depends(get_db)):
    project, visible_doc_ids, _, allowed_areas = _launch_project_context(db, project_code, identity)
    row = db.get(EngineeringWorkflowCase, workflow_id)
    if not row or row.project_code != project.code or (row.manufacturing_area and row.manufacturing_area not in allowed_areas) or not set(row.evidence_document_ids or []).issubset(visible_doc_ids):
        raise HTTPException(404, "Engineering workflow not found")
    values = req.model_dump(exclude_unset=True)
    if "evidence_document_ids" in values:
        ids = values.pop("evidence_document_ids") or []
        if not set(ids).issubset(visible_doc_ids): raise HTTPException(400, "Evidence document is unavailable or outside current ACL context")
        row.evidence_document_ids = list(dict.fromkeys(ids))
    requested_status = values.pop("status", None)
    if requested_status:
        allowed_status = {"active", "blocked", "ready_for_close", "closed", "cancelled"}
        if requested_status not in allowed_status: raise HTTPException(400, "Unsupported workflow status")
        if requested_status in {"closed", "cancelled"} and not _is_admin(identity):
            raise HTTPException(403, "Engineering admin required for final workflow closure/cancellation")
        row.status = requested_status
    complete = bool(values.pop("complete_current_stage", False))
    block_reason = values.pop("block_reason", None)
    for key in ("priority", "owner", "notes"):
        if key in values: setattr(row, key, values[key])
    advance_workflow_case(row, complete_current_stage=complete, block_reason=block_reason)
    db.commit(); db.refresh(row)
    log_event(db, identity.user, "ENGINEERING_OS_WORKFLOW_UPDATED", "project", project.code,
              {"workflow_id": row.id, "status": row.status, "current_stage": row.current_stage, "complete_current_stage": complete, "blocked": bool(block_reason)})
    return serialize_workflow(row)

