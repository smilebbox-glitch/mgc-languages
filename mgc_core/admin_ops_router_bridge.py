from __future__ import annotations

from dataclasses import dataclass
from types import ModuleType

from fastapi import FastAPI
from fastapi.routing import APIRoute
from starlette.routing import Mount

from mgc.routers.admin_ops import (
    ADMIN_OPS_HANDLER_NAMES,
    AlertAckPayload,
    build_admin_ops_router,
)


ADMIN_OPS_ROUTE_CONTRACT = {
    ("GET", "/api/admin/slo"),
    ("GET", "/api/admin/alerts"),
    ("PATCH", "/api/admin/alerts/{alert_id}/ack"),
    ("GET", "/api/admin/learning-error-telemetry"),
    ("GET", "/api/admin/pilot-telemetry"),
    ("GET", "/api/admin/analytics"),
    ("GET", "/api/admin/audit"),
    ("GET", "/api/admin/database/telemetry"),
    ("GET", "/api/admin/recovery/evidence"),
    ("GET", "/api/admin/it-dashboard"),
    ("POST", "/api/admin/maintenance/cleanup"),
    ("GET", "/api/admin/operational-events"),
    ("GET", "/api/admin/system/summary"),
}


@dataclass(frozen=True)
class AdminOpsRouterBindingReport:
    ok: bool
    route_count: int
    telemetry_route_count: int
    recovery_route_count: int
    alert_route_count: int
    mutation_route_count: int
    route_names_preserved: bool
    response_classes_preserved: bool
    payload_schema_preserved: bool
    root_mount_order_preserved: bool
    router_module_owned: bool
    auth_core_bound: bool
    user_service_bound: bool
    governance_core_bound: bool
    tts_core_bound: bool


def _key(route: APIRoute) -> tuple[str, str]:
    methods = sorted((route.methods or set()) - {"HEAD", "OPTIONS"})
    if len(methods) != 1:
        raise RuntimeError(f"admin ops route must have one explicit method: {route.path} {methods}")
    return methods[0], route.path


def _single_route_index(application: FastAPI, key: tuple[str, str]) -> int:
    matches = [
        index
        for index, route in enumerate(application.router.routes)
        if isinstance(route, APIRoute) and _key(route) == key
    ]
    if len(matches) != 1:
        raise RuntimeError(
            f"admin ops route contract drifted for {key[0]} {key[1]}: {len(matches)} matches"
        )
    return matches[0]


