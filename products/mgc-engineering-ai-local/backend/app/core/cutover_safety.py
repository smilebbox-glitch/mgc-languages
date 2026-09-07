from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.core.config import get_settings
from app.core.deployment_safety import _semver, deployment_safety_snapshot
from app.core.runtime_contract import APP_VERSION, SCHEMA_VERSION


@dataclass(frozen=True)
class RollbackCompatibility:
    compatible: bool
    reason: str
    target_version: str | None
    target_schema: str | None
    current_version: str = APP_VERSION
    current_schema: str = SCHEMA_VERSION

    def public(self) -> dict[str, Any]:
        return {
            "compatible": self.compatible,
            "reason": self.reason,
            "target_version": self.target_version,
            "target_schema": self.target_schema,
            "current_version": self.current_version,
            "current_schema": self.current_schema,
        }


def rollback_compatibility(target_version: str | None, target_schema: str | None) -> RollbackCompatibility:
    """Fail closed before routing traffic back to an older API revision.

    Blue/green rollback is permitted only inside the current database-schema boundary and
    a tightly bounded patch window. This is intentionally stricter than generic task
    compatibility: schema-changing releases require an explicit restore/forward-fix plan.
    """
    cfg = get_settings()
    if target_schema != SCHEMA_VERSION:
        return RollbackCompatibility(False, "schema_rollback_forbidden", target_version, target_schema)
    current = _semver(APP_VERSION)
    target = _semver(target_version)
    if current is None or target is None:
        return RollbackCompatibility(False, "invalid_version", target_version, target_schema)
    if target[:2] != current[:2]:
        return RollbackCompatibility(False, "major_minor_rollback_forbidden", target_version, target_schema)
    max_patch = max(int(getattr(cfg, "cutover_max_patch_rollback_skew", 1)), 0)
    if target[2] > current[2]:
        return RollbackCompatibility(False, "target_is_newer_than_current", target_version, target_schema)
    if current[2] - target[2] > max_patch:
        return RollbackCompatibility(False, "rollback_patch_skew_exceeded", target_version, target_schema)
    return RollbackCompatibility(True, "compatible", target_version, target_schema)


def cutover_safety_snapshot(*, touch_api: bool = False) -> dict[str, Any]:
    cfg = get_settings()
    deployment = deployment_safety_snapshot(touch_api=touch_api)
    components = deployment.get("components") or []
    apis = [row for row in components if row.get("component") == "api"]
    stable = [row for row in apis if row.get("deployment_slot") == "stable"]
    candidate = [row for row in apis if row.get("deployment_slot") == "candidate"]

    candidate_compatible = all(bool((row.get("compatibility") or {}).get("compatible")) for row in candidate)
    rollback_targets = []
    for row in stable:
        rollback_targets.append({
            "node": row.get("node"),
            "app_version": row.get("app_version"),
            "schema_version": row.get("schema_version"),
            "rollback": rollback_compatibility(row.get("app_version"), row.get("schema_version")).public(),
        })
    rollback_safe = bool(rollback_targets) and all(x["rollback"]["compatible"] for x in rollback_targets)
    candidate_visible = len(candidate) > 0
    return {
        "application_version": APP_VERSION,
        "schema_version": SCHEMA_VERSION,
        "registry_status": deployment.get("registry_status"),
        "stable_api_components": stable,
        "candidate_api_components": candidate,
        "candidate_visible": candidate_visible,
        "candidate_runtime_compatible": candidate_visible and candidate_compatible,
        "rollback_targets": rollback_targets,
        "automatic_rollback_safe": rollback_safe,
        "cutover_preconditions_met": (
            deployment.get("registry_status") != "available"
            or (candidate_visible and candidate_compatible and int(deployment.get("incompatible_components") or 0) == 0)
        ),
        "policy": {
            "blue_green_enabled": bool(getattr(cfg, "blue_green_enabled", True)),
            "same_schema_required_for_automatic_rollback": True,
            "max_patch_rollback_skew": max(int(getattr(cfg, "cutover_max_patch_rollback_skew", 1)), 0),
            "candidate_min_ready_samples": max(int(getattr(cfg, "cutover_candidate_min_ready_samples", 3)), 1),
            "post_switch_samples": max(int(getattr(cfg, "cutover_post_switch_samples", 5)), 1),
            "failure_threshold": max(int(getattr(cfg, "cutover_failure_threshold", 2)), 1),
            "registry_is_diagnostic_not_authoritative": True,
            "production_authorized": False,
        },
    }
