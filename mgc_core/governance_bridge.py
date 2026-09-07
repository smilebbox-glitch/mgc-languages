from __future__ import annotations

from dataclasses import dataclass
from types import ModuleType

from mgc.governance_core import GovernanceCoreBindings, build_governance_core


@dataclass(frozen=True)
class GovernanceBindingReport:
    ok: bool
    rls_bound: bool
    audit_event_bound: bool
    verifier_available: bool
    audit_model_contract_preserved: bool


def _column_names(model: object) -> set[str]:
    table = getattr(model, "__table__", None)
    columns = getattr(table, "columns", None)
    if columns is None:
        return set()
    return {str(column.name) for column in columns}


def bind_legacy_governance(module: ModuleType) -> GovernanceBindingReport:
    """Bind extracted RLS/audit execution before the auth core captures its RLS hook."""
    existing = getattr(module, "MGC_GOVERNANCE_BINDING_REPORT", None)
    if isinstance(existing, GovernanceBindingReport) and existing.ok:
        return existing

    audit_log_model = getattr(module, "AuditLog", None)
    audit_anchor_model = getattr(module, "AuditAnchor", None)
    legacy_rls = getattr(module, "apply_rls_context", None)
    legacy_audit = getattr(module, "audit_event", None)
    if audit_log_model is None or audit_anchor_model is None:
        raise RuntimeError("legacy audit models are incomplete")
    if not callable(legacy_rls) or not callable(legacy_audit):
        raise RuntimeError("legacy RLS/audit functions are incomplete")

    required_log = {
        "id",
        "event_type",
        "actor_user_id",
        "target_type",
        "target_id",
        "request_id",
        "source_ip_hash",
        "metadata_json",
        "previous_hash",
        "event_hash",
    }
    required_anchor = {"id", "last_deleted_id", "last_deleted_hash", "updated_at"}
    model_contract_ok = required_log <= _column_names(audit_log_model) and required_anchor <= _column_names(audit_anchor_model)
    if not model_contract_ok:
        raise RuntimeError("legacy audit model contract drifted")

    bindings: GovernanceCoreBindings = build_governance_core(
        audit_log_model=audit_log_model,
        audit_anchor_model=audit_anchor_model,
        database_url=str(getattr(module, "DATABASE_URL")),
        rls_enabled=bool(getattr(module, "RLS_ENABLED")),
        audit_chain_lock_id=int(getattr(module, "AUDIT_CHAIN_LOCK_ID")),
        client_key=getattr(module, "_client_key"),
    )

    module.apply_rls_context = bindings.apply_rls_context
    module.audit_event = bindings.audit_event
    module.verify_audit_chain_core = bindings.verify_audit_chain
    module.MGC_GOVERNANCE_BINDINGS = bindings

    report = GovernanceBindingReport(
        ok=True,
        rls_bound=module.apply_rls_context is bindings.apply_rls_context,
        audit_event_bound=module.audit_event is bindings.audit_event,
        verifier_available=module.verify_audit_chain_core is bindings.verify_audit_chain,
        audit_model_contract_preserved=model_contract_ok,
    )
    module.MGC_GOVERNANCE_BINDING_REPORT = report
    return report


__all__ = ["GovernanceBindingReport", "bind_legacy_governance"]
