from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
from typing import Iterable

from sqlalchemy import select
from sqlalchemy.orm import Session
from app.platform.actions import normalize_action, normalize_decision

from app.services.ux_simplification import build_role_landing
from app.db.models import EngineeringWorkflowCase, Project
from app.services.change_intelligence import change_intelligence_workspace
from app.services.closed_loop_engineering import closed_loop_workspace
from app.services.configuration_release_assurance import configuration_release_assurance_workspace
from app.services.field_reliability_product_lifecycle import field_reliability_workspace
from app.services.program_control import program_control_workspace
from app.services.series_quality_manufacturing_intelligence import series_quality_workspace
from app.services.vehicle_build_launch_intelligence import vehicle_build_launch_workspace


ROLE_PROFILES = {
    "engineering": {"label": "Engineering", "domains": ["digital_thread", "change", "configuration", "program", "closed_loop"]},
    "manufacturing": {"label": "Manufacturing Engineering", "domains": ["configuration", "build_launch", "series", "program", "change"]},
    "quality": {"label": "Quality", "domains": ["closed_loop", "build_launch", "series", "field", "change"]},
    "supplier": {"label": "Supplier / Localization", "domains": ["change", "closed_loop", "configuration", "series", "program"]},
    "program": {"label": "Program / Launch", "domains": ["program", "configuration", "change", "build_launch", "closed_loop"]},
    "field": {"label": "Field Reliability", "domains": ["field", "series", "closed_loop", "change", "configuration"]},
    "leadership": {"label": "Engineering Leadership", "domains": ["program", "configuration", "closed_loop", "series", "field", "change"]},
    "engineering_admin": {"label": "Engineering Admin", "domains": ["digital_thread", "change", "closed_loop", "program", "configuration", "build_launch", "series", "field"]},
}

WORKFLOW_TEMPLATES = {
    "change_to_release": [
        ("impact", "Impact analysis"), ("technical_review", "Technical review"), ("vv", "V&V refresh"),
        ("configuration", "Configuration / MBOM alignment"), ("release_review", "Human release review"),
    ],
    "defect_to_change": [
        ("contain", "Containment"), ("root_cause", "Root-cause investigation"), ("8d", "8D corrective action"),
        ("change", "ECR / ECO"), ("effectiveness", "Effectiveness review"),
    ],
    "field_to_change": [
        ("field_triage", "Field triage"), ("exposure", "Exposure population"), ("dfmea_vv", "DFMEA / V&V review"),
        ("change", "Engineering change"), ("field_effectiveness", "Field effectiveness"),
    ],
    "launch_blocker": [
        ("triage", "Blocker triage"), ("owner_action", "Owner action"), ("evidence", "Evidence refresh"),
        ("gate_review", "Human gate review"),
    ],
    "supplier_issue": [
        ("incoming_quality", "Incoming quality containment"), ("8d", "Supplier 8D"), ("ppap", "PPAP refresh"),
        ("run_at_rate", "Run@Rate / capacity"), ("release_review", "Human release review"),
    ],
}

SEVERITY_SCORE = {"critical": 100, "high": 80, "medium": 55, "warning": 50, "low": 30, "info": 10, "normal": 35}
CLOSED_WORKFLOW = {"closed", "cancelled", "completed", "archived"}


def _iso(value):
    return value.isoformat() if value else None


def _area_ok(area: str | None, requested: str | None, allowed: set[str]) -> bool:
    if area and area not in allowed:
        return False
    if requested and area and area != requested:
        return False
    return True


def _evidence_ok(ids: Iterable[str] | None, visible_document_ids: set[str]) -> bool:
    return set(ids or []).issubset(visible_document_ids)


def workflow_template(workflow_type: str) -> list[tuple[str, str]]:
    if workflow_type not in WORKFLOW_TEMPLATES:
        raise ValueError(f"Unsupported workflow_type: {workflow_type}")
    return WORKFLOW_TEMPLATES[workflow_type]


def initialize_workflow_state(workflow_type: str) -> dict:
    steps = workflow_template(workflow_type)
    return {"completed_stages": [], "blocked_stage": None, "block_reason": None,
            "steps": [{"code": c, "label": label} for c, label in steps]}


