from __future__ import annotations

from typing import Any

ACTION_SCHEMA = "mgc-action-item-v1"
DECISION_SCHEMA = "mgc-decision-item-v1"

PRIORITY = {"critical": 4, "high": 3, "medium": 2, "low": 1}


def normalize_action(value: dict[str, Any], *, default_domain: str = "engineering") -> dict[str, Any]:
    raw = dict(value or {})
    priority = str(raw.get("priority") or "medium").lower()
    if priority not in PRIORITY: priority = "medium"
    return {
        "schema": ACTION_SCHEMA,
        "id": str(raw.get("id") or raw.get("source_id") or raw.get("code") or raw.get("title") or "action"),
        "domain": str(raw.get("domain") or default_domain),
        "type": str(raw.get("type") or raw.get("source_type") or "review").lower(),
        "title": str(raw.get("title") or "Engineering action"),
        "reason": str(raw.get("reason") or ""),
        "priority": priority,
        "priority_score": int(raw.get("priority_score") or PRIORITY[priority] * 25),
        "decision_required": bool(raw.get("decision_required", False)),
        "owner": raw.get("owner"),
        "due_at": raw.get("due_at"),
        "entity": raw.get("entity") or ({"type": raw.get("source_type"), "id": raw.get("source_id")} if raw.get("source_id") else None),
        "evidence": list(raw.get("evidence") or []),
    }


def normalize_decision(value: dict[str, Any], *, default_domain: str = "engineering") -> dict[str, Any]:
    action = normalize_action({**value, "decision_required": True}, default_domain=default_domain)
    action["schema"] = DECISION_SCHEMA
    action["human_decision_required"] = True
    return action
