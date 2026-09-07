from __future__ import annotations

from collections import Counter
from typing import Any

from prometheus_client import Gauge

from app.core.config import get_settings
from app.core.deployment_safety import deployment_safety_snapshot
from app.core.runtime_contract import APP_VERSION, SCHEMA_VERSION

HA_API_REPLICAS = Gauge("mgc_ha_api_replicas", "Compatible active stable API replicas observed")
HA_SCHEDULER_LEADERS = Gauge("mgc_ha_scheduler_leaders", "Active scheduler leaders observed")
HA_WORKER_REPLICAS = Gauge("mgc_ha_worker_replicas", "Compatible active worker replicas by role", ["role"])
HA_READY = Gauge("mgc_ha_ready", "1 when configured HA redundancy/coordination targets are observed")
HA_SPLIT_BRAIN_RISK = Gauge("mgc_ha_split_brain_risk", "1 when more than one active scheduler leader is observed")


def _worker_role(node: str | None) -> str:
    value = str(node or "unknown")
    role = value.split("@", 1)[0].strip().lower()
    return role if role in {"interactive", "cpu", "io", "cad", "ai", "maintenance"} else "unknown"


def _required_roles(value: str | None) -> list[str]:
    out=[]
    for raw in str(value or "interactive,cpu,io").split(","):
        role=raw.strip().lower()
        if role and role not in out:
            out.append(role)
    return out


def high_availability_snapshot(*, touch_api: bool = False) -> dict[str, Any]:
    """Return HA topology/coordination diagnostics without making Redis engineering truth.

    Deliberately, under-replication does not make an individual API instance unready: doing
    that would create a cascading outage exactly when one replica is lost. The gateway keeps
    serving from the surviving compatible API while Operations reports DEGRADED redundancy.
    """
    cfg=get_settings()
    enabled=bool(getattr(cfg, "ha_enabled", False))
    deployment=deployment_safety_snapshot(touch_api=touch_api)
    registry=str(deployment.get("registry_status") or "unavailable")
    rows=deployment.get("components") or []

    compatible=[r for r in rows if bool((r.get("compatibility") or {}).get("compatible"))]
    stable_apis=[r for r in compatible if r.get("component")=="api" and r.get("deployment_slot")=="stable" and r.get("state")=="active"]
    active_beats=[r for r in compatible if r.get("component")=="beat" and r.get("state")=="active"]
    standby_beats=[r for r in compatible if r.get("component")=="beat" and r.get("state")=="standby"]
    active_workers=[r for r in compatible if r.get("component")=="worker" and r.get("state")=="active"]
    role_counts=Counter(_worker_role(r.get("node")) for r in active_workers)
    role_counts.pop("unknown", None)

    min_api=max(int(getattr(cfg, "ha_min_api_replicas", 2)), 1)
    min_worker=max(int(getattr(cfg, "ha_min_worker_replicas_per_role", 2)), 1)
    roles=_required_roles(getattr(cfg, "ha_required_worker_roles", "interactive,cpu,io"))
    api_redundant=len(stable_apis) >= min_api
    worker_gaps={role:max(min_worker-int(role_counts.get(role,0)),0) for role in roles if int(role_counts.get(role,0)) < min_worker}
    worker_redundant=not worker_gaps
    split_brain=len(active_beats) > 1
    require_one=bool(getattr(cfg, "ha_require_single_scheduler_leader", True))
    scheduler_safe=(len(active_beats)==1) if require_one else (len(active_beats)<=1)
    incompatible=int(deployment.get("incompatible_components") or 0)

    if not enabled:
        status="DISABLED"
        ha_ready=False
    elif registry != "available":
        status="UNKNOWN"
        ha_ready=False
    else:
        ha_ready=api_redundant and worker_redundant and scheduler_safe and incompatible==0
        if split_brain or incompatible:
            status="UNSAFE"
        elif ha_ready:
            status="HEALTHY"
        else:
            status="DEGRADED"

    HA_API_REPLICAS.set(len(stable_apis))
    HA_SCHEDULER_LEADERS.set(len(active_beats))
    HA_SPLIT_BRAIN_RISK.set(1 if split_brain else 0)
    HA_READY.set(1 if ha_ready else 0)
    for role in ("interactive","cpu","io","cad","ai","maintenance"):
        HA_WORKER_REPLICAS.labels(role).set(int(role_counts.get(role,0)))

    return {
        "application_version": APP_VERSION,
        "schema_version": SCHEMA_VERSION,
        "enabled": enabled,
        "status": status,
        "registry_status": registry,
        "stable_api_replicas": len(stable_apis),
        "stable_api_nodes": [r.get("node") for r in stable_apis],
        "api_redundant": api_redundant,
        "scheduler_active_leaders": len(active_beats),
        "scheduler_standby_instances": len(standby_beats),
        "scheduler_single_leader": scheduler_safe,
        "split_brain_risk": split_brain,
        "worker_replicas_by_role": dict(sorted(role_counts.items())),
        "worker_replica_gaps": worker_gaps,
        "worker_redundant": worker_redundant,
        "ha_ready": ha_ready,
        "serving_capacity_present": len(stable_apis) >= 1,
        "policy": {
            "postgresql_authoritative": True,
            "redis_registry_authoritative": False,
            "under_replication_blocks_individual_api_readiness": False,
            "candidate_api_counts_toward_stable_redundancy": False,
            "minimum_api_replicas": min_api,
            "minimum_worker_replicas_per_required_role": min_worker,
            "required_worker_roles": roles,
            "single_scheduler_leader_required": require_one,
            "worker_lost_tasks_requeued_via_late_ack": True,
            "non_idempotent_gateway_retry_enabled": False,
            "ha_scope": "application_tier",
            "shared_evidence_storage_required_across_api_replicas": True,
            "postgresql_failover_managed_by_mgc": False,
            "external_entrypoint_redundancy_required_for_host_or_zone_ha": True,
            "physical_host_redundancy_requires_external_orchestrator_or_load_balancer": True,
            "full_stack_ha_claimed": False,
            "production_authorized": False,
        },
    }
