from __future__ import annotations

from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone
from typing import Iterable

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import (
    ChangeEffectivenessReview,
    ChangeRequest,
    EngineeringDeviation,
    EngineeringRequirement,
    EngineeringRisk,
    LaunchReadinessItem,
    LaunchTrial,
    LocalizationItem,
    PPAPSubmission,
    ProcessDefect,
    ProgramDependency,
    Project,
    ProjectArea,
    ProjectMilestone,
    ReleaseBaseline,
    RequirementVerification,
)
from app.services.closed_loop_engineering import serialize_deviation, serialize_risk


DONE_MILESTONE = {"done", "waived", "closed", "complete", "completed"}
DONE_LAUNCH = {"done", "waived", "passed", "approved", "complete", "completed", "closed"}
TERMINAL_CHANGE = {"implemented", "rejected", "cancelled"}
CLOSED_RISK = {"closed", "accepted"}
BAD_EFFECTIVENESS = {"ineffective", "verified_ineffective"}
GATE_RANK = {"design_freeze": 0, "release": 1, "sop": 2, "audit": 3, "engineering": 4}


def _utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


def _iso(value: datetime | None) -> str | None:
    v = _utc(value)
    return v.isoformat() if v else None


def _area_ok(area: str | None, requested: str | None, allowed: set[str]) -> bool:
    if area and area not in allowed:
        return False
    return not requested or area in {None, requested}


def _doc_ok(ids: Iterable[str] | None, visible_document_ids: set[str]) -> bool:
    values = set(ids or [])
    return not values or values.issubset(visible_document_ids)


def _part_ok(part_number: str | None, visible_part_numbers: set[str]) -> bool:
    return not part_number or part_number in visible_part_numbers


def _gate_kind(value: str | None) -> str:
    text = (value or "engineering").strip().lower().replace("-", "_").replace(" ", "_")
    if "design" in text and ("freeze" in text or "gate" in text):
        return "design_freeze"
    if text in {"df", "design_freeze"}:
        return "design_freeze"
    if "sop" in text or "launch" in text or "start_of_production" in text:
        return "sop"
    if "release" in text:
        return "release"
    if "audit" in text:
        return "audit"
    return text or "engineering"


def serialize_dependency(x: ProgramDependency, milestones: dict[str, ProjectMilestone] | None = None) -> dict:
    milestones = milestones or {}
    pred = milestones.get(x.predecessor_milestone_id)
    succ = milestones.get(x.successor_milestone_id)
    slack = None
    if pred and succ and pred.due_at and succ.due_at:
        slack = ( _utc(succ.due_at) - _utc(pred.due_at) ).days - int(x.lag_days or 0)
    return {
        "id": x.id,
        "project_code": x.project_code,
        "manufacturing_area": x.manufacturing_area,
        "predecessor_milestone_id": x.predecessor_milestone_id,
        "successor_milestone_id": x.successor_milestone_id,
        "predecessor_code": pred.code if pred else None,
        "predecessor_name": pred.name if pred else None,
        "successor_code": succ.code if succ else None,
        "successor_name": succ.name if succ else None,
        "dependency_type": x.dependency_type,
        "lag_days": int(x.lag_days or 0),
        "criticality": x.criticality,
        "owner": x.owner,
        "notes": x.notes,
        "slack_days": slack,
        "schedule_violation": slack is not None and slack < 0,
        "metadata": x.metadata_json or {},
        "created_by": x.created_by,
        "created_at": _iso(x.created_at),
        "updated_at": _iso(x.updated_at),
    }