def bind_admin_ops_router(
    module: ModuleType,
    application: FastAPI,
) -> AdminOpsRouterBindingReport:
    """Replace thirteen admin operations APIRoutes with a dedicated router."""
    existing = getattr(module, "MGC_ADMIN_OPS_ROUTER_BINDING_REPORT", None)
    if isinstance(existing, AdminOpsRouterBindingReport) and existing.ok:
        return existing

    required = (
        "db_session",
        "require_roles",
        "user_admin_stats",
        "audit_event",
        "_tts_health",
        "AlertAckPayload",
        *ADMIN_OPS_HANDLER_NAMES,
    )
    missing = [name for name in required if not hasattr(module, name)]
    if missing:
        raise RuntimeError(f"legacy admin ops dependencies are incomplete: {missing}")

    auth_core_bound = getattr(module.require_roles, "__module__", "") == "mgc.auth_core"
    if not auth_core_bound:
        raise RuntimeError("admin ops router must bind after extracted auth core")

    users = getattr(module, "MGC_USER_SERVICE_BINDINGS", None)
    user_service_bound = bool(users) and module.user_admin_stats is users.user_admin_stats
    if not user_service_bound:
        raise RuntimeError("admin ops router must bind after extracted user service")

    governance = getattr(module, "MGC_GOVERNANCE_BINDINGS", None)
    governance_core_bound = bool(governance) and module.audit_event is governance.audit_event
    if not governance_core_bound:
        raise RuntimeError("admin ops router must bind after extracted governance core")

    tts = getattr(module, "MGC_TTS_CORE_BINDINGS", None)
    tts_core_bound = bool(tts) and module._tts_health is tts.health
    if not tts_core_bound:
        raise RuntimeError("admin ops router must bind after extracted TTS core")

    legacy_payload = getattr(module, "AlertAckPayload")
    payload_schema_preserved = (
        callable(getattr(legacy_payload, "model_json_schema", None))
        and legacy_payload.model_json_schema() == AlertAckPayload.model_json_schema()
    )
    if not payload_schema_preserved:
        raise RuntimeError("admin ops alert payload contract drifted")

    handlers = {name: getattr(module, name) for name in ADMIN_OPS_HANDLER_NAMES}
    extracted = build_admin_ops_router(
        db_session=module.db_session,
        require_roles=module.require_roles,
        handlers=handlers,
    )
    new_routes = {_key(route): route for route in extracted.routes if isinstance(route, APIRoute)}
    if set(new_routes) != ADMIN_OPS_ROUTE_CONTRACT:
        raise RuntimeError(
            "extracted admin ops router contract drifted: "
            + str(sorted(set(new_routes) ^ ADMIN_OPS_ROUTE_CONTRACT))
        )

    originals: dict[tuple[str, str], APIRoute] = {}
    replaced: dict[tuple[str, str], APIRoute] = {}
    indexes: list[int] = []
    route_names_preserved = True
    response_classes_preserved = True

    for key in sorted(ADMIN_OPS_ROUTE_CONTRACT):
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

    module.MGC_LEGACY_ADMIN_OPS_ROUTES = originals
    module.MGC_ADMIN_OPS_ROUTER = extracted

    mount_indices = [
        index
        for index, route in enumerate(application.router.routes)
        if isinstance(route, Mount) and getattr(route, "name", None) == "static"
    ]
    root_mount_order_preserved = bool(mount_indices) and all(index < mount_indices[0] for index in indexes)
    router_module_owned = all(
        route.endpoint.__module__ == "mgc.routers.admin_ops" for route in replaced.values()
    )

    alert_count = sum(1 for key in replaced if "/alerts" in key[1])
    recovery_count = sum(
        1 for key in replaced
        if key[1] in {"/api/admin/recovery/evidence", "/api/admin/slo", "/api/admin/it-dashboard", "/api/admin/system/summary"}
    )
    telemetry_count = sum(
        1 for key in replaced
        if key[1] in {
            "/api/admin/learning-error-telemetry",
            "/api/admin/pilot-telemetry",
            "/api/admin/analytics",
            "/api/admin/audit",
            "/api/admin/database/telemetry",
            "/api/admin/operational-events",
        }
    )
    mutation_count = sum(1 for key in replaced if key[0] in {"POST", "PUT", "PATCH", "DELETE"})

    report = AdminOpsRouterBindingReport(
        ok=(
            len(replaced) == 13
            and alert_count == 2
            and recovery_count == 4
            and telemetry_count == 6
            and mutation_count == 2
            and route_names_preserved
            and response_classes_preserved
            and payload_schema_preserved
            and root_mount_order_preserved
            and router_module_owned
            and auth_core_bound
            and user_service_bound
            and governance_core_bound
            and tts_core_bound
        ),
        route_count=len(replaced),
        telemetry_route_count=telemetry_count,
        recovery_route_count=recovery_count,
        alert_route_count=alert_count,
        mutation_route_count=mutation_count,
        route_names_preserved=route_names_preserved,
        response_classes_preserved=response_classes_preserved,
        payload_schema_preserved=payload_schema_preserved,
        root_mount_order_preserved=root_mount_order_preserved,
        router_module_owned=router_module_owned,
        auth_core_bound=auth_core_bound,
        user_service_bound=user_service_bound,
        governance_core_bound=governance_core_bound,
        tts_core_bound=tts_core_bound,
    )
    if not report.ok:
        raise RuntimeError("v5.9.0 admin ops router binding failed closed")
    module.MGC_ADMIN_OPS_ROUTER_BINDING_REPORT = report
    return report


__all__ = [
    "ADMIN_OPS_ROUTE_CONTRACT",
    "AdminOpsRouterBindingReport",
    "bind_admin_ops_router",
]
