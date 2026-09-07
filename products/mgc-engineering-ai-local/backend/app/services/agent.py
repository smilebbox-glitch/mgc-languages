from sqlalchemy.orm import Session

from app.services.change_impact import analyze_change_impact
from app.services.design_review import run_design_review
from app.services.evidence_pack import build_evidence_pack
from app.services.query_planner import plan_query


def execute_engineering_workflow(db: Session, instruction: str, user: str, allowed_document_ids: set[str] | None = None) -> dict:
    """Deterministic tool router for high-value engineering workflows.
    It does not let an LLM execute arbitrary code; the planner maps only to allow-listed tools.
    """
    plan = plan_query(instruction)
    pn = plan.get("part_number")
    rev = plan.get("revision")
    low = instruction.lower()
    if not pn:
        return {"action": "needs_context", "message": "Part number is required for this workflow", "plan": plan}
    if any(x in low for x in ["design review", "ревью", "провер конструк", "проверь конструк"]):
        baseline = plan.get("baseline_revision")
        if not rev:
            return {"action": "needs_context", "message": "Target revision is required", "plan": plan}
        review = run_design_review(db, pn, rev, baseline, user, allowed_document_ids)
        return {"action": "design_review", "review_id": review.id, "risk_score": review.risk_score, "summary": review.summary, "findings": review.findings}
    if any(x in low for x in ["impact", "влия", "затрон"]):
        baseline = plan.get("baseline_revision")
        if not rev or not baseline:
            return {"action": "needs_context", "message": "Both baseline and target revisions are required", "plan": plan}
        return {"action": "change_impact", "result": analyze_change_impact(db, pn, baseline, rev, allowed_document_ids=allowed_document_ids)}
    if any(x in low for x in ["evidence", "доказ", "ниокр", "пакет"]):
        pack = build_evidence_pack(db, pn, rev, user, "niokr" if "ниокр" in low else "engineering", allowed_document_ids)
        return {"action": "evidence_pack", "pack_id": pack.id, "manifest": pack.manifest}
    return {"action": "search_or_ask", "plan": plan, "message": "Use /ask for evidence-grounded Q&A"}