def visible_program_rows(
    db: Session,
    project_code: str,
    visible_document_ids: set[str],
    visible_part_numbers: set[str],
    manufacturing_area: str | None,
    allowed_area_codes: set[str],
) -> dict:
    milestones = [
        x for x in db.scalars(select(ProjectMilestone).where(ProjectMilestone.project_code == project_code)).all()
        if _area_ok(x.manufacturing_area, manufacturing_area, allowed_area_codes)
    ]
    milestone_ids = {x.id for x in milestones}
    dependencies = [
        x for x in db.scalars(select(ProgramDependency).where(ProgramDependency.project_code == project_code)).all()
        if x.predecessor_milestone_id in milestone_ids
        and x.successor_milestone_id in milestone_ids
        and _area_ok(x.manufacturing_area, manufacturing_area, allowed_area_codes)
    ]
    launch_items = [
        x for x in db.scalars(select(LaunchReadinessItem).where(LaunchReadinessItem.project_code == project_code)).all()
        if _area_ok(x.manufacturing_area, manufacturing_area, allowed_area_codes)
        and _part_ok(x.part_number, visible_part_numbers)
        and _doc_ok(x.evidence_document_ids, visible_document_ids)
    ]
    trials = [
        x for x in db.scalars(select(LaunchTrial).where(LaunchTrial.project_code == project_code)).all()
        if _area_ok(x.manufacturing_area, manufacturing_area, allowed_area_codes)
        and _part_ok(x.part_number, visible_part_numbers)
        and _doc_ok(x.evidence_document_ids, visible_document_ids)
    ]
    risks = [
        x for x in db.scalars(select(EngineeringRisk).where(EngineeringRisk.project_code == project_code)).all()
        if _area_ok(x.manufacturing_area, manufacturing_area, allowed_area_codes)
        and _part_ok(x.part_number, visible_part_numbers)
        and _doc_ok(x.evidence_document_ids, visible_document_ids)
    ]
    defects = [
        x for x in db.scalars(select(ProcessDefect).where(ProcessDefect.project_code == project_code)).all()
        if _area_ok(x.manufacturing_area, manufacturing_area, allowed_area_codes)
        and _part_ok(x.part_number, visible_part_numbers)
        and _doc_ok(x.evidence_document_ids, visible_document_ids)
    ]
    changes = [
        x for x in db.scalars(select(ChangeRequest)).all()
        if _part_ok(x.part_number, visible_part_numbers)
        and _doc_ok(x.affected_document_ids, visible_document_ids)
        and (x.part_number in visible_part_numbers or getattr(x, "project_code", None) == project_code)
    ]
    requirements = [
        x for x in db.scalars(select(EngineeringRequirement).where(EngineeringRequirement.project_code == project_code)).all()
        if _area_ok(x.manufacturing_area, manufacturing_area, allowed_area_codes)
        and (not x.source_document_id or x.source_document_id in visible_document_ids)
        and (not x.part_numbers or bool(set(x.part_numbers or []) & visible_part_numbers))
    ]
    req_ids = {x.id for x in requirements}
    verifications = [
        x for x in db.scalars(select(RequirementVerification).where(RequirementVerification.project_code == project_code)).all()
        if x.requirement_id in req_ids
        and _area_ok(x.manufacturing_area, manufacturing_area, allowed_area_codes)
        and _doc_ok(x.evidence_document_ids, visible_document_ids)
    ]
    ppap = [
        x for x in db.scalars(select(PPAPSubmission).where(PPAPSubmission.project_code == project_code)).all()
        if _part_ok(x.part_number, visible_part_numbers)
        and _area_ok(x.manufacturing_area, manufacturing_area, allowed_area_codes)
        and _doc_ok(x.evidence_document_ids, visible_document_ids)
    ]
    localization = [
        x for x in db.scalars(select(LocalizationItem).where(LocalizationItem.project_code == project_code)).all()
        if _part_ok(x.part_number, visible_part_numbers)
        and _area_ok(x.manufacturing_area, manufacturing_area, allowed_area_codes)
        and _doc_ok(x.evidence_document_ids, visible_document_ids)
    ]
    effectiveness = [
        x for x in db.scalars(select(ChangeEffectivenessReview).where(ChangeEffectivenessReview.project_code == project_code)).all()
        if _area_ok(x.manufacturing_area, manufacturing_area, allowed_area_codes)
        and _doc_ok(x.evidence_document_ids, visible_document_ids)
    ]
    deviations = [
        x for x in db.scalars(select(EngineeringDeviation).where(EngineeringDeviation.project_code == project_code)).all()
        if _part_ok(x.part_number, visible_part_numbers)
        and _area_ok(x.manufacturing_area, manufacturing_area, allowed_area_codes)
        and _doc_ok(x.evidence_document_ids, visible_document_ids)
    ]
    baselines = [
        x for x in db.scalars(select(ReleaseBaseline).where(ReleaseBaseline.project_code == project_code)).all()
        if _area_ok(x.manufacturing_area, manufacturing_area, allowed_area_codes)
        and set(x.source_document_ids or []).issubset(visible_document_ids)
    ]
    return {
        "milestones": milestones,
        "dependencies": dependencies,
        "launch_items": launch_items,
        "trials": trials,
        "risks": risks,
        "defects": defects,
        "changes": changes,
        "requirements": requirements,
        "verifications": verifications,
        "ppap": ppap,
        "localization": localization,
        "effectiveness": effectiveness,
        "deviations": deviations,
        "baselines": baselines,
    }


