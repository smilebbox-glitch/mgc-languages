from __future__ import annotations

from dataclasses import dataclass
from types import ModuleType

from fastapi import FastAPI
from fastapi.routing import APIRoute
from starlette.routing import Mount

from mgc.routers.pilot_admin import (
    FeatureFlagPayload,
    PILOT_ADMIN_HANDLER_NAMES,
    PilotFeaturePayload,
    PilotGroupPayload,
    PilotGroupStatusPayload,
    PilotGroupUpdatePayload,
    TrackAssignmentPayload,
    build_pilot_admin_router,
)


PILOT_ADMIN_ROUTE_CONTRACT = {
    ("GET", "/api/admin/pilot/groups"),
    ("POST", "/api/admin/pilot/groups"),
    ("PATCH", "/api/admin/pilot/groups/{group_id}/status"),
    ("PATCH", "/api/admin/pilot/groups/{group_id}"),
    ("POST", "/api/admin/pilot/groups/{group_id}/members/{user_id}"),
    ("DELETE", "/api/admin/pilot/groups/{group_id}/members/{user_id}"),
    ("GET", "/api/admin/pilot/features"),
    ("POST", "/api/admin/pilot/features"),
    ("PUT", "/api/admin/pilot/groups/{group_id}/features/{flag_key}"),
    ("POST", "/api/admin/pilot/groups/{group_id}/assignments"),
    ("DELETE", "/api/admin/pilot/groups/{group_id}/assignments/{assignment_id}"),
    ("GET", "/api/admin/pilot/export.csv"),
    ("GET", "/api/admin/pilot/governance-summary"),
}


@dataclass(frozen=True)
class PilotAdminRouterBindingReport:
    ok: bool
    route_count: int
    group_route_count: int
    feature_route_count: int
    assignment_route_count: int
    export_route_count: int
    governance_route_count: int
    mutation_route_count: int
    route_names_preserved: bool
    response_classes_preserved: bool
    payload_schemas_preserved: bool
    root_mount_order_preserved: bool
    router_module_owned: bool
    auth_core_bound: bool
    user_service_bound: bool
    governance_core_bound: bool


def _key(route: APIRoute) -> tuple[str, str]:
    methods = sorted((route.methods or set()) - {"HEAD", "OPTIONS"})
    if len(methods) != 1:
        raise RuntimeError(f"pilot admin route must have one explicit method: {route.path} {methods}")
    return methods[0], route.path


def _single_route_index(application: FastAPI, key: tuple[str, str]) -> int:
    matches = [
        index
        for index, route in enumerate(application.router.routes)
        if isinstance(route, APIRoute) and _key(route) == key
    ]
    if len(matches) != 1:
        raise RuntimeError(
            f"pilot admin route contract drifted for {key[0]} {key[1]}: {len(matches)} matches"
        )
    return matches[0]


def _payload_contract(module: ModuleType) -> bool:
    pairs = (
        ("PilotGroupPayload", PilotGroupPayload),
        ("PilotGroupUpdatePayload", PilotGroupUpdatePayload),
        ("PilotGroupStatusPayload", PilotGroupStatusPayload),
        ("PilotFeaturePayload", PilotFeaturePayload),
        ("FeatureFlagPayload", FeatureFlagPayload),
        ("TrackAssignmentPayload", TrackAssignmentPayload),
    )
    for legacy_name, extracted in pairs:
        legacy = getattr(module, legacy_name, None)
        if not callable(getattr(legacy, "model_json_schema", None)):
            return False
        if legacy.model_json_schema() != extracted.model_json_schema():
            return False
    return True


