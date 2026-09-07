from types import SimpleNamespace
from pathlib import Path

from app.core import high_availability as ha
from app.core.runtime_contract import APP_VERSION, SCHEMA_VERSION


def settings(**kw):
    base=dict(ha_enabled=True, ha_min_api_replicas=2, ha_min_worker_replicas_per_role=2,
              ha_required_worker_roles="interactive,cpu,io", ha_require_single_scheduler_leader=True)
    base.update(kw); return SimpleNamespace(**base)


def row(component,node,state="active",slot="stable",compatible=True):
    return {"component":component,"node":node,"state":state,"deployment_slot":slot,
            "compatibility":{"compatible":compatible}}


def snapshot(rows, registry="available", incompatible=0):
    return {"registry_status":registry,"components":rows,"incompatible_components":incompatible}


def test_release_marker_without_schema_change():
    assert APP_VERSION == "6.3.34" and SCHEMA_VERSION == "6.3.13"


def test_two_api_two_required_workers_and_one_leader_are_healthy(monkeypatch):
    monkeypatch.setattr(ha,"get_settings",lambda:settings())
    rows=[row("api","api@a"),row("api","api@b"),row("beat","beat@a"),row("beat","beat@b","standby")]
    for role in ("interactive","cpu","io"):
        rows += [row("worker",f"{role}@a"),row("worker",f"{role}@b")]
    monkeypatch.setattr(ha,"deployment_safety_snapshot",lambda touch_api=False:snapshot(rows))
    s=ha.high_availability_snapshot()
    assert s["status"] == "HEALTHY" and s["ha_ready"] is True
    assert s["stable_api_replicas"] == 2 and s["scheduler_active_leaders"] == 1


def test_candidate_does_not_count_as_stable_redundancy(monkeypatch):
    monkeypatch.setattr(ha,"get_settings",lambda:settings())
    rows=[row("api","api@stable"),row("api","api@candidate",slot="candidate"),row("beat","beat@a")]
    monkeypatch.setattr(ha,"deployment_safety_snapshot",lambda touch_api=False:snapshot(rows))
    s=ha.high_availability_snapshot()
    assert s["stable_api_replicas"] == 1 and s["api_redundant"] is False


def test_draining_api_does_not_count(monkeypatch):
    monkeypatch.setattr(ha,"get_settings",lambda:settings())
    rows=[row("api","api@a"),row("api","api@b","draining"),row("beat","beat@a")]
    monkeypatch.setattr(ha,"deployment_safety_snapshot",lambda touch_api=False:snapshot(rows))
    assert ha.high_availability_snapshot()["stable_api_replicas"] == 1


def test_under_replication_is_degraded_not_cascading_core_failure(monkeypatch):
    monkeypatch.setattr(ha,"get_settings",lambda:settings())
    rows=[row("api","api@a"),row("beat","beat@a")]
    monkeypatch.setattr(ha,"deployment_safety_snapshot",lambda touch_api=False:snapshot(rows))
    s=ha.high_availability_snapshot()
    assert s["status"] == "DEGRADED" and s["serving_capacity_present"] is True
    assert s["policy"]["under_replication_blocks_individual_api_readiness"] is False


def test_two_active_scheduler_leaders_are_unsafe(monkeypatch):
    monkeypatch.setattr(ha,"get_settings",lambda:settings())
    rows=[row("api","api@a"),row("api","api@b"),row("beat","beat@a"),row("beat","beat@b")]
    monkeypatch.setattr(ha,"deployment_safety_snapshot",lambda touch_api=False:snapshot(rows))
    s=ha.high_availability_snapshot()
    assert s["status"] == "UNSAFE" and s["split_brain_risk"] is True and s["ha_ready"] is False


def test_worker_role_gap_is_explicit(monkeypatch):
    monkeypatch.setattr(ha,"get_settings",lambda:settings())
    rows=[row("api","api@a"),row("api","api@b"),row("beat","beat@a"),row("worker","cpu@a")]
    monkeypatch.setattr(ha,"deployment_safety_snapshot",lambda touch_api=False:snapshot(rows))
    s=ha.high_availability_snapshot()
    assert s["worker_replica_gaps"]["cpu"] == 1
    assert s["worker_replica_gaps"]["interactive"] == 2


def test_registry_outage_never_claims_ha(monkeypatch):
    monkeypatch.setattr(ha,"get_settings",lambda:settings())
    monkeypatch.setattr(ha,"deployment_safety_snapshot",lambda touch_api=False:snapshot([],"unavailable"))
    s=ha.high_availability_snapshot()
    assert s["status"] == "UNKNOWN" and s["ha_ready"] is False
    assert s["policy"]["redis_registry_authoritative"] is False
    assert s["policy"]["full_stack_ha_claimed"] is False


def test_disabled_base_topology_is_not_misrepresented(monkeypatch):
    monkeypatch.setattr(ha,"get_settings",lambda:settings(ha_enabled=False))
    monkeypatch.setattr(ha,"deployment_safety_snapshot",lambda touch_api=False:snapshot([]))
    assert ha.high_availability_snapshot()["status"] == "DISABLED"


def test_gateway_failover_never_enables_non_idempotent_replay():
    src=Path("ops/gateway/templates/ha.conf.template").read_text()
    assert "proxy_next_upstream" in src
    directives=[line.strip() for line in src.splitlines() if line.strip().startswith("proxy_next_upstream ")]
    assert directives and all("non_idempotent" not in line for line in directives)


def test_ha_compose_has_redundant_api_worker_and_beat():
    src=Path("docker-compose.ha.yml").read_text()
    for service in ("api-ha:","worker-ha:","worker-cpu-ha:","worker-io-ha:","beat-ha:","frontend-ha:"):
        assert service in src
    assert "HA_ENABLED: \"true\"" in src


def test_api_base_has_local_readiness_healthcheck():
    src=Path("docker-compose.yml").read_text()
    api=src[src.index("  api:"):src.index("  worker:")]
    assert "/api/v1/health/ready" in api and "healthcheck:" in api