def _target_gate(project: Project, milestones: list[ProjectMilestone], now: datetime) -> dict:
    gates = [x for x in milestones if _gate_kind(x.gate) in {"design_freeze", "release", "sop"} and x.status not in DONE_MILESTONE]
    future = [x for x in gates if _utc(x.due_at) and _utc(x.due_at) >= now]
    candidates = future or [x for x in gates if _utc(x.due_at)]
    if candidates:
        row = sorted(candidates, key=lambda x: (_utc(x.due_at), GATE_RANK.get(_gate_kind(x.gate), 9)))[0]
        return {
            "id": row.id,
            "code": row.code,
            "name": row.name,
            "gate": _gate_kind(row.gate),
            "due_at": _iso(row.due_at),
            "status": row.status,
            "virtual": False,
        }
    if project.target_release_at:
        return {
            "id": None,
            "code": "TARGET-RELEASE",
            "name": "Target Release / SOP",
            "gate": "sop",
            "due_at": _iso(project.target_release_at),
            "status": "planned",
            "virtual": True,
        }
    return {"id": None, "code": None, "name": "Target gate not configured", "gate": None, "due_at": None, "status": "unknown", "virtual": True}


def _schedule_forecast(milestones: list[ProjectMilestone], dependencies: list[ProgramDependency], now: datetime) -> dict:
    by_id = {x.id: x for x in milestones}
    forecast: dict[str, datetime] = {}
    for x in milestones:
        due = _utc(x.due_at)
        if not due:
            continue
        if x.status in DONE_MILESTONE:
            forecast[x.id] = due
        else:
            forecast[x.id] = max(due, now) if due < now else due

    # Forward propagation. Cycles are tolerated and surfaced separately; bounded loop prevents runaway.
    for _ in range(max(1, len(milestones) + 2)):
        changed = False
        for edge in dependencies:
            if edge.predecessor_milestone_id not in forecast or edge.successor_milestone_id not in forecast:
                continue
            earliest = forecast[edge.predecessor_milestone_id] + timedelta(days=int(edge.lag_days or 0))
            if earliest > forecast[edge.successor_milestone_id]:
                forecast[edge.successor_milestone_id] = earliest
                changed = True
        if not changed:
            break

    rows = []
    for x in milestones:
        due = _utc(x.due_at)
        f = forecast.get(x.id)
        slip = max(0, (f - due).days) if due and f else None
        rows.append({
            "id": x.id,
            "code": x.code,
            "name": x.name,
            "gate": _gate_kind(x.gate),
            "manufacturing_area": x.manufacturing_area,
            "owner": x.owner,
            "status": x.status,
            "due_at": _iso(due),
            "forecast_due_at": _iso(f),
            "forecast_slip_days": slip,
            "overdue": bool(due and due < now and x.status not in DONE_MILESTONE),
        })
    return {"milestones": rows, "forecast_by_id": forecast}


