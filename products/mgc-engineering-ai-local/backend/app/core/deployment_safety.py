from __future__ import annotations

import json
import os
import socket
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from prometheus_client import Gauge

from app.core.config import get_settings
from app.core.runtime_contract import APP_VERSION, SCHEMA_VERSION

DEPLOYMENT_VERSION_SKEW = Gauge(
    "mgc_deployment_version_skew",
    "Number of active deployment components incompatible with the current application runtime",
)
DEPLOYMENT_COMPONENTS = Gauge(
    "mgc_deployment_components",
    "Observed deployment components by type/state/compatibility",
    ["component", "state", "compatibility"],
)

_COMPONENT_PREFIX = "mgc:deployment:component:"


class RuntimeVersionSkew(RuntimeError):
    """Raised before task side effects when producer/consumer runtime is incompatible."""


@dataclass(frozen=True)
class RuntimeCompatibility:
    compatible: bool
    reason: str
    peer_version: str | None
    peer_schema: str | None
    legacy_envelope: bool = False

    def public(self) -> dict[str, Any]:
        return {
            "compatible": self.compatible,
            "reason": self.reason,
            "peer_version": self.peer_version,
            "peer_schema": self.peer_schema,
            "legacy_envelope": self.legacy_envelope,
        }


def _semver(value: str | None) -> tuple[int, int, int] | None:
    try:
        parts = str(value or "").strip().split(".")
        if len(parts) != 3:
            return None
        return tuple(int(x) for x in parts)  # type: ignore[return-value]
    except (TypeError, ValueError):
        return None


def runtime_identity(*, component: str, node: str | None = None, state: str = "active") -> dict[str, Any]:
    cfg = get_settings()
    return {
        "component": component,
        "node": (node or socket.gethostname())[:255],
        "state": state,
        "app_version": APP_VERSION,
        "schema_version": SCHEMA_VERSION,
        "deployment_profile": getattr(cfg, "runtime_profile", getattr(cfg, "deployment_profile", "unknown")),
        "deployment_slot": str(getattr(cfg, "deployment_slot", "stable"))[:32],
        "topology_node_id": str(getattr(cfg, "topology_node_id", "") or "")[:128],
        "topology_failure_domain": str(getattr(cfg, "topology_failure_domain", "") or "")[:128],
        "topology_node_role": str(getattr(cfg, "topology_node_role", "application") or "application")[:64],
        "observed_at": datetime.now(timezone.utc).isoformat(),
    }


def compatibility(peer_version: str | None, peer_schema: str | None) -> RuntimeCompatibility:
    cfg = get_settings()
    if peer_schema != SCHEMA_VERSION:
        return RuntimeCompatibility(False, "schema_mismatch", peer_version, peer_schema)
    current = _semver(APP_VERSION)
    peer = _semver(peer_version)
    if current is None or peer is None:
        return RuntimeCompatibility(False, "invalid_version", peer_version, peer_schema)
    if peer[:2] != current[:2]:
        return RuntimeCompatibility(False, "major_minor_skew", peer_version, peer_schema)
    max_patch = max(int(getattr(cfg, "rolling_upgrade_max_patch_skew", 1)), 0)
    if abs(peer[2] - current[2]) > max_patch:
        return RuntimeCompatibility(False, "patch_skew_exceeded", peer_version, peer_schema)
    return RuntimeCompatibility(True, "compatible", peer_version, peer_schema)


def task_publish_headers() -> dict[str, str]:
    cfg = get_settings()
    return {
        "mgc_app_version": APP_VERSION,
        "mgc_schema_version": SCHEMA_VERSION,
        "mgc_deployment_profile": str(getattr(cfg, "runtime_profile", getattr(cfg, "deployment_profile", "unknown"))),
    }


def validate_task_headers(headers: dict[str, Any] | None) -> RuntimeCompatibility:
    cfg = get_settings()
    if not bool(getattr(cfg, "rolling_upgrade_task_envelope_enabled", True)):
        return RuntimeCompatibility(True, "task_envelope_disabled", None, None)
    headers = headers or {}
    peer_version = headers.get("mgc_app_version")
    peer_schema = headers.get("mgc_schema_version")
    if not peer_version or not peer_schema:
        if bool(getattr(cfg, "rolling_upgrade_allow_legacy_task_envelopes", True)):
            return RuntimeCompatibility(True, "legacy_envelope_transition", None, None, legacy_envelope=True)
        raise RuntimeVersionSkew("MGC task envelope is missing version/schema compatibility metadata")
    result = compatibility(str(peer_version), str(peer_schema))
    if not result.compatible:
        raise RuntimeVersionSkew(
            f"MGC task runtime skew rejected before execution: {result.reason}; "
            f"producer={peer_version}/{peer_schema}, consumer={APP_VERSION}/{SCHEMA_VERSION}"
        )
    return result