def bind_pilot_admin_router(
    module: ModuleType,
    application: FastAPI,
) -> PilotAdminRouterBindingReport:
    """Replace thirteen pilot-administration APIRoutes with a dedicated router."""
    existing = getattr(module, "MGC_PILOT_ADMIN_ROUTER_BINDING_REPORT", None)
    if isinstance(existing, PilotAdminRouterBindingReport) and existing.ok:
        return existing

    required = (
        "db_session",
        "require_roles",
        "user_admin_stats",
        "audit_event",
        "PilotGroupPayload",
        "PilotGroupUpdatePayload",
        "PilotGroupStatusPayload",
        "PilotFeaturePayload",
        "FeatureFlagPayload",
        "TrackAssignmentPayload",
        *PILOT_ADMIN_HANDLER_NAMES,
    )
    missing = [name for name in required if not hasattr(module, name)]
    if missing:
        raise RuntimeError(f"legacy pilot admin dependencies are incomplete: {missing}")

    auth_core_bound = getattr(module.require_roles, "__module__", "") == "mgc.auth_core"
    if not auth_core_bound:
        raise RuntimeError("pilot admin router must bind after extracted auth core")

    users = getattr(module, "MGC_USER_SERVICE_BINDINGS", None)
    user_service_bound = bool(users) and module.user_admin_stats is users.user_admin_stats
    if not user_service_bound:
        raise RuntimeError("pilot admin router must bind after extracted user service")

    governance = getattr(module, "MGC_GOVERNANCE_BINDINGS", None)
    governance_core_bound = bool(governance) and module.audit_event is governance.audit_event
    if not governance_core_bound:
        raise RuntimeError("pilot admin router must bind after extracted governance core")

    payload_schemas_preserved = _payload_contract(module)
    if not payload_schemas_preserved:
        raise RuntimeError("pilot admin payload contract drifted")

    handlers = {name: getattr(module, name) for name in PILOT_ADMIN_HANDLER_NAMES}
    extracted = build_pilot_admin_router(
        db_session=module.db_session,
        require_roles=module.require_roles,
        handlers=handlers,
    )
    new_routes = {_key(route): route for route in extracted.routes if isinstance(route, APIRoute)}
    if set(new_routes) != PILOT_ADMIN_ROUTE_CONTRACT:
        raise RuntimeError(
            "extracted pilot admin router contract drifted: "
            + str(sorted(set(new_routes) ^ PILOT_ADMIN_ROUTE_CONTRACT))
        )

    originals: dict[tuple[str, str], APIRoute] = {}
    replaced: dict[tuple[str, str], APIRoute] = {}
    indexes: list[int] = []
    route_names_preserved = True
    response_classes_preserved = True

    for key in sorted(PILOT_ADMIN_ROUTE_CONTRACT):
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

    module.MGC_LEGACY_PILOT_ADMIN_ROUTES = originals
    module.MGC_PILOT_ADMIN_ROUTER = extracted

    mount_indices = [
        index
        for index, route in enumerate(application.router.routes)
        if isinstance(route, Mount) and getattr(route, "name", None) == "static"
    ]
    root_mount_order_preserved = bool(mount_indices) and all(index < mount_indices[0] for index in indexes)
    router_module_owned = all(
        route.endpoint.__module__ == "mgc.routers.pilot_admin" for route in replaced.values()
    )

    group_count = sum(1 for key in replaced if key[1].startswith("/api/admin/pilot/groups"))
    feature_count = sum(1 for key in replaced if key[1] == "/api/admin/pilot/features")
    assignment_count = sum(1 for key in replaced if "/assignments" in key[1])
    export_count = sum(1 for key in replaced if key[1] == "/api/admin/pilot/export.csv")
    governance_count = sum(1 for key in replaced if key[1] == "/api/admin/pilot/governance-summary")
    mutation_count = sum(1 for key in replaced if key[0] in {"POST", "PUT", "PATCH", "DELETE"})

    report = PilotAdminRouterBindingReport(
        ok=(
            len(replaced) == 13
            and group_count == 9
            and feature_count == 2
            and assignment_count == 2
            and export_count == 1
            and governance_count == 1
            and mutation_count == 9
            and route_names_preserved
            and response_classes_preserved
            and payload_schemas_preserved
            and root_mount_order_preserved
            and router_module_owned
            and auth_core_bound
            and user_service_bound
            and governance_core_bound
        ),
        route_count=len(replaced),
        group_route_count=group_count,
        feature_route_count=feature_count,
        assignment_route_count=assignment_count,
        export_route_count=export_count,
        governance_route_count=governance_count,
        mutation_route_count=mutation_count,
        route_names_preserved=route_names_preserved,
        response_classes_preserved=response_classes_preserved,
        payload_schemas_preserved=payload_schemas_preserved,
        root_mount_order_preserved=root_mount_order_preserved,
        router_module_owned=router_module_owned,
        auth_core_bound=auth_core_bound,
        user_service_bound=user_service_bound,
        governance_core_bound=governance_core_bound,
    )
    if not report.ok:
        raise RuntimeError("v5.8.9 pilot admin router binding failed closed")
    module.MGC_PILOT_ADMIN_ROUTER_BINDING_REPORT = report
    return report


__all__ = [
    "PILOT_ADMIN_ROUTE_CONTRACT",
    "PilotAdminRouterBindingReport",
    "bind_pilot_admin_router",
]