def _graph_cycles(milestones: list[ProjectMilestone], dependencies: list[ProgramDependency]) -> list[list[str]]:
    valid = {x.id for x in milestones}
    graph = defaultdict(list)
    for e in dependencies:
        if e.predecessor_milestone_id in valid and e.successor_milestone_id in valid:
            graph[e.predecessor_milestone_id].append(e.successor_milestone_id)
    state: dict[str, int] = {}
    stack: list[str] = []
    cycles: list[list[str]] = []

    def visit(node: str):
        state[node] = 1
        stack.append(node)
        for nxt in graph.get(node, []):
            if state.get(nxt, 0) == 0:
                visit(nxt)
            elif state.get(nxt) == 1 and nxt in stack:
                idx = stack.index(nxt)
                cyc = stack[idx:] + [nxt]
                if cyc not in cycles:
                    cycles.append(cyc)
        stack.pop()
        state[node] = 2

    for node in valid:
        if state.get(node, 0) == 0:
            visit(node)
    return cycles[:10]


def critical_dependency_chain(milestones: list[ProjectMilestone], dependencies: list[ProgramDependency], target_id: str | None) -> dict:
    by_id = {x.id: x for x in milestones}
    if not target_id or target_id not in by_id:
        return {"target_milestone_id": target_id, "path": [], "total_slack_days": None, "method": "deterministic_due_date_dependency_slack"}
    incoming = defaultdict(list)
    for e in dependencies:
        if e.predecessor_milestone_id in by_id and e.successor_milestone_id in by_id:
            incoming[e.successor_milestone_id].append(e)

    best: tuple[float, list[ProgramDependency]] | None = None

    def dfs(node: str, edges: list[ProgramDependency], seen: set[str], cumulative_slack: float):
        nonlocal best
        inc = incoming.get(node, [])
        if not inc:
            if best is None or cumulative_slack < best[0]:
                best = (cumulative_slack, list(edges))
            return
        for e in inc:
            if e.predecessor_milestone_id in seen:
                continue
            pred = by_id[e.predecessor_milestone_id]
            succ = by_id[e.successor_milestone_id]
            slack = 3650.0
            if pred.due_at and succ.due_at:
                slack = float((_utc(succ.due_at) - _utc(pred.due_at)).days - int(e.lag_days or 0))
            # High/critical engineering dependencies are treated as lower effective slack.
            slack -= {"critical": 3.0, "high": 1.0}.get(e.criticality, 0.0)
            dfs(e.predecessor_milestone_id, [e] + edges, seen | {e.predecessor_milestone_id}, cumulative_slack + slack)

    dfs(target_id, [], {target_id}, 0.0)
    if best is None:
        return {"target_milestone_id": target_id, "path": [], "total_slack_days": None, "method": "deterministic_due_date_dependency_slack"}
    path = []
    for e in best[1]:
        sx = serialize_dependency(e, by_id)
        path.append({
            "dependency_id": e.id,
            "from": sx["predecessor_code"],
            "from_name": sx["predecessor_name"],
            "to": sx["successor_code"],
            "to_name": sx["successor_name"],
            "lag_days": sx["lag_days"],
            "slack_days": sx["slack_days"],
            "criticality": sx["criticality"],
        })
    return {
        "target_milestone_id": target_id,
        "path": path,
        "total_slack_days": round(best[0], 1),
        "method": "deterministic_due_date_dependency_slack",
        "formal_cpm": False,
        "note": "This is an explainable dependency/slack chain. It is not formal CPM unless planning durations are supplied by the authoritative program system.",
    }


def _score(done: int, total: int, *, fallback: float = 70.0) -> float:
    return round(100.0 * done / total, 1) if total else fallback


