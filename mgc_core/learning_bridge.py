from __future__ import annotations

from dataclasses import dataclass
from types import ModuleType

from mgc.services.learning import (
    LearningServiceBindings,
    build_learning_service,
    build_pilot_daily_usage_accessor,
)


@dataclass(frozen=True)
class LearningBindingReport:
    ok: bool
    xp_profile_bound: bool
    xp_award_bound: bool
    xp_spend_bound: bool
    srs_card_bound: bool
    srs_schedule_bound: bool
    pilot_usage_bound: bool
    concurrent_write_safe: bool
    model_contract_preserved: bool
    reward_contract_preserved: bool


def _column_names(model: object) -> set[str]:
    table = getattr(model, "__table__", None)
    columns = getattr(table, "columns", None)
    if columns is None:
        return set()
    return {str(column.name) for column in columns}


def _has_columns(model: object, required: set[str]) -> bool:
    return required <= _column_names(model)


def bind_legacy_learning(module: ModuleType) -> LearningBindingReport:
    """Bind XP/profile/SRS execution before user services capture gamification_view."""
    existing = getattr(module, "MGC_LEARNING_BINDING_REPORT", None)
    if isinstance(existing, LearningBindingReport) and existing.ok:
        return existing

    required_functions = (
        "current_week_key",
        "level_info",
        "get_profile",
        "gamification_view",
        "award_xp",
        "spend_xp",
        "get_or_create_srs_card",
        "schedule_srs",
        "pilot_daily_usage",
        "_pilot_day_key",
    )
    if not all(callable(getattr(module, name, None)) for name in required_functions):
        raise RuntimeError("legacy learning/gamification helpers are incomplete")

    profile_model = getattr(module, "GamificationProfile", None)
    xp_event_model = getattr(module, "XPEvent", None)
    srs_card_model = getattr(module, "SRSCard", None)
    pilot_usage_model = getattr(module, "PilotDailyUsage", None)
    if any(model is None for model in (profile_model, xp_event_model, srs_card_model, pilot_usage_model)):
        raise RuntimeError("legacy learning models are incomplete")

    model_contract_ok = all(
        (
            _has_columns(
                profile_model,
                {
                    "user_id",
                    "lifetime_xp",
                    "spendable_xp",
                    "weekly_xp",
                    "week_key",
                    "last_activity_at",
                    "updated_at",
                },
            ),
            _has_columns(
                xp_event_model,
                {
                    "user_id",
                    "event_type",
                    "source_id",
                    "language",
                    "topic",
                    "xp_delta",
                    "lifetime_delta",
                    "raw_xp",
                    "multiplier_pct",
                    "idempotency_key",
                    "metadata_json",
                    "created_at",
                },
            ),
            _has_columns(
                srs_card_model,
                {
                    "user_id",
                    "language",
                    "term_id",
                    "topic",
                    "repetitions",
                    "lapses",
                    "ease_factor_pct",
                    "interval_days",
                    "due_at",
                    "last_quality",
                    "updated_at",
                },
            ),
            _has_columns(
                pilot_usage_model,
                {
                    "user_id",
                    "day_key",
                    "xp_awarded",
                    "game_starts",
                    "tts_requests",
                    "practice_submissions",
                    "updated_at",
                },
            ),
        )
    )
    if not model_contract_ok:
        raise RuntimeError("legacy learning model contract drifted")

    reward_catalog = getattr(module, "REWARD_CATALOG", None)
    reward_contract_ok = isinstance(reward_catalog, dict) and bool(reward_catalog) and all(
        isinstance(item, dict)
        and isinstance(item.get("price"), int)
        and int(item["price"]) > 0
        for item in reward_catalog.values()
    )
    if not reward_contract_ok:
        raise RuntimeError("legacy XP reward catalog contract drifted")

    pilot_usage = build_pilot_daily_usage_accessor(
        usage_model=pilot_usage_model,
        day_key=getattr(module, "_pilot_day_key"),
    )
    module.pilot_daily_usage = pilot_usage

    bindings: LearningServiceBindings = build_learning_service(
        gamification_profile_model=profile_model,
        xp_event_model=xp_event_model,
        srs_card_model=srs_card_model,
        pilot_daily_usage=pilot_usage,
        daily_xp_cap=int(getattr(module, "PILOT_DAILY_XP_CAP")),
        reward_catalog=reward_catalog,
        level_titles=tuple(getattr(module, "LEVEL_TITLES")),
        roman=tuple(getattr(module, "ROMAN")),
    )

    module.current_week_key = bindings.current_week_key
    module.level_info = bindings.level_info
    module.get_profile = bindings.get_profile
    module.gamification_view = bindings.gamification_view
    module.award_xp = bindings.award_xp
    module.spend_xp = bindings.spend_xp
    module.get_or_create_srs_card = bindings.get_or_create_srs_card
    module.schedule_srs = bindings.schedule_srs
    module.MGC_LEARNING_SERVICE_BINDINGS = bindings

    report = LearningBindingReport(
        ok=True,
        xp_profile_bound=(
            module.get_profile is bindings.get_profile
            and module.gamification_view is bindings.gamification_view
            and module.level_info is bindings.level_info
        ),
        xp_award_bound=module.award_xp is bindings.award_xp,
        xp_spend_bound=module.spend_xp is bindings.spend_xp,
        srs_card_bound=module.get_or_create_srs_card is bindings.get_or_create_srs_card,
        srs_schedule_bound=module.schedule_srs is bindings.schedule_srs,
        pilot_usage_bound=module.pilot_daily_usage is pilot_usage,
        concurrent_write_safe=(
            module.pilot_daily_usage.__module__ == "mgc.services.learning"
            and module.award_xp.__module__ == "mgc.services.learning"
        ),
        model_contract_preserved=model_contract_ok,
        reward_contract_preserved=reward_contract_ok,
    )
    module.MGC_LEARNING_BINDING_REPORT = report
    return report


__all__ = ["LearningBindingReport", "bind_legacy_learning"]
