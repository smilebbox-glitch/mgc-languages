from __future__ import annotations

from dataclasses import dataclass
from types import ModuleType
from typing import Any

from fastapi import FastAPI
from fastapi.routing import APIRoute

from mgc.services.practice_games import (
    PracticeGameWorkflowBindings,
    build_practice_game_workflows,
)


@dataclass(frozen=True)
class WorkflowBindingReport:
    ok: bool
    practice_route_bound: bool
    game_start_route_bound: bool
    game_finish_route_bound: bool
    question_attempt_route_bound: bool
    route_contract_preserved: bool
    model_contract_preserved: bool
    learning_service_captured: bool
    terminology_service_captured: bool


def _column_names(model: object) -> set[str]:
    table = getattr(model, "__table__", None)
    columns = getattr(table, "columns", None)
    if columns is None:
        return set()
    return {str(column.name) for column in columns}


def _has_columns(model: object, required: set[str]) -> bool:
    return required <= _column_names(model)


def _find_route(application: FastAPI, path: str, method: str) -> APIRoute:
    matches = [
        route
        for route in application.routes
        if isinstance(route, APIRoute)
        and route.path == path
        and method.upper() in (route.methods or set())
    ]
    if len(matches) != 1:
        raise RuntimeError(
            f"workflow route contract drifted for {method.upper()} {path}: {len(matches)} matches"
        )
    return matches[0]


def _bind_route(route: APIRoute, call: Any) -> None:
    # APIRoute's request handler retains the same Dependant object created during
    # registration. Replacing only Dependant.call preserves parsed body/query/
    # dependency metadata and therefore keeps the public FastAPI/OpenAPI contract.
    route.endpoint = call
    route.dependant.call = call


def bind_legacy_workflows(
    module: ModuleType,
    application: FastAPI,
) -> WorkflowBindingReport:
    """Move practice/game orchestration behind modular endpoint-compatible workflows."""
    existing = getattr(module, "MGC_WORKFLOW_BINDING_REPORT", None)
    if isinstance(existing, WorkflowBindingReport) and existing.ok:
        return existing

    required_functions = (
        "validate_language",
        "_consume_daily_quota",
        "require_feature",
        "terms_for",
        "gamification_view",
        "award_xp",
        "get_or_create_srs_card",
        "schedule_srs",
        "rate_limit",
        "save_practice_result",
        "start_game",
        "finish_game",
        "question_attempt",
    )
    if not all(callable(getattr(module, name, None)) for name in required_functions):
        raise RuntimeError("legacy practice/game workflow dependencies are incomplete")

    practice_model = getattr(module, "PracticeResult", None)
    game_model = getattr(module, "GameSession", None)
    attempt_model = getattr(module, "QuestionAttempt", None)
    if any(model is None for model in (practice_model, game_model, attempt_model)):
        raise RuntimeError("legacy practice/game workflow models are incomplete")

    model_contract_ok = all(
        (
            _has_columns(
                practice_model,
                {"user_id", "session_id", "kind", "language", "topic", "score", "total", "created_at"},
            ),
            _has_columns(
                game_model,
                {
                    "public_id",
                    "user_id",
                    "game_type",
                    "language",
                    "topic",
                    "payload_json",
                    "status",
                    "score",
                    "total",
                    "completed_at",
                },
            ),
            _has_columns(
                attempt_model,
                {
                    "user_id",
                    "session_id",
                    "question_id",
                    "term_id",
                    "language",
                    "topic",
                    "kind",
                    "correct",
                    "response_ms",
                    "selected_hash",
                },
            ),
        )
    )
    if not model_contract_ok:
        raise RuntimeError("legacy practice/game model contract drifted")

    learning_service_captured = all(
        getattr(getattr(module, name), "__module__", "") == "mgc.services.learning"
        for name in (
            "gamification_view",
            "award_xp",
            "get_or_create_srs_card",
            "schedule_srs",
        )
    )
    if not learning_service_captured:
        raise RuntimeError("practice/game workflows must bind after extracted learning service")

    terminology_service_captured = (
        getattr(getattr(module, "terms_for"), "__module__", "")
        == "mgc.services.terminology"
    )
    if not terminology_service_captured:
        raise RuntimeError("practice/game workflows must bind after terminology service")

    bindings: PracticeGameWorkflowBindings = build_practice_game_workflows(
        practice_result_model=practice_model,
        game_session_model=game_model,
        question_attempt_model=attempt_model,
        validate_language=getattr(module, "validate_language"),
        consume_daily_quota=getattr(module, "_consume_daily_quota"),
        practice_daily_cap=int(getattr(module, "PILOT_DAILY_PRACTICE_CAP")),
        game_daily_cap=int(getattr(module, "PILOT_DAILY_GAME_START_CAP")),
        require_feature=getattr(module, "require_feature"),
        terms_for=getattr(module, "terms_for"),
        gamification_view=getattr(module, "gamification_view"),
        award_xp=getattr(module, "award_xp"),
        get_or_create_srs_card=getattr(module, "get_or_create_srs_card"),
        schedule_srs=getattr(module, "schedule_srs"),
        rate_limit=getattr(module, "rate_limit"),
    )

    route_specs = (
        ("save_practice_result", "/api/practice/result", "POST", bindings.save_practice_result),
        ("start_game", "/api/games/{game_type}/start", "POST", bindings.start_game),
        ("finish_game", "/api/games/{session_id}/finish", "POST", bindings.finish_game),
        ("question_attempt", "/api/learning/question-attempt", "POST", bindings.question_attempt),
    )
    original_endpoints: dict[str, Any] = {}
    bound_routes: dict[str, APIRoute] = {}
    for name, path, method, call in route_specs:
        route = _find_route(application, path, method)
        legacy_call = getattr(module, name)
        if route.dependant.call is not legacy_call:
            raise RuntimeError(f"legacy route call drifted before workflow binding: {method} {path}")
        original_endpoints[name] = legacy_call
        _bind_route(route, call)
        module.__dict__[name] = call
        bound_routes[name] = route

    module.MGC_LEGACY_WORKFLOW_ENDPOINTS = original_endpoints
    module.MGC_PRACTICE_GAME_WORKFLOW_BINDINGS = bindings

    route_contract_ok = all(
        route.dependant.call is call and route.endpoint is call
        for (name, _path, _method, call), route in zip(route_specs, bound_routes.values())
    )
    report = WorkflowBindingReport(
        ok=route_contract_ok and model_contract_ok,
        practice_route_bound=(
            bound_routes["save_practice_result"].dependant.call is bindings.save_practice_result
        ),
        game_start_route_bound=(
            bound_routes["start_game"].dependant.call is bindings.start_game
        ),
        game_finish_route_bound=(
            bound_routes["finish_game"].dependant.call is bindings.finish_game
        ),
        question_attempt_route_bound=(
            bound_routes["question_attempt"].dependant.call is bindings.question_attempt
        ),
        route_contract_preserved=route_contract_ok,
        model_contract_preserved=model_contract_ok,
        learning_service_captured=learning_service_captured,
        terminology_service_captured=terminology_service_captured,
    )
    if not report.ok:
        raise RuntimeError("practice/game workflow binding failed closed")
    module.MGC_WORKFLOW_BINDING_REPORT = report
    return report


__all__ = ["WorkflowBindingReport", "bind_legacy_workflows"]