def serialize_workflow(x: EngineeringWorkflowCase) -> dict:
    state = x.workflow_state_json or {}
    steps = state.get("steps") or [{"code": c, "label": l} for c, l in workflow_template(x.workflow_type)]
    completed = set(state.get("completed_stages") or [])
    rendered = [{**s, "status": "completed" if s["code"] in completed else ("blocked" if s["code"] == state.get("blocked_stage") else ("current" if s["code"] == x.current_stage else "pending"))} for s in steps]
    progress = round(len(completed) * 100 / max(len(steps), 1), 1)
    return {"id": x.id, "project_code": x.project_code, "manufacturing_area": x.manufacturing_area, "code": x.code,
            "workflow_type": x.workflow_type, "title": x.title, "status": x.status, "priority": x.priority, "owner": x.owner,
            "current_stage": x.current_stage, "trigger_type": x.trigger_type, "trigger_id": x.trigger_id, "target_gate": x.target_gate,
            "due_at": _iso(x.due_at), "progress_pct": progress, "steps": rendered, "state": state,
            "source_object_refs": x.source_object_refs or [], "evidence_document_ids": x.evidence_document_ids or [], "notes": x.notes,
            "human_approval_required": x.human_approval_required, "created_by": x.created_by, "created_at": _iso(x.created_at), "updated_at": _iso(x.updated_at)}


def visible_workflow_cases(db: Session, project_code: str, visible_document_ids: set[str], manufacturing_area: str | None, allowed_area_codes: set[str]) -> list[EngineeringWorkflowCase]:
    return [x for x in db.scalars(select(EngineeringWorkflowCase).where(EngineeringWorkflowCase.project_code == project_code)).all()
            if _area_ok(x.manufacturing_area, manufacturing_area, allowed_area_codes) and _evidence_ok(x.evidence_document_ids, visible_document_ids)]


def advance_workflow_case(x: EngineeringWorkflowCase, *, complete_current_stage: bool = False, block_reason: str | None = None) -> None:
    state = dict(x.workflow_state_json or initialize_workflow_state(x.workflow_type))
    steps = state.get("steps") or [{"code": c, "label": l} for c, l in workflow_template(x.workflow_type)]
    codes = [s["code"] for s in steps]
    if x.current_stage not in codes:
        x.current_stage = codes[0] if codes else None
    if block_reason:
        state["blocked_stage"] = x.current_stage
        state["block_reason"] = block_reason
        x.status = "blocked"
    elif complete_current_stage and x.current_stage:
        completed = list(dict.fromkeys((state.get("completed_stages") or []) + [x.current_stage]))
        state["completed_stages"] = completed
        state["blocked_stage"] = None
        state["block_reason"] = None
        idx = codes.index(x.current_stage)
        if idx + 1 < len(codes):
            x.current_stage = codes[idx + 1]
            x.status = "active"
        else:
            x.status = "ready_for_close"
    x.workflow_state_json = state


def _priority(severity: str | None, due_at: str | None = None) -> tuple[str, int]:
    sev = (severity or "medium").lower()
    score = SEVERITY_SCORE.get(sev, 50)
    if due_at:
        try:
            due = datetime.fromisoformat(due_at.replace("Z", "+00:00"))
            if due.tzinfo is None: due = due.replace(tzinfo=timezone.utc)
            days = (due - datetime.now(timezone.utc)).total_seconds() / 86400
            if days < 0: score += 20
            elif days <= 7: score += 10
        except Exception:
            pass
    band = "critical" if score >= 95 else "high" if score >= 75 else "medium" if score >= 45 else "low"
    return band, min(score, 120)


def _action(domain: str, severity: str, title: str, reason: str, *, source_type: str, source_id: str | None = None,
            part_number: str | None = None, manufacturing_area: str | None = None, owner: str | None = None,
            due_at: str | None = None, decision_required: bool = False) -> dict:
    band, score = _priority(severity, due_at)
    return {"domain": domain, "priority": band, "priority_score": score, "title": title, "reason": reason, "source_type": source_type,
            "source_id": source_id, "part_number": part_number, "manufacturing_area": manufacturing_area, "owner": owner, "due_at": due_at,
            "decision_required": decision_required}


