from __future__ import annotations

from typing import Any

UX_SCHEMA = "mgc-role-landing-v1"
MAX_PRIMARY_ACTIONS = 5
MAX_DECISIONS = 3
MAX_GUIDED_WORKFLOWS = 3

ROLE_GUIDES: dict[str, list[dict[str, Any]]] = {
    "engineering": [
        {"code":"review_change","label":"Проверить изменение","steps":["Change Impact","V&V / evidence","Release decision"]},
        {"code":"release_part","label":"Подготовить деталь к выпуску","steps":["Part 360","BOM / drawing","Configuration / baseline"]},
        {"code":"investigate_issue","label":"Разобрать инженерную проблему","steps":["Digital Thread","Historical analogues","Decision record"]},
    ],
    "manufacturing": [
        {"code":"buildability","label":"Проверить собираемость","steps":["EBOM ↔ MBOM","Process / WI","Handover gate"]},
        {"code":"cut_in","label":"Провести cut-in изменения","steps":["Effectivity","Stock disposition","MES / next build"]},
        {"code":"launch_blocker","label":"Закрыть launch blocker","steps":["Program blocker","Owner evidence","Human gate review"]},
    ],
    "quality": [
        {"code":"defect_investigation","label":"Расследовать дефект","steps":["VIN / genealogy","PFMEA / Control Plan","8D / containment"]},
        {"code":"suspect_population","label":"Определить suspect population","steps":["Part / supplier lot","VIN population","Containment"]},
        {"code":"effectiveness","label":"Проверить эффективность решения","steps":["Before / after","Recurrence","Lesson Learned"]},
    ],
    "supplier": [
        {"code":"supplier_issue","label":"Закрыть проблему поставщика","steps":["Incoming quality","Supplier 8D","PPAP / effectiveness"]},
        {"code":"localization","label":"Проверить локализацию","steps":["Part / supplier","Evidence","Release readiness"]},
    ],
    "program": [
        {"code":"next_gate","label":"Подготовить следующий gate","steps":["Critical chain","Top blockers","Decision review"]},
        {"code":"slip_what_if","label":"Проверить риск сдвига","steps":["Milestone","What-if","Downstream gates"]},
    ],
    "field": [
        {"code":"field_failure","label":"Разобрать field failure","steps":["Exposure","VIN trace","DFMEA / validation"]},
        {"code":"field_effectiveness","label":"Проверить новую ревизию","steps":["Reliability comparison","Field recurrence","Human effectiveness review"]},
    ],
    "leadership": [
        {"code":"decision_review","label":"Провести decision review","steps":["Critical actions","Decision Queue","Evidence / owners"]},
        {"code":"program_health","label":"Проверить здоровье программы","steps":["Domain health","Next gate","Top cross-domain workflows"]},
    ],
}

ROLE_ALIASES = {"rd":"engineering", "manufacturing_engineering":"manufacturing", "quality_engineering":"quality"}

def normalize_role(role: str) -> str:
    r=(role or "engineering").strip().lower()
    return ROLE_ALIASES.get(r,r) if ROLE_ALIASES.get(r,r) in ROLE_GUIDES else "engineering"

def build_role_landing(workspace: dict[str, Any], usability_issues: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    role=normalize_role((workspace.get("role") or {}).get("code", "engineering"))
    focused=list((workspace.get("action_inbox") or {}).get("focused") or [])
    decisions=list(workspace.get("decision_queue") or [])
    domains=dict((workspace.get("cockpit") or {}).get("domains") or {})
    issues=[x for x in (usability_issues or []) if x.get("status") not in {"closed","verified"} and x.get("role") in {None,"","all",role}]
    return {
        "schema": UX_SCHEMA,
        "role": role,
        "headline": (workspace.get("command_brief") or {}).get("lines", ["Engineering workspace"])[0],
        "primary_actions": focused[:MAX_PRIMARY_ACTIONS],
        "decisions": decisions[:MAX_DECISIONS],
        "guided_workflows": ROLE_GUIDES.get(role, ROLE_GUIDES["engineering"])[:MAX_GUIDED_WORKFLOWS],
        "domain_health": [{"domain":k, **(v or {})} for k,v in domains.items()],
        "open_usability_issues": issues[:5],
        "progressive_disclosure": {
            "default_visible_layers": ["attention","decisions","guided_workflows"],
            "drilldown_collapsed_by_default": True,
            "max_primary_actions": MAX_PRIMARY_ACTIONS,
            "max_decisions": MAX_DECISIONS,
        },
        "governance": {"role_is_ui_focus_not_authorization": True, "acl_unchanged": True, "employee_performance_scoring": False},
    }
