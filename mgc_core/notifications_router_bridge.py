from __future__ import annotations

from dataclasses import dataclass
from types import ModuleType

from fastapi import FastAPI
from fastapi.routing import APIRoute
from starlette.routing import Mount

from mgc.routers.notifications import (
    NOTIFICATION_HANDLER_NAMES,
    NotificationSettingsPayload,
    build_notifications_router,
)


NOTIFICATION_ROUTE_CONTRACT = {
    ("GET", "/api/notifications/settings"),
    ("PUT", "/api/notifications/settings"),
    ("GET", "/api/notifications/pending"),
    ("POST", "/api/notifications/{nudge_id}/read"),
}


@dataclass(frozen=True)
class NotificationsRouterBindingReport:
    ok: bool
    route_count: int
    settings_route_count: int
    nudge_route_count: int
    mutation_route_count: int
    route_names_preserved: bool
    response_classes_preserved: bool
    payload_schema_preserved: bool
    root_mount_order_preserved: bool
    router_module_owned: bool
    auth_core_bound: bool
    learning_service_bound: bool


def _key(route: APIRoute) -> tuple[str, str]:
    methods = sorted((route.methods or set()) - {"HEAD", "OPTIONS"})
    if len(methods) != 1:
        raise RuntimeError(f"notification route must have one explicit method: {route.path} {methods}")
    return methods[0], route.path


def _single_route_index(application: FastAPI, key: tuple[str, str]) -> int:
    matches = [
        index
        for index, route in enumerate(application.router.routes)
        if isinstance(route, APIRoute) and _key(route) == key
    ]
    if len(matches) != 1:
        raise RuntimeError(
            f"notification route contract drifted for {key[0]} {key[1]}: {len(matches)} matches"
        )
    return matches[0]


def bind_notifications_router(
    module: ModuleType,
    application: FastAPI,
) -> NotificationsRouterBindingReport:
    """Replace notification/settings APIRoutes with a dedicated router."""
    existing = getattr(module, "MGC_NOTIFICATIONS_ROUTER_BINDING_REPORT", None)
    if isinstance(existing, NotificationsRouterBindingReport) and existing.ok:
        return existing

    required = (
        "db_session",
        "current_user",
        "get_profile",
        "NotificationSettingsPayload",
        *NOTIFICATION_HANDLER_NAMES,
    )
    missing = [name for name in required if not hasattr(module, name)]
    if missing:
        raise RuntimeError(f"legacy notification dependencies are incomplete: {missing}")

    auth_core_bound = getattr(module.current_user, "__module__", "") == "mgc.auth_core"
    if not auth_core_bound:
        raise RuntimeError("notifications router must bind after extracted auth core")

    learning = getattr(module, "MGC_LEARNING_SERVICE_BINDINGS", None)
    learning_service_bound = bool(learning) and module.get_profile is learning.get_profile
    if not learning_service_bound:
        raise RuntimeError("notifications router must bind after extracted learning service")

    legacy_payload = getattr(module, "NotificationSettingsPayload")
    payload_schema_preserved = (
        callable(getattr(legacy_payload, "model_json_schema", None))
        and legacy_payload.model_json_schema() == NotificationSettingsPayload.model_json_schema()
    )
    if not payload_schema_preserved:
        raise RuntimeError("notification settings payload contract drifted")

    handlers = {name: getattr(module, name) for name in NOTIFICATION_HANDLER_NAMES}
    extracted = build_notifications_router(
        db_session=module.db_session,
        current_user=module.current_user,
        handlers=handlers,
    )
    new_routes = {_key(route): route for route in extracted.routes if isinstance(route, APIRoute)}
    if set(new_routes) != NOTIFICATION_ROUTE_CONTRACT:
        raise RuntimeError(
            "extracted notifications router contract drifted: "
            + str(sorted(set(new_routes) ^ NOTIFICATION_ROUTE_CONTRACT))
        )

    originals: dict[tuple[str, str], APIRoute] = {}
    replaced: dict[tuple[str, str], APIRoute] = {}
    indexes: list[int] = []
    route_names_preserved = True
    response_classes_preserved = True

    for key in sorted(NOTIFICATION_ROUTE_CONTRACT):
        index = _single_route_index(application, key)
        indexes.append(index)
        old_route = application.router.routes[index]
        assert isinstance(old_route, APIRoute)
        new_route = new_routes[key]
        route_names_preserved = route_names_preserved and old_route.name == new_route.name
        response_classes_preserved = response_classes_preserved and old_route.response_class == new_route.response_class
        originals[key] = old_route
        application.router.routes[index] = new_route
        replaced[key] = new_route
        setattr(module, old_route.name, new_route.endpoint)

    module.MGC_LEGACY_NOTIFICATION_ROUTES = originals
    module.MGC_NOTIFICATIONS_ROUTER = extracted

    mount_indices = [
        index
        for index, route in enumerate(application.router.routes)
        if isinstance(route, Mount) and getattr(route, "name", None) == "static"
    ]
    root_mount_order_preserved = bool(mount_indices) and all(index < mount_indices[0] for index in indexes)
    router_module_owned = all(
        route.endpoint.__module__ == "mgc.routers.notifications" for route in replaced.values()
    )
    settings_count = sum(1 for key in replaced if key[1] == "/api/notifications/settings")
    nudge_count = len(replaced) - settings_count
    mutation_count = sum(1 for key in replaced if key[0] in {"POST", "PUT", "PATCH", "DELETE"})

    report = NotificationsRouterBindingReport(
        ok=(
            len(replaced) == 4
            and settings_count == 2
            and nudge_count == 2
            and mutation_count == 2
            and route_names_preserved
            and response_classes_preserved
            and payload_schema_preserved
            and root_mount_order_preserved
            and router_module_owned
            and auth_core_bound
            and learning_service_bound
        ),
        route_count=len(replaced),
        settings_route_count=settings_count,
        nudge_route_count=nudge_count,
        mutation_route_count=mutation_count,
        route_names_preserved=route_names_preserved,
        response_classes_preserved=response_classes_preserved,
        payload_schema_preserved=payload_schema_preserved,
        root_mount_order_preserved=root_mount_order_preserved,
        router_module_owned=router_module_owned,
        auth_core_bound=auth_core_bound,
        learning_service_bound=learning_service_bound,
    )
    if not report.ok:
        raise RuntimeError("v5.9.1 notifications router binding failed closed")
    module.MGC_NOTIFICATIONS_ROUTER_BINDING_REPORT = report
    return report


__all__ = [
    "NOTIFICATION_ROUTE_CONTRACT",
    "NotificationsRouterBindingReport",
    "bind_notifications_router",
]
