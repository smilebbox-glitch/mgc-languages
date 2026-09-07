from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

from app.core import multi_host_topology as topo
from app.core import deployment_safety as ds
from app.core.runtime_contract import APP_VERSION, SCHEMA_VERSION


def settings(**kw):
    base=dict(
        multi_host_topology_enabled=True,
        topology_min_failure_domains=2,
        topology_min_api_failure_domains=2,
        topology_min_worker_failure_domains=2,
        topology_required_worker_roles="interactive,cpu,io",
        topology_external_lb_required=True,
        topology_external_lb_health_path="/api/v1/health/lb",
        runtime_profile="core",
        deployment_slot="stable",
        topology_node_id="node-a",
        topology_failure_domain="host-a",
        topology_node_role="application",
    )
    base.update(kw)
    return SimpleNamespace(**base)


def row(component,node,domain,node_id=None,state="active",slot="stable",compatible=True):
    return {
        "component":component,"node":node,"state":state,"deployment_slot":slot,
        "topology_node_id":node_id or node.split("@")[-1],"topology_failure_domain":domain,
        "topology_node_role":"application","compatibility":{"compatible":compatible},
    }


def snapshot(rows, registry="available", incompatible=0):
    return {"registry_status":registry,"components":rows,"incompatible_components":incompatible}


def healthy_rows():
    rows=[row("api","api@a","host-a","a"),row("api","api@b","host-b","b")]
    for role in ("interactive","cpu","io"):
        rows += [row("worker",f"{role}@a","host-a","a"),row("worker",f"{role}@b","host-b","b")]
    return rows


def test_release_marker_without_schema_change():
    assert APP_VERSION == "6.3.34" and SCHEMA_VERSION == "6.3.13"


def test_runtime_identity_carries_topology_labels(monkeypatch):
    monkeypatch.setattr(ds,"get_settings",lambda:settings())
    ident=ds.runtime_identity(component="api",node="api@node-a")
    assert ident["topology_node_id"] == "node-a"
    assert ident["topology_failure_domain"] == "host-a"


def test_two_failure_domains_are_healthy(monkeypatch):
    monkeypatch.setattr(topo,"get_settings",lambda:settings())
    monkeypatch.setattr(topo,"deployment_safety_snapshot",lambda touch_api=False:snapshot(healthy_rows()))
    out=topo.multi_host_topology_snapshot()
    assert out["status"] == "HEALTHY" and out["topology_ready"] is True
    assert out["api_failure_domain_count"] == 2


def test_candidate_api_does_not_count_for_stable_spread(monkeypatch):
    monkeypatch.setattr(topo,"get_settings",lambda:settings())
    rows=healthy_rows()
    rows[1]["deployment_slot"]="candidate"
    monkeypatch.setattr(topo,"deployment_safety_snapshot",lambda touch_api=False:snapshot(rows))
    out=topo.multi_host_topology_snapshot()
    assert out["api_failure_domain_count"] == 1 and out["status"] == "DEGRADED"


def test_unlabeled_active_component_degrades_claim(monkeypatch):
    monkeypatch.setattr(topo,"get_settings",lambda:settings())
    rows=healthy_rows(); rows.append(row("worker","cpu@c","host-c","c")); rows[-1]["topology_failure_domain"]=""
    monkeypatch.setattr(topo,"deployment_safety_snapshot",lambda touch_api=False:snapshot(rows))
    out=topo.multi_host_topology_snapshot()
    assert out["unlabeled_active_components"] == 1 and out["topology_ready"] is False


def test_same_node_id_in_two_domains_is_unsafe(monkeypatch):
    monkeypatch.setattr(topo,"get_settings",lambda:settings())
    rows=healthy_rows(); rows.append(row("api","api@clone","host-c","a"))
    monkeypatch.setattr(topo,"deployment_safety_snapshot",lambda touch_api=False:snapshot(rows))
    out=topo.multi_host_topology_snapshot()
    assert out["status"] == "UNSAFE" and out["node_identity_conflicts"]["a"] == ["host-a","host-c"]


def test_worker_role_gap_is_explicit(monkeypatch):
    monkeypatch.setattr(topo,"get_settings",lambda:settings())
    rows=[r for r in healthy_rows() if not (r["node"].startswith("io@") and r["topology_failure_domain"]=="host-b")]
    monkeypatch.setattr(topo,"deployment_safety_snapshot",lambda touch_api=False:snapshot(rows))
    assert topo.multi_host_topology_snapshot()["worker_failure_domain_gaps"]["io"] == 1


def test_registry_outage_never_claims_topology(monkeypatch):
    monkeypatch.setattr(topo,"get_settings",lambda:settings())
    monkeypatch.setattr(topo,"deployment_safety_snapshot",lambda touch_api=False:snapshot([],"unavailable"))
    out=topo.multi_host_topology_snapshot()
    assert out["status"] == "UNKNOWN" and out["policy"]["registry_is_ephemeral"] is True


def test_disabled_base_topology_not_misrepresented(monkeypatch):
    monkeypatch.setattr(topo,"get_settings",lambda:settings(multi_host_topology_enabled=False))
    monkeypatch.setattr(topo,"deployment_safety_snapshot",lambda touch_api=False:snapshot([]))
    assert topo.multi_host_topology_snapshot()["status"] == "DISABLED"


def test_lb_health_contract_is_sanitized(monkeypatch):
    import app.api.health_routes as hr
    monkeypatch.setattr(hr,"readiness_snapshot",lambda:{"status":"ready","checks":[{"secret":"x"}]})
    r=hr.health_load_balancer()
    body=json.loads(r.body)
    assert r.status_code == 200
    assert set(body) == {"contract","status","traffic_eligible","version","schema_version"}
    assert body["contract"] == "mgc-external-lb-v1"


def test_external_lb_reference_never_replays_requests():
    src=Path("ops/external-lb/haproxy.cfg.example").read_text()
    active="\n".join(x for x in src.splitlines() if not x.lstrip().startswith("#"))
    assert "retries 0" in active and "redispatch" not in active and "retry-on" not in active
    assert "option httpchk GET /api/v1/health/lb" in src


def test_multihost_overlay_requires_explicit_placement_and_authority():
    src=Path("docker-compose.multihost.yml").read_text()
    for text in ("MGC_NODE_ID:?","MGC_FAILURE_DOMAIN:?","MGC_NODE_BIND_IP:?","DATABASE_URL:?","REDIS_URL:?"):
        assert text in src
    assert 'DATABASE_HA_ENABLED: "true"' in src and 'EVIDENCE_HA_ENABLED: "true"' in src
    assert "0.0.0.0" not in src


def test_reference_inventory_passes_30_profile():
    cmd=[sys.executable,"scripts/topology_certify.py","--inventory","ops/multihost/topology.inventory.example.json","--profile","30","--json"]
    r=subprocess.run(cmd,check=True,capture_output=True,text=True)
    out=json.loads(r.stdout)
    assert out["status"] == "PASS" and out["performance_certified"] is False and out["production_authorized"] is False


def test_100_profile_requires_three_api_failure_domains(tmp_path):
    inv=json.loads(Path("ops/multihost/topology.inventory.example.json").read_text())
    inv["profile"]="100"; p=tmp_path/"inv.json"; p.write_text(json.dumps(inv))
    r=subprocess.run([sys.executable,"scripts/topology_certify.py","--inventory",str(p),"--profile","100"],capture_output=True,text=True)
    assert r.returncode == 2 and "FAIL: api_anti_affinity" in r.stdout