def _redis_client():
    import redis

    cfg = get_settings()
    return redis.Redis.from_url(
        cfg.redis_url,
        decode_responses=True,
        socket_connect_timeout=cfg.health_timeout_seconds,
        socket_timeout=cfg.health_timeout_seconds,
    )


def component_key(component: str, node: str) -> str:
    safe_component = "".join(x for x in component.lower() if x.isalnum() or x in "_-")[:64] or "unknown"
    safe_node = "".join(x for x in node if x.isalnum() or x in "._@:-")[:255] or "unknown"
    return f"{_COMPONENT_PREFIX}{safe_component}:{safe_node}"


def record_component_heartbeat(component: str, *, node: str | None = None, state: str = "active") -> bool:
    """Best-effort ephemeral rollout telemetry. Redis is never deployment truth."""
    cfg = get_settings()
    if not bool(getattr(cfg, "rolling_upgrade_component_registry_enabled", True)):
        return False
    payload = runtime_identity(component=component, node=node, state=state)
    ttl = max(int(getattr(cfg, "deployment_component_heartbeat_ttl_seconds", 120)), 30)
    try:
        client = _redis_client()
        client.set(component_key(component, payload["node"]), json.dumps(payload, sort_keys=True), ex=ttl)
        return True
    except Exception:
        return False


def remove_component_heartbeat(component: str, *, node: str | None = None) -> None:
    try:
        client = _redis_client()
        client.delete(component_key(component, node or socket.gethostname()))
    except Exception:
        pass


def _component_registry() -> tuple[str, list[dict[str, Any]]]:
    cfg = get_settings()
    if not bool(getattr(cfg, "rolling_upgrade_component_registry_enabled", True)):
        return "disabled", []
    try:
        client = _redis_client()
        rows: list[dict[str, Any]] = []
        for key in client.scan_iter(match=f"{_COMPONENT_PREFIX}*", count=100):
            raw = client.get(key)
            if not raw:
                continue
            try:
                item = json.loads(raw)
            except json.JSONDecodeError:
                continue
            comp = compatibility(item.get("app_version"), item.get("schema_version"))
            rows.append({
                "component": str(item.get("component") or "unknown")[:64],
                "node": str(item.get("node") or "unknown")[:255],
                "state": str(item.get("state") or "unknown")[:32],
                "app_version": item.get("app_version"),
                "schema_version": item.get("schema_version"),
                "deployment_profile": str(item.get("deployment_profile") or "unknown")[:32],
                "deployment_slot": str(item.get("deployment_slot") or "stable")[:32],
                "topology_node_id": str(item.get("topology_node_id") or "")[:128],
                "topology_failure_domain": str(item.get("topology_failure_domain") or "")[:128],
                "topology_node_role": str(item.get("topology_node_role") or "application")[:64],
                "compatibility": comp.public(),
            })
        return "available", sorted(rows, key=lambda x: (x["component"], x["node"]))
    except Exception:
        return "unavailable", []


def deployment_safety_snapshot(*, touch_api: bool = False) -> dict[str, Any]:
    cfg = get_settings()
    if touch_api:
        record_component_heartbeat("api", node=f"api@{os.environ.get('HOSTNAME') or socket.gethostname()}")
    registry_status, rows = _component_registry()
    incompatible = [x for x in rows if not bool((x.get("compatibility") or {}).get("compatible"))]
    draining = [x for x in rows if x.get("state") == "draining"]
    DEPLOYMENT_VERSION_SKEW.set(len(incompatible))
    # Clear known label combinations before setting current observations.
    for component in ("api", "worker", "beat"):
        for state in ("active", "draining", "standby"):
            for compat in ("compatible", "incompatible"):
                DEPLOYMENT_COMPONENTS.labels(component, state, compat).set(0)
    counts: dict[tuple[str, str, str], int] = {}
    for row in rows:
        compat = "compatible" if (row.get("compatibility") or {}).get("compatible") else "incompatible"
        key = (str(row.get("component")), str(row.get("state")), compat)
        counts[key] = counts.get(key, 0) + 1
    for (component, state, compat), count in counts.items():
        DEPLOYMENT_COMPONENTS.labels(component, state, compat).set(count)
    return {
        "application_version": APP_VERSION,
        "schema_version": SCHEMA_VERSION,
        "registry_status": registry_status,
        "components": rows,
        "incompatible_components": len(incompatible),
        "draining_components": len(draining),
        "rolling_upgrade_safe": registry_status != "available" or len(incompatible) == 0,
        "policy": {
            "postgresql_authoritative": True,
            "registry_is_ephemeral": True,
            "max_patch_skew": max(int(getattr(cfg, "rolling_upgrade_max_patch_skew", 1)), 0),
            "same_schema_required": True,
            "legacy_task_envelopes_temporarily_allowed": bool(getattr(cfg, "rolling_upgrade_allow_legacy_task_envelopes", True)),
            "known_incompatible_component_blocks_readiness": True,
            "registry_outage_blocks_core": False,
        },
    }
