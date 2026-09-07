from __future__ import annotations

from dataclasses import dataclass
from types import ModuleType

from mgc.services.terminology import TerminologyServiceBindings, build_terminology_service
from mgc.services.users import UserServiceBindings, build_user_service


@dataclass(frozen=True)
class ServiceBindingReport:
    ok: bool
    user_view_bound: bool
    user_stats_bound: bool
    manager_policy_bound: bool
    terminology_view_bound: bool
    terms_query_bound: bool
    revision_bound: bool
    model_contract_preserved: bool


def _column_names(model: object) -> set[str]:
    table = getattr(model, "__table__", None)
    columns = getattr(table, "columns", None)
    if columns is None:
        return set()
    return {str(column.name) for column in columns}


def _has_columns(model: object, required: set[str]) -> bool:
    return required <= _column_names(model)


def bind_legacy_services(module: ModuleType) -> ServiceBindingReport:
    """Move reusable user/terminology business helpers behind service modules.

    The legacy route functions resolve these helpers through module globals at
    request time, so rebinding keeps route objects and OpenAPI contracts intact.
    This binding intentionally runs before auth so the auth core captures the
    extracted user_view implementation for login/session responses.
    """
    existing = getattr(module, "MGC_SERVICE_BINDING_REPORT", None)
    if isinstance(existing, ServiceBindingReport) and existing.ok:
        return existing

    required_functions = (
        "user_view",
        "user_admin_stats",
        "_manager_target_allowed",
        "custom_term_view",
        "terms_for",
        "term_by_id",
        "_term_snapshot",
        "record_term_revision",
        "admin_term_response",
        "gamification_view",
        "notification_pref",
        "english_pronunciation",
        "pinyin_to_ru_approx",
    )
    if not all(callable(getattr(module, name, None)) for name in required_functions):
        raise RuntimeError("legacy user/terminology service helpers are incomplete")

    user_model = getattr(module, "User", None)
    term_progress_model = getattr(module, "TermProgress", None)
    exam_result_model = getattr(module, "ExamResult", None)
    custom_term_model = getattr(module, "CustomTerm", None)
    term_revision_model = getattr(module, "TermRevision", None)
    if any(
        model is None
        for model in (
            user_model,
            term_progress_model,
            exam_result_model,
            custom_term_model,
            term_revision_model,
        )
    ):
        raise RuntimeError("legacy service models are incomplete")

    model_contract_ok = all(
        (
            _has_columns(
                user_model,
                {
                    "id",
                    "username",
                    "display_name",
                    "role",
                    "department",
                    "preferred_language",
                    "created_at",
                },
            ),
            _has_columns(term_progress_model, {"user_id", "status"}),
            _has_columns(exam_result_model, {"user_id", "score"}),
            _has_columns(
                custom_term_model,
                {
                    "id",
                    "public_id",
                    "language",
                    "shop",
                    "topic",
                    "subtopic",
                    "level",
                    "term",
                    "pronunciation",
                    "reading",
                    "translation",
                    "example",
                    "example_translation",
                    "tags",
                    "source_type",
                    "source_ref",
                    "status",
                    "created_at",
                    "updated_at",
                },
            ),
            _has_columns(
                term_revision_model,
                {
                    "term_id",
                    "revision_no",
                    "action",
                    "snapshot_json",
                    "actor_user_id",
                },
            ),
        )
    )
    if not model_contract_ok:
        raise RuntimeError("legacy user/terminology model contract drifted")

    user_bindings: UserServiceBindings = build_user_service(
        term_progress_model=term_progress_model,
        exam_result_model=exam_result_model,
        gamification_view=getattr(module, "gamification_view"),
        notification_pref=getattr(module, "notification_pref"),
    )
    terminology_bindings: TerminologyServiceBindings = build_terminology_service(
        custom_term_model=custom_term_model,
        term_revision_model=term_revision_model,
        base_terms=getattr(module, "TERMS"),
        english_pronunciation=getattr(module, "english_pronunciation"),
        pinyin_to_ru_approx=getattr(module, "pinyin_to_ru_approx"),
    )

    module.user_view = user_bindings.user_view
    module.user_admin_stats = user_bindings.user_admin_stats
    module._manager_target_allowed = user_bindings.manager_target_allowed
    module.custom_term_view = terminology_bindings.custom_term_view
    module.terms_for = terminology_bindings.terms_for
    module.term_by_id = terminology_bindings.term_by_id
    module._term_snapshot = terminology_bindings.term_snapshot
    module.record_term_revision = terminology_bindings.record_term_revision
    module.admin_term_response = terminology_bindings.admin_term_response
    module.MGC_USER_SERVICE_BINDINGS = user_bindings
    module.MGC_TERMINOLOGY_SERVICE_BINDINGS = terminology_bindings

    report = ServiceBindingReport(
        ok=True,
        user_view_bound=module.user_view is user_bindings.user_view,
        user_stats_bound=module.user_admin_stats is user_bindings.user_admin_stats,
        manager_policy_bound=module._manager_target_allowed is user_bindings.manager_target_allowed,
        terminology_view_bound=(
            module.custom_term_view is terminology_bindings.custom_term_view
            and module.admin_term_response is terminology_bindings.admin_term_response
        ),
        terms_query_bound=(
            module.terms_for is terminology_bindings.terms_for
            and module.term_by_id is terminology_bindings.term_by_id
        ),
        revision_bound=(
            module._term_snapshot is terminology_bindings.term_snapshot
            and module.record_term_revision is terminology_bindings.record_term_revision
        ),
        model_contract_preserved=model_contract_ok,
    )
    module.MGC_SERVICE_BINDING_REPORT = report
    return report


__all__ = ["ServiceBindingReport", "bind_legacy_services"]
