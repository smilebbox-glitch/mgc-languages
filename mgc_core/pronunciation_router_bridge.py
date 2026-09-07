from __future__ import annotations

import inspect
from dataclasses import dataclass
from types import ModuleType

from fastapi import FastAPI
from fastapi.routing import APIRoute
from starlette.routing import Mount

from mgc.routers.pronunciation import (
    PRONUNCIATION_HANDLER_NAMES,
    PronunciationPayload,
    build_pronunciation_router,
)


PRONUNCIATION_BASE_ROUTE_CONTRACT = {
    ("GET", "/api/pronunciation/status"),
    ("POST", "/api/pronunciation/audio"),
}
PRONUNCIATION_LEGACY_ROUTE = ("GET", "/api/pronunciation/audio")


@dataclass(frozen=True)
class PronunciationRouterBindingReport:
    ok: bool
    route_count: int
    status_route_count: int
    post_audio_route_count: int
    legacy_get_enabled: bool
    legacy_get_route_count: int
    route_names_preserved: bool
    response_classes_preserved: bool
    legacy_get_deprecated_preserved: bool
    payload_schema_preserved: bool
    tts_max_chars_preserved: bool
    root_mount_order_preserved: bool
    router_module_owned: bool
    auth_core_bound: bool
    legacy_tts_handlers_captured: bool


def _key(route: APIRoute) -> tuple[str, str]:
    methods = sorted((route.methods or set()) - {"HEAD", "OPTIONS"})
    if len(methods) != 1:
        raise RuntimeError(f"pronunciation route must have one explicit method: {route.path} {methods}")
    return methods[0], route.path


def _contract(legacy_get_enabled: bool) -> set[tuple[str, str]]:
    routes = set(PRONUNCIATION_BASE_ROUTE_CONTRACT)
    if legacy_get_enabled:
        routes.add(PRONUNCIATION_LEGACY_ROUTE)
    return routes


def _single_route_index(application: FastAPI, key: tuple[str, str]) -> int:
    matches = [
        index
        for index, route in enumerate(application.router.routes)
        if isinstance(route, APIRoute) and _key(route) == key
    ]
    if len(matches) != 1:
        raise RuntimeError(
            f"pronunciation route contract drifted for {key[0]} {key[1]}: {len(matches)} matches"
        )
    return matches[0]


def _captured_handler(route: APIRoute, variable: str, expected: object) -> bool:
    try:
        closure = inspect.getclosurevars(route.endpoint)
    except (TypeError, ValueError):
        return False
    return closure.nonlocals.get(variable) is expected


