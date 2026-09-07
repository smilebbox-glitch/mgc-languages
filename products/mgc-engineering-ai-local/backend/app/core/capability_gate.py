from __future__ import annotations

import json
import re
from dataclasses import dataclass
from starlette.types import ASGIApp, Receive, Scope, Send

from app.core.config import get_settings
from app.core.runtime_contract import context_for_capability


@dataclass(frozen=True)
class CapabilityRouteRule:
    pattern: re.Pattern[str]
    feature: str

    @property
    def context(self) -> str | None:
        return context_for_capability(self.feature)


# Declarative compatibility gate for legacy endpoints. New v6.2 facades should use the same
# central runtime contract instead of inventing route-local feature switches.
ROUTE_CAPABILITY_RULES: tuple[CapabilityRouteRule, ...] = (
    CapabilityRouteRule(re.compile(r"^/api/v1/projects/[^/]+/(?:supplier-localization|localization)(?:/|$)"), "supplier_field"),
    CapabilityRouteRule(re.compile(r"^/api/v1/projects/[^/]+/field-intelligence(?:/|$)"), "advanced_field"),
    CapabilityRouteRule(re.compile(r"^/api/v1/projects/[^/]+/cost(?:-|/|$)"), "cost_economics"),
    CapabilityRouteRule(re.compile(r"^/api/v1/projects/[^/]+/program-control(?:/|$)"), "program_control"),
    CapabilityRouteRule(re.compile(r"^/api/v1/graph/[^/]+/(?:sync|neighborhood)$"), "neo4j_projection"),
    CapabilityRouteRule(re.compile(r"^/api/v1/cad/(?:gateways|native-formats|convert)(?:/|$)"), "native_cad_gateway"),
    CapabilityRouteRule(re.compile(r"^/api/v1/documents/[^/]+/visual-inspect$"), "local_vlm"),
    CapabilityRouteRule(re.compile(r"^/api/v1/objects/supplier(?:/|$)"), "supplier_field"),
)


def capability_for_path(path: str) -> CapabilityRouteRule | None:
    for rule in ROUTE_CAPABILITY_RULES:
        if rule.pattern.match(path):
            return rule
    return None


class CapabilityGateMiddleware:
    """Hide optional capability surfaces when the deployment profile disables them.

    This reduces operational/UI surface area. It does not grant access and does not replace ACL.
    The pre-auth response is deliberately generic so deployment posture is not disclosed to an
    unauthenticated caller. Authenticated users can inspect `/api/v1/runtime`.
    """
    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope.get("type") == "http":
            path = str(scope.get("path") or "")
            rule = capability_for_path(path)
            if rule and rule.feature not in get_settings().runtime_features:
                body = json.dumps({"detail": "Not found"}).encode()
                await send({
                    "type": "http.response.start",
                    "status": 404,
                    "headers": [(b"content-type", b"application/json"), (b"content-length", str(len(body)).encode())],
                })
                await send({"type": "http.response.body", "body": body})
                return
        await self.app(scope, receive, send)