def _domain_band(value: str | None) -> str:
    v = (value or "NOT_CONFIGURED").upper()
    if v in {"BLOCKED", "CRITICAL"}: return "RED"
    if v in {"NEEDS_REVIEW", "REVIEW_REQUIRED"}: return "AMBER"
    if v in {"CANDIDATE", "READY", "MATCH", "EXITED"}: return "GREEN"
    return v if v in {"GREEN", "AMBER", "RED", "NOT_CONFIGURED"} else "AMBER"


def operating_system_workspace(db: Session, project: Project, visible_document_ids: set[str], visible_part_numbers: set[str],
                               manufacturing_area: str | None, allowed_area_codes: set[str], user: str, role: str = "engineering") -> dict:
    role = role if role in ROLE_PROFILES else "engineering"
    profile = ROLE_PROFILES[role]

    change = change_intelligence_workspace(db, project.code, visible_document_ids, visible_part_numbers, manufacturing_area, allowed_area_codes)
    closed = closed_loop_workspace(db, project.code, visible_document_ids, visible_part_numbers, manufacturing_area, allowed_area_codes)
    program = program_control_workspace(db, project, visible_document_ids, visible_part_numbers, manufacturing_area, allowed_area_codes)
    config = configuration_release_assurance_workspace(db, project, visible_document_ids, visible_part_numbers, manufacturing_area, allowed_area_codes)
    build = vehicle_build_launch_workspace(db, project.code, visible_document_ids, visible_part_numbers, manufacturing_area, allowed_area_codes)
    series = series_quality_workspace(db, project.code, visible_document_ids, visible_part_numbers, manufacturing_area, allowed_area_codes)
    field = field_reliability_workspace(db, project.code, visible_document_ids, visible_part_numbers, manufacturing_area, allowed_area_codes)
    workflows = visible_workflow_cases(db, project.code, visible_document_ids, manufacturing_area, allowed_area_codes)

    actions: list[dict] = []
    for x in change.get("action_queue", []):
        actions.append(_action("change", x.get("priority", "high"), x.get("title", "Engineering change action"), x.get("reason", "Change intelligence"),
                               source_type=x.get("type", "change"), source_id=x.get("entity_id"), part_number=x.get("part_number"), manufacturing_area=x.get("manufacturing_area")))
    for x in program.get("top_actions", []):
        actions.append(_action("program", x.get("severity", "high"), x.get("action", "Program blocker"), x.get("why", "Program control blocker"),
                               source_type=x.get("source_type", "program"), source_id=x.get("source_id"), manufacturing_area=x.get("manufacturing_area"), owner=x.get("owner"), due_at=x.get("due_at"), decision_required=True))
    for x in closed.get("early_warnings", []):
        actions.append(_action("closed_loop", x.get("severity", "medium"), x.get("title", "Closed-loop signal"), x.get("detail", "Closed-loop engineering signal"),
                               source_type=x.get("type", "closed_loop"), source_id=x.get("entity_id"), decision_required=x.get("type") in {"ineffective_change", "residual_risk", "expired_deviation"}))
    for x in config.get("manufacturing_handover", {}).get("blockers", []):
        actions.append(_action("configuration", x.get("severity", "high"), x.get("title") or x.get("type", "Configuration blocker"), x.get("reason") or "Manufacturing handover blocker",
                               source_type=x.get("type", "configuration"), source_id=x.get("id"), part_number=x.get("part_number"), decision_required=True))
    for x in build.get("recurrence", [])[:20]:
        actions.append(_action("build_launch", "high", f"Recurring build issue: {x.get('failure_mode') or x.get('title') or 'defect'}", f"Observed in {x.get('affected_builds') or x.get('builds') or x.get('count') or 'multiple'} builds",
                               source_type="build_recurrence", source_id=x.get("defect_id"), part_number=x.get("part_number")))
    for x in build.get("safe_launch", {}).get("controls", []):
        if x.get("exit_candidate"):
            actions.append(_action("build_launch", "medium", f"Safe Launch exit review: {x.get('code')}", "Exit criteria appear met; human approval is still required.",
                                   source_type="safe_launch_exit", source_id=x.get("id"), part_number=x.get("part_number"), decision_required=True))
    for x in series.get("early_series_signals", []):
        actions.append(_action("series", x.get("severity", "medium"), x.get("title", "Series quality signal"), x.get("detail", "Series quality signal"),
                               source_type=x.get("type", "series"), source_id=x.get("id"), decision_required=x.get("severity") in {"critical", "high"}))
    for x in field.get("dfmea_feedback", []):
        if x.get("status") == "DFMEA_REVIEW_REQUIRED":
            actions.append(_action("field", "high", f"DFMEA review: {x.get('failure_mode') or x.get('failure_family')}", x.get("reason", "Field occurrence may exceed DFMEA assumption"),
                                   source_type="dfmea_review", source_id=x.get("dfmea_id"), part_number=x.get("part_number"), decision_required=True))
    for x in field.get("validation_effectiveness", []):
        if x.get("status") == "VALIDATION_COVERAGE_GAP":
            actions.append(_action("field", "high", f"Validation coverage gap: {x.get('failure_family')}", x.get("reason", "Field failure outside recorded validation coverage"),
                                   source_type="validation_gap", part_number=x.get("part_number"), decision_required=True))
    for x in field.get("campaign_candidates", []):
        actions.append(_action("field", "critical", f"Field campaign assessment: {x.get('failure_family')}", f"{x.get('claims')} accessible claims; review by Engineering/Quality/Legal required.",
                               source_type="campaign_review", part_number=x.get("part_number"), decision_required=True))
    for wf in workflows:
        if wf.status in CLOSED_WORKFLOW:
            continue
        sev = "critical" if wf.priority == "critical" else "high" if wf.priority == "high" else "medium"
        actions.append(_action("workflow", sev, f"{wf.code} · {wf.title}", f"Current stage: {wf.current_stage or 'not initialized'}",
                               source_type="workflow", source_id=wf.id, manufacturing_area=wf.manufacturing_area, owner=wf.owner, due_at=_iso(wf.due_at), decision_required=wf.status in {"blocked", "ready_for_close"}))

    dedup = {}
    for x in actions:
        key = (x.get("domain"), x.get("source_type"), x.get("source_id"), x.get("title"))
        if key not in dedup or x["priority_score"] > dedup[key]["priority_score"]:
            dedup[key] = x
    actions = [{**x, **normalize_action(x)} for x in sorted(dedup.values(), key=lambda x: (-x["priority_score"], x["title"]))[:250]]
    focused = [x for x in actions if x["domain"] in set(profile["domains"]) or x["domain"] == "workflow"]
    assigned = [x for x in actions if x.get("owner") == user]
    decisions = [{**x, **normalize_decision(x)} for x in focused if x.get("decision_required")]

    coverage = change.get("coverage", {})
    cov_values = [float(v) for v in coverage.values() if isinstance(v, (int, float))] if isinstance(coverage, dict) else []
    digital_score = round(sum(cov_values) / len(cov_values), 1) if cov_values else None
    domains = {
        "digital_thread": {"band": "GREEN" if digital_score is not None and digital_score >= 90 else "AMBER" if digital_score is not None else "NOT_CONFIGURED", "score": digital_score},
        "change": {"band": "RED" if change.get("counts", {}).get("stale", 0) else "AMBER" if change.get("counts", {}).get("actions", 0) else "GREEN", "count": change.get("counts", {}).get("actions", 0)},
        "closed_loop": {"band": _domain_band(closed.get("release_confidence", {}).get("band")), "score": closed.get("release_confidence", {}).get("overall")},
        "program": {"band": _domain_band(program.get("gate_forecast", {}).get("band")), "score": program.get("maturity", {}).get("overall")},
        "configuration": {"band": _domain_band(config.get("confidence", {}).get("band")), "score": config.get("confidence", {}).get("overall")},
        "build_launch": {"band": _domain_band(build.get("safe_launch", {}).get("status")), "count": build.get("launch_pulse", {}).get("linked_defects", 0)},
        "series": {"band": _domain_band(series.get("series_health", {}).get("status")), "count": series.get("counts", {}).get("observations", 0)},
        "field": {"band": _domain_band(field.get("field_health", {}).get("band")), "count": field.get("counts", {}).get("claims", 0)},
    }
    visible_domains = {k: v for k, v in domains.items() if k in profile["domains"]}
    rank = {"RED": 3, "AMBER": 2, "GREEN": 1, "NOT_CONFIGURED": 0}
    overall_band = max((v["band"] for v in visible_domains.values()), key=lambda b: rank.get(b, 2), default="NOT_CONFIGURED")
    workflow_payload = [serialize_workflow(x) for x in sorted(workflows, key=lambda x: x.updated_at or x.created_at, reverse=True)]
    result = {
        "schema_version": "mgc-engineering-intelligence-os-v1", "project": {"code": project.code, "name": project.name, "phase": project.phase},
        "manufacturing_area": manufacturing_area, "role": {"code": role, **profile}, "available_roles": [{"code": k, **v} for k, v in ROLE_PROFILES.items()],
        "cockpit": {"band": overall_band, "domains": visible_domains, "all_domains": domains, "next_gate": program.get("target_gate"),
                    "program_forecast": program.get("gate_forecast"), "top_signal": focused[0] if focused else None},
        "action_inbox": {"focused": focused[:80], "all_accessible": actions[:120], "assigned_to_me": assigned[:80], "counts": {"focused": len(focused), "all": len(actions), "mine": len(assigned), "critical": sum(x["priority"] == "critical" for x in focused), "high": sum(x["priority"] == "high" for x in focused)}},
        "decision_queue": decisions[:50], "workflows": workflow_payload,
        "workflow_templates": [{"code": k, "steps": [{"code": c, "label": l} for c, l in v]} for k, v in WORKFLOW_TEMPLATES.items()],
        "command_brief": _command_brief(project, role, overall_band, visible_domains, focused, decisions, workflow_payload),
        "governance": {"advisory_only": True, "role_is_ui_focus_not_authorization": True, "acl_remains_authoritative": True,
                       "not_project_tracker_or_plm_erp_mes_qms": True, "no_automatic_engineering_decision": True, "human_approval_required": True,
                       "cpu_only_deterministic_core": True},
    }
    result["ux_landing"] = build_role_landing(result)
    return result