def maturity_scores(rows: dict, schedule: dict) -> dict:
    milestones = rows["milestones"]
    milestone_done = sum(x.status in DONE_MILESTONE for x in milestones)
    overdue = sum(x["overdue"] for x in schedule["milestones"])
    program = max(0.0, _score(milestone_done, len(milestones), fallback=70.0) - overdue * 8.0)

    launch_required = [x for x in rows["launch_items"] if x.required]
    launch_good = sum(x.status in DONE_LAUNCH and (not x.evidence_document_ids or bool(x.evidence_document_ids)) for x in launch_required)
    trial_good = sum(x.status in {"passed", "complete", "completed"} and bool(x.evidence_document_ids) for x in rows["trials"])
    launch_total = len(launch_required) + len(rows["trials"])
    launch = _score(launch_good + trial_good, launch_total, fallback=70.0)

    vv_total = len(rows["verifications"])
    vv_good = sum(x.status in {"passed", "waived"} and bool(x.evidence_document_ids) for x in rows["verifications"])
    vv = _score(vv_good, vv_total, fallback=70.0)

    ppap_total = len(rows["ppap"])
    ppap_good = sum(x.status == "approved" and bool(x.evidence_document_ids) for x in rows["ppap"])
    supplier = _score(ppap_good, ppap_total, fallback=70.0)

    active_changes = sum(x.status not in TERMINAL_CHANGE for x in rows["changes"])
    high_changes = sum(x.status not in TERMINAL_CHANGE and getattr(x, "risk_level", "") in {"high", "critical"} for x in rows["changes"])
    change = max(0.0, 100.0 - active_changes * 4.0 - high_changes * 10.0)

    open_defects = [x for x in rows["defects"] if x.status not in {"resolved", "closed", "cancelled"}]
    critical_defects = sum(x.severity in {"high", "critical"} for x in open_defects)
    ineffective = sum(x.status in BAD_EFFECTIVENESS for x in rows["effectiveness"])
    quality = max(0.0, 100.0 - len(open_defects) * 3.0 - critical_defects * 10.0 - ineffective * 15.0)

    open_risk = [serialize_risk(x) for x in rows["risks"] if x.status not in CLOSED_RISK]
    high_risk = sum(x["residual_band"] in {"high", "critical"} for x in open_risk)
    risk = max(0.0, 100.0 - high_risk * 15.0 - max(0, len(open_risk) - high_risk) * 3.0)

    candidate = [x for x in rows["baselines"] if x.release_candidate]
    product = 100.0 if candidate else (80.0 if rows["baselines"] else 70.0)

    domains = {
        "product": round(product, 1),
        "program": round(program, 1),
        "vv": round(vv, 1),
        "manufacturing_launch": round(launch, 1),
        "supplier": round(supplier, 1),
        "changes": round(change, 1),
        "quality": round(quality, 1),
        "risk": round(risk, 1),
    }
    overall = round(sum(domains.values()) / len(domains), 1)
    return {"overall": overall, "domains": domains, "method": "deterministic_evidence_weighted_maturity", "advisory_only": True}


def _risk_rank(severity: str) -> int:
    return {"critical": 0, "high": 1, "medium": 2, "warning": 2, "low": 3, "info": 4}.get(severity, 9)


