from __future__ import annotations

from collections import defaultdict
from typing import Any

from prometheus_client import Gauge

from app.core.config import get_settings
from app.core.deployment_safety import deployment_safety_snapshot
from app.core.high_availability import _worker_role
from app.core.runtime_contract import APP_VERSION, SCHEMA_VERSION

TOPOLOGY_DOMAINS = Gauge("mgc_topology_failure_domains", "Compatible active stable failure domains observed")
TOPOLOGY_API_DOMAINS = Gauge("mgc_topology_api_failure_domains", "Failure domains carrying compatible active stable APIs")
TOPOLOGY_READY = Gauge("mgc_topology_ready", "1 when configured multi-host topology placement targets are observed")
TOPOLOGY_IDENTITY_CONFLICT = Gauge("mgc_topology_identity_conflict", "1 when a topology node id is observed in multiple failure domains")
TOPOLOGY_WORKER_DOMAINS = Gauge("mgc_topology_worker_failure_domains", "Failure domains carrying compatible worker role", ["role"])


def _required_roles(value: str | None) -> list[str]:
    out: list[str] = []
    for raw in str(value or "interactive,cpu,io").split(","):
        role = raw.strip().lower()
        if role and role not in out:
            out.append(role)
    return out


def _identity_conflicts(rows: list[dict[str, Any]]) -> dict[str, list[str]]:
    domains_by_node: dict[str, set[str]] = defaultdict(set)
    for row in rows:
        node_id = str(row.get("topology_node_id") or "").strip()
        domain = str(row.get("topology_failure_domain") or "").strip()
        if node_id and domain:
            domains_by_node[node_id].add(domain)
    return {node: sorted(domains) for node, domains in domains_by_node.items() if len(domains) > 1}


def multi_host_topology_snapshot(*, touch_api: bool = False) -> dict[str, Any]:
    """Observe placement/failure-domain safety without turning Redis into topology truth.

    The registry is ephemeral evidence for operations/certification. Under-replication never
    makes a surviving API instance unready; the external LB uses the local /health/lb contract.
    """
    cfg = get_settings()
    enabled = bool(getattr(cfg, "multi_host_topology_enabled", False))
    deployment = deployment_safety_snapshot(touch_api=touch_api)
    registry = str(deployment.get("registry_status") or "unavailable")
    rows = deployment.get("components") or []
    compatible = [r for r in rows if bool((r.get("compatibility") or {}).get("compatible"))]
    active = [r for r in compatible if r.get("state") == "active" and r.get("deployment_slot") == "stable"]

    labeled = [r for r in active if str(r.get("topology_node_id") or "").strip() and str(r.get("topology_failure_domain") or "").strip()]
    unlabeled = [r for r in active if r not in labeled]
    all_domains = {str(r.get("topology_failure_domain")) for r in labeled}
    api_domains = {str(r.get("topology_failure_domain")) for r in labeled if r.get("component") == "api"}
    worker_domains: dict[str, set[str]] = defaultdict(set)
    for row in labeled:
        if row.get("component") == "worker":
            worker_domains[_worker_role(row.get("node"))].add(str(row.get("topology_failure_domain")))
    worker_domains.pop("unknown", None)

    min_domains = max(int(getattr(cfg, "topology_min_failure_domains", 2)), 1)
    min_api_domains = max(int(getattr(cfg, "topology_min_api_failure_domains", 2)), 1)
    min_worker_domains = max(int(getattr(cfg, "topology_min_worker_failure_domains", 2)), 1)
    required_roles = _required_roles(getattr(cfg, "topology_required_worker_roles", "interactive,cpu,io"))
    role_gaps = {
        role: max(min_worker_domains - len(worker_domains.get(role, set())), 0)
        for role in required_roles
        if len(worker_domains.get(role, set())) < min_worker_domains
    }
    conflicts = _identity_conflicts(labeled)
    incompatible = int(deployment.get("incompatible_components") or 0)
    labels_complete = len(unlabeled) == 0
    domain_redundant = len(all_domains) >= min_domains
    api_spread = len(api_domains) >= min_api_domains
    worker_spread = not role_gaps

    if not enabled:
        status = "DISABLED"
        ready = False
    elif registry != "available":
        status = "UNKNOWN"
        ready = False
    else:
        ready = labels_complete and domain_redundant and api_spread and worker_spread and not conflicts and incompatible == 0
        if conflicts or incompatible:
            status = "UNSAFE"
        elif ready:
            status = "HEALTHY"
        else:
            status = "DEGRADED"

    TOPOLOGY_DOMAINS.set(len(all_domains))
    TOPOLOGY_API_DOMAINS.set(len(api_domains))
    TOPOLOGY_READY.set(1 if ready else 0)
    TOPOLOGY_IDENTITY_CONFLICT.set(1 if conflicts else 0)
    for role in ("interactive", "cpu", "io", "cad", "ai", "maintenance"):
        TOPOLOGY_WORKER_DOMAINS.labels(role).set(len(worker_domains.get(role, set())))

    return {
        "application_version": APP_VERSION,
        "schema_version": SCHEMA_VERSION,
        "enabled": enabled,
        "status": status,
        "registry_status": registry,
        "failure_domains": sorted(all_domains),
        "failure_domain_count": len(all_domains),
        "api_failure_domains": sorted(api_domains),
        "api_failure_domain_count": len(api_domains),
        "worker_failure_domains_by_role": {role: sorted(domains) for role, domains in sorted(worker_domains.items())},
        "worker_failure_domain_gaps": role_gaps,
        "unlabeled_active_components": len(unlabeled),
        "node_identity_conflicts": conflicts,
        "topology_ready": ready,
        "serving_capacity_present": bool(api_domains),
        "policy": {
            "minimum_failure_domains": min_domains,
            "minimum_api_failure_domains": min_api_domains,
            "minimum_worker_failure_domains": min_worker_domains,
            "required_worker_roles": required_roles,
            "anti_affinity_required_across_failure_domains": True,
            "external_load_balancer_required": bool(getattr(cfg, "topology_external_lb_required", True)),
            "external_load_balancer_health_path": str(getattr(cfg, "topology_external_lb_health_path", "/api/v1/health/lb")),
            "external_lb_non_idempotent_retry_enabled": False,
            "registry_is_ephemeral": True,
            "under_replication_blocks_individual_api_readiness": False,
            "authoritative_db_evidence_fencing_required": True,
            "multi_host_compose_is_per_node_not_an_orchestrator": True,
            "host_or_zone_placement_must_be_enforced_externally": True,
            "performance_profile_is_capacity_reference_not_certification": True,
            "production_authorized": False,
        },
    }