def _command_brief(project: Project, role: str, band: str, domains: dict, actions: list[dict], decisions: list[dict], workflows: list[dict]) -> dict:
    red = [k for k, v in domains.items() if v.get("band") == "RED"]
    amber = [k for k, v in domains.items() if v.get("band") == "AMBER"]
    lines = [f"{project.code}: {band} for role {role}."]
    if red: lines.append("RED domains: " + ", ".join(red) + ".")
    elif amber: lines.append("AMBER domains: " + ", ".join(amber) + ".")
    if actions: lines.append(f"{len(actions)} role-focused actions; top: {actions[0]['title']}.")
    if decisions: lines.append(f"{len(decisions)} items require an explicit human decision/review.")
    active = sum(x["status"] not in CLOSED_WORKFLOW for x in workflows)
    if active: lines.append(f"{active} active cross-domain workflow cases.")
    return {"lines": lines, "generated": False, "evidence_first": True}


def engineering_os_answer(workspace: dict, query: str) -> dict:
    q = query.lower(); lines = []
    if any(k in q for k in ("что делать", "action", "действ", "приоритет", "attention")):
        for x in workspace.get("action_inbox", {}).get("focused", [])[:8]:
            lines.append(f"[{x['priority'].upper()}] {x['title']} — {x['reason']}")
    elif any(k in q for k in ("решен", "decision", "approval", "соглас")):
        for x in workspace.get("decision_queue", [])[:8]: lines.append(f"{x['title']} — {x['reason']}")
    elif any(k in q for k in ("workflow", "процесс", "сквоз", "этап")):
        for x in workspace.get("workflows", [])[:8]: lines.append(f"{x['code']}: {x['current_stage']} · {x['progress_pct']}% · {x['status']}")
    else:
        lines.extend(workspace.get("command_brief", {}).get("lines", []))
    if not lines: lines = ["В доступном engineering evidence нет действий для выбранного role/context."]
    return {"answer": "\n".join(lines), "generated": False, "source": "deterministic_engineering_os", "human_decision_required": True,
            "role_is_ui_focus_not_authorization": True}