def blocker_forecast(rows: dict, schedule: dict, target: dict, now: datetime) -> list[dict]:
    target_due = datetime.fromisoformat(target["due_at"]) if target.get("due_at") else None
    blockers: list[dict] = []

    for x in schedule["milestones"]:
        if x["overdue"]:
            blockers.append({"severity": "high", "type": "overdue_milestone", "title": f"Просрочен этап {x['code']} · {x['name']}", "entity_id": x["id"], "owner": x["owner"], "due_at": x["due_at"], "manufacturing_area": x["manufacturing_area"], "explain": "Milestone due date is in the past and status is not complete."})
        elif x["forecast_slip_days"] and x["forecast_slip_days"] > 0:
            blockers.append({"severity": "high" if x["forecast_slip_days"] >= 7 else "medium", "type": "dependency_slip", "title": f"{x['code']} forecast slip +{x['forecast_slip_days']}d", "entity_id": x["id"], "owner": x["owner"], "due_at": x["due_at"], "manufacturing_area": x["manufacturing_area"], "explain": "Predecessor due dates + configured dependency lag push the milestone beyond its current due date."})

    for x in rows["launch_items"]:
        if not x.required or x.status in DONE_LAUNCH:
            continue
        due = _utc(x.due_at)
        if target_due is None or due is None or due <= target_due:
            blockers.append({"severity": "high" if x.category in {"run_at_rate", "ppap", "quality", "capacity"} else "medium", "type": "launch_gate", "title": f"Launch gate: {x.code} · {x.title}", "entity_id": x.id, "owner": x.owner, "due_at": _iso(x.due_at), "manufacturing_area": x.manufacturing_area, "explain": "Required launch-readiness item is not complete before the target gate."})

    for x in rows["risks"]:
        sx = serialize_risk(x)
        if x.status not in CLOSED_RISK and sx["residual_band"] in {"high", "critical"}:
            blockers.append({"severity": sx["residual_band"], "type": "engineering_risk", "title": f"{x.code} · {x.title}", "entity_id": x.id, "owner": x.owner, "due_at": None, "manufacturing_area": x.manufacturing_area, "explain": f"Open residual engineering risk score {sx['residual_score']}."})

    for x in rows["changes"]:
        if x.status not in TERMINAL_CHANGE and getattr(x, "risk_level", "") in {"high", "critical"}:
            blockers.append({"severity": "high", "type": "engineering_change", "title": f"Open {x.eco_code or x.code} · {x.title}", "entity_id": x.id, "owner": getattr(x, "owner", None), "due_at": None, "manufacturing_area": None, "explain": "High/critical engineering change is not yet implemented/closed."})

    for x in rows["verifications"]:
        if x.status not in {"passed", "waived"}:
            blockers.append({"severity": "high" if x.status in {"failed", "blocked"} else "medium", "type": "vv", "title": f"V&V {x.code} · {x.title}", "entity_id": x.id, "owner": getattr(x, "owner", None), "due_at": None, "manufacturing_area": x.manufacturing_area, "explain": "Requirement verification is not in a passed/waived evidence state."})

    for x in rows["ppap"]:
        if x.status != "approved":
            blockers.append({"severity": "high" if x.status in {"rejected", "blocked"} else "medium", "type": "ppap", "title": f"PPAP {x.part_number} · {x.supplier_name or x.supplier_code or 'supplier'}", "entity_id": x.id, "owner": None, "due_at": None, "manufacturing_area": x.manufacturing_area, "explain": "Supplier PPAP is not approved."})

    for x in rows["defects"]:
        if x.status not in {"resolved", "closed", "cancelled"} and x.severity in {"high", "critical"}:
            blockers.append({"severity": x.severity, "type": "quality_defect", "title": f"{x.title}", "entity_id": x.id, "owner": None, "due_at": None, "manufacturing_area": x.manufacturing_area, "explain": "High/critical production-quality defect remains open."})

    for x in rows["effectiveness"]:
        if x.status in BAD_EFFECTIVENESS:
            blockers.append({"severity": "high", "type": "ineffective_change", "title": f"{x.code}: change effectiveness failed", "entity_id": x.id, "owner": x.reviewed_by, "due_at": None, "manufacturing_area": x.manufacturing_area, "explain": x.conclusion or x.target_description})

    for x in rows["deviations"]:
        sx = serialize_deviation(x)
        if sx["expired"]:
            blockers.append({"severity": "high", "type": "expired_deviation", "title": f"{x.code}: deviation expired", "entity_id": x.id, "owner": None, "due_at": sx["valid_until"], "manufacturing_area": x.manufacturing_area, "explain": f"Temporary deviation for {x.part_number} exceeded its validity date."})

    blockers.sort(key=lambda x: (_risk_rank(x["severity"]), x.get("due_at") or "9999", x["title"]))
    return blockers[:60]


def _gate_forecast(target: dict, schedule: dict, blockers: list[dict], cycles: list[list[str]], now: datetime) -> dict:
    target_due = datetime.fromisoformat(target["due_at"]) if target.get("due_at") else None
    days_to_gate = (target_due - now).days if target_due else None
    predicted_slip = 0
    if target.get("id"):
        row = next((x for x in schedule["milestones"] if x["id"] == target["id"]), None)
        if row:
            predicted_slip = int(row.get("forecast_slip_days") or 0)
    critical = sum(x["severity"] == "critical" for x in blockers)
    high = sum(x["severity"] == "high" for x in blockers)
    if cycles or critical or predicted_slip > 0 or (days_to_gate is not None and days_to_gate < 0):
        band = "RED"
    elif high or (days_to_gate is not None and days_to_gate <= 45 and blockers):
        band = "AMBER"
    else:
        band = "GREEN"
    return {
        "band": band,
        "days_to_gate": days_to_gate,
        "predicted_slip_days": predicted_slip,
        "critical_blockers": critical,
        "high_blockers": high,
        "dependency_cycles": len(cycles),
        "forecast_method": "deterministic_due_dates_dependencies_and_open_engineering_gates",
        "probabilistic_prediction": False,
        "human_program_decision_required": True,
    }