def bind_pronunciation_router(
    module: ModuleType,
    application: FastAPI,
) -> PronunciationRouterBindingReport:
    """Replace pronunciation APIRoutes while preserving the existing TTS engine."""
    existing = getattr(module, "MGC_PRONUNCIATION_ROUTER_BINDING_REPORT", None)
    if isinstance(existing, PronunciationRouterBindingReport) and existing.ok:
        return existing

    if getattr(getattr(module, "current_user", None), "__module__", "") != "mgc.auth_core":
        raise RuntimeError("pronunciation router must bind after extracted current_user")
    auth_core_bound = True

    required = (
        "db_session",
        "current_user",
        "PronunciationPayload",
        "TTS_MAX_CHARS",
        "TTS_LEGACY_GET_ENABLED",
        "_pronunciation_response",
        *PRONUNCIATION_HANDLER_NAMES,
    )
    missing = [name for name in required if not hasattr(module, name)]
    if missing:
        raise RuntimeError(f"legacy pronunciation router dependencies are incomplete: {missing}")

    legacy_get_enabled = bool(getattr(module, "TTS_LEGACY_GET_ENABLED"))
    handlers = {name: getattr(module, name) for name in PRONUNCIATION_HANDLER_NAMES}
    if legacy_get_enabled:
        legacy_handler = getattr(module, "pronunciation_audio_legacy", None)
        if not callable(legacy_handler):
            raise RuntimeError("legacy pronunciation GET is enabled but its handler is missing")
        handlers["pronunciation_audio_legacy"] = legacy_handler

    legacy_payload_model = getattr(module, "PronunciationPayload")
    payload_schema_preserved = (
        callable(getattr(legacy_payload_model, "model_json_schema", None))
        and legacy_payload_model.model_json_schema() == PronunciationPayload.model_json_schema()
    )
    tts_max_chars = int(getattr(module, "TTS_MAX_CHARS"))
    tts_max_chars_preserved = (
        PronunciationPayload.model_fields["text"].metadata
        == legacy_payload_model.model_fields["text"].metadata
    )
    if not payload_schema_preserved or not tts_max_chars_preserved:
        raise RuntimeError("pronunciation payload contract drifted")

    extracted = build_pronunciation_router(
        db_session=module.db_session,
        current_user=module.current_user,
        handlers=handlers,
        legacy_get_enabled=legacy_get_enabled,
        tts_max_chars=tts_max_chars,
    )
    expected = _contract(legacy_get_enabled)
    new_routes = {_key(route): route for route in extracted.routes if isinstance(route, APIRoute)}
    if set(new_routes) != expected:
        raise RuntimeError(
            "extracted pronunciation router contract drifted: "
            + str(sorted(set(new_routes) ^ expected))
        )

    originals: dict[tuple[str, str], APIRoute] = {}
    replaced: dict[tuple[str, str], APIRoute] = {}
    indexes: list[int] = []
    route_names_preserved = True
    response_classes_preserved = True
    legacy_get_deprecated_preserved = True

    for key in sorted(expected):
        index = _single_route_index(application, key)
        indexes.append(index)
        old_route = application.router.routes[index]
        assert isinstance(old_route, APIRoute)
        new_route = new_routes[key]
        route_names_preserved = route_names_preserved and old_route.name == new_route.name
        response_classes_preserved = (
            response_classes_preserved and old_route.response_class == new_route.response_class
        )
        if key == PRONUNCIATION_LEGACY_ROUTE:
            legacy_get_deprecated_preserved = old_route.deprecated == new_route.deprecated == True
        originals[key] = old_route
        application.router.routes[index] = new_route
        replaced[key] = new_route
        setattr(module, old_route.name, new_route.endpoint)

    module.MGC_LEGACY_PRONUNCIATION_ROUTES = originals
    module.MGC_PRONUNCIATION_ROUTER = extracted

    mount_indices = [
        index
        for index, route in enumerate(application.router.routes)
        if isinstance(route, Mount) and getattr(route, "name", None) == "static"
    ]
    root_mount_order_preserved = bool(mount_indices) and all(
        index < mount_indices[0] for index in indexes
    )
    router_module_owned = all(
        route.endpoint.__module__ == "mgc.routers.pronunciation"
        for route in replaced.values()
    )

    capture_checks = [
        _captured_handler(
            replaced[("GET", "/api/pronunciation/status")],
            "pronunciation_status_handler",
            handlers["pronunciation_status"],
        ),
        _captured_handler(
            replaced[("POST", "/api/pronunciation/audio")],
            "pronunciation_audio_post_handler",
            handlers["pronunciation_audio_post"],
        ),
    ]
    if legacy_get_enabled:
        capture_checks.append(
            _captured_handler(
                replaced[PRONUNCIATION_LEGACY_ROUTE],
                "pronunciation_audio_legacy_handler",
                handlers["pronunciation_audio_legacy"],
            )
        )
    legacy_tts_handlers_captured = all(capture_checks)

    status_count = sum(1 for key in replaced if key == ("GET", "/api/pronunciation/status"))
    post_count = sum(1 for key in replaced if key == ("POST", "/api/pronunciation/audio"))
    legacy_count = sum(1 for key in replaced if key == PRONUNCIATION_LEGACY_ROUTE)

    report = PronunciationRouterBindingReport(
        ok=(
            len(replaced) == 2 + int(legacy_get_enabled)
            and status_count == 1
            and post_count == 1
            and legacy_count == int(legacy_get_enabled)
            and route_names_preserved
            and response_classes_preserved
            and legacy_get_deprecated_preserved
            and payload_schema_preserved
            and tts_max_chars_preserved
            and root_mount_order_preserved
            and router_module_owned
            and auth_core_bound
            and legacy_tts_handlers_captured
        ),
        route_count=len(replaced),
        status_route_count=status_count,
        post_audio_route_count=post_count,
        legacy_get_enabled=legacy_get_enabled,
        legacy_get_route_count=legacy_count,
        route_names_preserved=route_names_preserved,
        response_classes_preserved=response_classes_preserved,
        legacy_get_deprecated_preserved=legacy_get_deprecated_preserved,
        payload_schema_preserved=payload_schema_preserved,
        tts_max_chars_preserved=tts_max_chars_preserved,
        root_mount_order_preserved=root_mount_order_preserved,
        router_module_owned=router_module_owned,
        auth_core_bound=auth_core_bound,
        legacy_tts_handlers_captured=legacy_tts_handlers_captured,
    )
    if not report.ok:
        raise RuntimeError("v5.8.6 pronunciation router binding failed closed")
    module.MGC_PRONUNCIATION_ROUTER_BINDING_REPORT = report
    return report


__all__ = [
    "PRONUNCIATION_BASE_ROUTE_CONTRACT",
    "PRONUNCIATION_LEGACY_ROUTE",
    "PronunciationRouterBindingReport",
    "bind_pronunciation_router",
]
