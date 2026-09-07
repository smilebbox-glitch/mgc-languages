import re

from app.services.query_planner import plan_query
from app.adapters.registry import get_ai_analysis_port, get_search_port
from app.ports.ai import AIAnalysisPort
from app.ports.search import SearchPort


SYSTEM_PROMPT = """You are MGC Engineering AI, an internal engineering evidence assistant.
Answer only from supplied evidence. Never invent dimensions, materials, tolerances, test results, revisions, part numbers, standards or approvals.
Deterministic CAD metadata is authoritative for computed geometry. Document statements are authoritative only for what the source actually says.
When sources disagree, explicitly identify the conflict instead of choosing a value.
Cite every factual engineering claim inline as [S1], [S2], etc. If evidence is insufficient, say exactly what is missing.
Use the language of the user unless requested otherwise. Keep answers concise but technically complete.
"""


def _context(hits: list[dict]) -> str:
    blocks = []
    for i, h in enumerate(hits, 1):
        meta = h.get("metadata") or {}
        blocks.append(
            f"[S{i}] file={h['filename']} type={h.get('doc_type')} part={h.get('part_number')} revision={h.get('revision')}\n"
            f"metadata={meta}\n{h['text']}"
        )
    return "\n\n".join(blocks)


def _confidence(hits: list[dict]) -> str:
    if not hits: return "none"
    if len(hits) >= 3 and hits[0]["score"] >= 0.8: return "high"
    if hits[0]["score"] >= 0.45: return "medium"
    return "low"


async def ask(
    query: str,
    limit: int,
    acl_groups: list[str],
    part_number=None,
    revision=None,
    doc_type=None,
    project_code=None,
    manufacturing_area=None,
    conversation=None,
    *,
    search_port: SearchPort | None = None,
    ai_port: AIAnalysisPort | None = None,
):
    search_port = search_port or get_search_port()
    ai_port = ai_port or get_ai_analysis_port()
    plan = plan_query(query)
    part_number = part_number or plan.get("part_number")
    revision = revision or plan.get("revision")
    hits = search_port.search(query, limit, acl_groups, part_number, revision, doc_type, project_code, manufacturing_area)
    if not hits and (part_number or revision):
        # Relax structured constraints rather than hallucinate an empty answer.
        hits = search_port.search(query, limit, acl_groups, None, None, doc_type, project_code, manufacturing_area)
        plan["filters_relaxed"] = True
    if not hits:
        return "В доступной базе знаний не найдено подтверждающих материалов.", [], False, plan, "none"

    if not ai_port.available:
        evidence = "\n\n".join(f"[S{i}] {h['filename']}: {h['text'][:700]}" for i, h in enumerate(hits, 1))
        return "Core-профиль: AI-синтез отключён. Найдены подтверждающие материалы:\n\n" + evidence, hits, False, plan, _confidence(hits)

    history = (conversation or [])[-6:]
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    for m in history:
        if m.get("role") in {"user", "assistant"} and isinstance(m.get("content"), str):
            messages.append({"role": m["role"], "content": m["content"][:6000]})
    messages.append({"role": "user", "content": f"Question:\n{query}\n\nRetrieval plan:\n{plan}\n\nEvidence:\n{_context(hits)}"})
    try:
        completion = await ai_port.complete(messages, temperature=0.05)
        return completion.content, hits, True, plan, _confidence(hits)
    except Exception as exc:
        return f"AI-синтез недоступен ({type(exc).__name__}). Найдены подтверждающие источники, но синтез ответа не выполнен.", hits, False, plan, _confidence(hits)