def area_maturity(db: Session, project: Project, rows: dict, schedule: dict, allowed_area_codes: set[str]) -> list[dict]:
    areas = [x for x in db.scalars(select(ProjectArea).where(ProjectArea.project_code == project.code)).all() if x.code in allowed_area_codes]
    out = []
    schedule_by_id = {x["id"]: x for x in schedule["milestones"]}
    for area in sorted(areas, key=lambda x: (x.sort_order, x.code)):
        ms = [x for x in rows["milestones"] if x.manufacturing_area in {None, area.code}]
        li = [x for x in rows["launch_items"] if x.manufacturing_area in {None, area.code} and x.required]
        rr = [serialize_risk(x) for x in rows["risks"] if x.manufacturing_area in {None, area.code} and x.status not in CLOSED_RISK]
        defects = [x for x in rows["defects"] if x.manufacturing_area in {None, area.code} and x.status not in {"resolved", "closed", "cancelled"}]
        ms_done = sum(x.status in DONE_MILESTONE for x in ms)
        li_done = sum(x.status in DONE_LAUNCH for x in li)
        overdue = sum(schedule_by_id.get(x.id, {}).get("overdue", False) for x in ms)
        high_risk = sum(x["residual_band"] in {"high", "critical"} for x in rr)
        high_defect = sum(x.severity in {"high", "critical"} for x in defects)
        score = (_score(ms_done, len(ms), fallback=80.0) * 0.45 + _score(li_done, len(li), fallback=80.0) * 0.35 + max(0.0, 100 - 15 * high_risk - 10 * high_defect - 8 * overdue) * 0.20)
        out.append({
            "code": area.code,
            "name": area.name,
            "score": round(score, 1),
            "band": "GREEN" if score >= 90 else ("AMBER" if score >= 70 else "RED"),
            "counts": {"milestones": len(ms), "launch_gates": len(li), "overdue": overdue, "high_risks": high_risk, "high_defects": high_defect},
        })
    return out


def simulate_milestone_slip(milestones: list[ProjectMilestone], dependencies: list[ProgramDependency], milestone_id: str, slip_days: int) -> dict:
    by_id = {x.id: x for x in milestones}
    if milestone_id not in by_id:
        raise LookupError("Milestone not found")
    due = {x.id: _utc(x.due_at) for x in milestones if x.due_at}
    if milestone_id not in due:
        raise ValueError("Selected milestone has no due date")
    forecast = dict(due)
    forecast[milestone_id] = forecast[milestone_id] + timedelta(days=slip_days)
    graph = defaultdict(list)
    for e in dependencies:
        graph[e.predecessor_milestone_id].append(e)
    q = deque([milestone_id])
    seen_count = defaultdict(int)
    while q:
        pred_id = q.popleft()
        seen_count[pred_id] += 1
        if seen_count[pred_id] > len(milestones) + 1:
            break
        for e in graph.get(pred_id, []):
            if pred_id not in forecast or e.successor_milestone_id not in forecast:
                continue
            earliest = forecast[pred_id] + timedelta(days=int(e.lag_days or 0))
            if earliest > forecast[e.successor_milestone_id]:
                forecast[e.successor_milestone_id] = earliest
                q.append(e.successor_milestone_id)
    affected = []
    for mid, f in forecast.items():
        base = due.get(mid)
        if not base or f <= base:
            continue
        x = by_id[mid]
        affected.append({"id": mid, "code": x.code, "name": x.name, "gate": _gate_kind(x.gate), "due_at": _iso(base), "scenario_due_at": _iso(f), "slip_days": (f - base).days})
    affected.sort(key=lambda x: (-x["slip_days"], x["code"]))
    return {
        "source_milestone_id": milestone_id,
        "source_code": by_id[milestone_id].code,
        "input_slip_days": slip_days,
        "affected": affected,
        "affected_count": len(affected),
        "deterministic": True,
        "no_schedule_write": True,
        "method": "forward_dependency_lag_propagation",
    }


def _weekly_brief(project: Project, target: dict, maturity: dict, gate: dict, blockers: list[dict], areas: list[dict], schedule: dict) -> dict:
    overdue = sum(x["overdue"] for x in schedule["milestones"])
    worst_area = min(areas, key=lambda x: x["score"]) if areas else None
    lines = [
        f"{project.code}: program maturity {maturity['overall']:.1f}% · gate forecast {gate['band']}.",
    ]
    if target.get("code"):
        lines.append(f"Next controlled gate: {target['code']} · {target['name']} · {target.get('due_at') or 'date not configured'}.")
    if overdue:
        lines.append(f"Overdue engineering milestones: {overdue}.")
    if blockers:
        lines.append(f"Top blocker: {blockers[0]['title']} ({blockers[0]['severity'].upper()}).")
    if worst_area:
        lines.append(f"Lowest manufacturing-area maturity: {worst_area['name']} · {worst_area['score']}%.")
    return {"headline": lines[0], "lines": lines, "generated_from_current_evidence": True, "llm_required": False}


def program_control_workspace(
    db: Session,
    project: Project,
    visible_document_ids: set[str],
    visible_part_numbers: set[str],
    manufacturing_area: str | None,
    allowed_area_codes: set[str],
) -> dict:
    now = datetime.now(timezone.utc)
    rows = visible_program_rows(db, project.code, visible_document_ids, visible_part_numbers, manufacturing_area, allowed_area_codes)
    by_id = {x.id: x for x in rows["milestones"]}
    schedule = _schedule_forecast(rows["milestones"], rows["dependencies"], now)
    target = _target_gate(project, rows["milestones"], now)
    cycles = _graph_cycles(rows["milestones"], rows["dependencies"])
    chain = critical_dependency_chain(rows["milestones"], rows["dependencies"], target.get("id"))
    maturity = maturity_scores(rows, schedule)
    blockers = blocker_forecast(rows, schedule, target, now)
    gate = _gate_forecast(target, schedule, blockers, cycles, now)
    areas = area_maturity(db, project, rows, schedule, allowed_area_codes)
    deps = [serialize_dependency(x, by_id) for x in rows["dependencies"]]
    top_actions = [
        {
            "priority": i + 1,
            "severity": x["severity"],
            "action": x["title"],
            "owner": x.get("owner"),
            "due_at": x.get("due_at"),
            "manufacturing_area": x.get("manufacturing_area"),
            "why": x.get("explain"),
            "source_type": x["type"],
            "source_id": x["entity_id"],
        }
        for i, x in enumerate(blockers[:10])
    ]
    return {
        "project": {"code": project.code, "name": project.name, "phase": project.phase, "target_release_at": _iso(project.target_release_at)},
        "manufacturing_area": manufacturing_area,
        "target_gate": target,
        "gate_forecast": gate,
        "maturity": maturity,
        "area_maturity": areas,
        "critical_dependency_chain": chain,
        "schedule": {"milestones": schedule["milestones"], "dependency_cycles": cycles},
        "dependencies": deps,
        "blocker_forecast": blockers,
        "top_actions": top_actions,
        "engineering_command_brief": _weekly_brief(project, target, maturity, gate, blockers, areas, schedule),
        "counts": {
            "milestones": len(rows["milestones"]),
            "dependencies": len(rows["dependencies"]),
            "blockers": len(blockers),
            "launch_items": len(rows["launch_items"]),
            "trials": len(rows["trials"]),
            "open_high_risks": sum(serialize_risk(x)["residual_band"] in {"high", "critical"} and x.status not in CLOSED_RISK for x in rows["risks"]),
            "open_changes": sum(x.status not in TERMINAL_CHANGE for x in rows["changes"]),
        },
        "governance": {
            "advisory_only": True,
            "not_project_management_system_of_record": True,
            "not_plm_or_erp_or_mes": True,
            "no_automatic_gate_approval": True,
            "human_program_and_release_approval_required": True,
            "forecast_is_deterministic_not_probabilistic": True,
        },
    }
