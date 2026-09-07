from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.core import production_certification as pc
from app.core import load_certification as lc
from app.core.runtime_contract import APP_VERSION, SCHEMA_VERSION


def topology(profile="30", domains=2):
    nodes=[]
    for i in range(domains):
        nodes.append({"node_id":f"n{i}","failure_domain":f"fd{i}","roles":["api","interactive","cpu","io"]})
    return {"schema":"mgc-multihost-topology-v1","profile":profile,"nodes":nodes}



def load_evidence(profile="30"):
    p=lc.LOAD_PROFILES[profile]
    ops=list(lc.REQUIRED_WORKLOAD_OPERATIONS)
    records=[{"operation":ops[i%len(ops)],"ok":True,"status":200,"latency_ms":100+(i%5)} for i in range(p.min_requests)]
    ev={
        "schema":lc.LOAD_EVIDENCE_SCHEMA,"release":"6.3.24","schema_version":"6.3.13","profile":profile,
        "named_users":p.named_users,"concurrency":p.concurrency,"workload":lc.workload_contract(),
        "summary":lc.summarize_request_records(records,wall_seconds=10,profile=profile),
        "saturation":lc.summarize_saturation([{"production_certification":{"database_pool":{"saturation_ratio":.5}},"queue":{"oldest_job_age_seconds":1,"queues":[{"queue":"interactive","depth":0}]},"workload":{"dead_letter_jobs":0,"orphaned_jobs":0,"expired_running_leases":0}}]),
        "governance":{"live_target_measurement":True,"synthetic":False,"engineering_state_mutation_allowed":False,"non_idempotent_business_write_replay_allowed":False},
    }
    return lc.attach_integrity(ev,detached_signature_verified=True,signature_algorithm="test")

def evidence(profile="30"):
    p=pc.PROFILES[profile]
    return {
        "schema":pc.EVIDENCE_SCHEMA,
        "load_certification":load_evidence(profile),
        "named_users":p.named_users,
        "http":{"requests":p.min_http_requests,"p95_ms":p.api_p95_ms-1,"error_rate":p.error_rate_max/2},
        "dependencies":{"availability":min(1.0,p.dependency_availability_target+0.0005)},
        "database_pool":{"max_saturation_ratio":p.pool_hard_ratio-0.05},
        "external_load_balancer":{"successful_probes":20,"non_idempotent_replay_detected":False},
        "failover":{"host_loss_passed":True,"authoritative_failover_passed":True,"evidence_integrity_passed":True,"rto_seconds":p.rto_seconds,"rpo_seconds":p.rpo_seconds},
    }


def test_release_marker_and_schema_stability():
    assert APP_VERSION == "6.3.34"
    assert SCHEMA_VERSION == "6.3.13"


def test_profiles_cover_15_30_100():
    assert set(pc.PROFILES) == {"15","30","100"}
    assert pc.PROFILES["100"].min_failure_domains == 3


def test_complete_target_host_evidence_is_technical_go_not_authorization():
    r=pc.evaluate_target_host_evidence(profile="30",topology=topology(),evidence=evidence())
    assert r["decision"] == "GO"
    assert r["production_authorized"] is False
    assert r["human_approval_required"] is True


def test_missing_live_evidence_is_conditional_not_pass():
    ev=evidence(); del ev["http"]["p95_ms"]
    r=pc.evaluate_target_host_evidence(profile="30",topology=topology(),evidence=ev)
    assert r["decision"] == "CONDITIONAL"
    assert "HTTP_P95" in r["missing_checks"]


def test_slo_violation_is_no_go():
    ev=evidence(); ev["http"]["error_rate"]=0.5
    r=pc.evaluate_target_host_evidence(profile="30",topology=topology(),evidence=ev)
    assert r["decision"] == "NO_GO"
    assert "HTTP_ERROR_RATE" in r["failed_checks"]


def test_100_profile_requires_three_api_domains():
    r=pc.evaluate_target_host_evidence(profile="100",topology=topology("100",2),evidence=evidence("100"))
    assert r["decision"] == "NO_GO"
    assert "FAILURE_DOMAINS" in r["failed_checks"] or "API_FAILURE_DOMAINS" in r["failed_checks"]


def test_rto_rpo_are_enforced():
    ev=evidence(); ev["failover"]["rto_seconds"]=9999; ev["failover"]["rpo_seconds"]=9999
    r=pc.evaluate_target_host_evidence(profile="30",topology=topology(),evidence=ev)
    assert r["decision"] == "NO_GO"
    assert {"RTO","RPO"}.issubset(set(r["failed_checks"]))


def test_lb_non_idempotent_replay_is_no_go():
    ev=evidence(); ev["external_load_balancer"]["non_idempotent_replay_detected"]=True
    r=pc.evaluate_target_host_evidence(profile="30",topology=topology(),evidence=ev)
    assert "LB_NON_IDEMPOTENT_REPLAY" in r["failed_checks"]


def test_profile_aliases_are_supported():
    assert pc.normalize_profile("pilot_15") == "15"
    assert pc.normalize_profile("enterprise_100") == "100"
    with pytest.raises(ValueError): pc.normalize_profile("500")


def test_pool_capacity_uses_effective_capacity(monkeypatch):
    monkeypatch.setattr(pc,"_pool_numbers",lambda:(10,5,1,10))
    monkeypatch.setattr(pc,"get_settings",lambda:SimpleNamespace(production_certification_profile="30",db_max_overflow=10,db_pool_saturation_warn_ratio=.8,db_pool_saturation_hard_ratio=.95))
    r=pc.db_pool_capacity_snapshot()
    assert r["effective_capacity"] == 20
    assert r["saturation_ratio"] == .25
    assert r["status"] == "OK"


def test_pool_critical_closes_mutating_admission(monkeypatch):
    monkeypatch.setattr(pc,"_pool_numbers",lambda:(10,19,9,10))
    monkeypatch.setattr(pc,"get_settings",lambda:SimpleNamespace(production_certification_profile="30",db_max_overflow=10,db_pool_saturation_warn_ratio=.8,db_pool_saturation_hard_ratio=.95))
    r=pc.db_pool_capacity_snapshot()
    assert r["status"] == "CRITICAL"
    assert r["admission_open"] is False


def test_example_evidence_files_are_not_self_authorization():
    import json
    from pathlib import Path
    root=Path(__file__).resolve().parents[2]
    for code in ("15","30","100"):
        ev=json.loads((root/f"ops/certification/evidence.{code}.example.json").read_text())
        assert ev["governance"]["example_only"] is True
        assert ev["governance"]["must_be_replaced_with_target_host_measurements"] is True


def test_deployment_guard_requires_human_confirmation(tmp_path):
    import json, subprocess, sys
    from pathlib import Path
    root=Path(__file__).resolve().parents[2]
    report=pc.evaluate_target_host_evidence(profile="30",topology=topology(),evidence=evidence())
    p=tmp_path/"report.json"; p.write_text(json.dumps(report))
    bad=subprocess.run([sys.executable,str(root/"scripts/production_deployment_guard.py"),"--report",str(p)],capture_output=True,text=True)
    good=subprocess.run([sys.executable,str(root/"scripts/production_deployment_guard.py"),"--report",str(p),"--confirm","APPROVED_CHANGE_WINDOW"],capture_output=True,text=True)
    assert bad.returncode == 2
    assert good.returncode == 0

def test_runtime_dependency_slo_no_data_is_explicit(tmp_path):
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from app.db.models import OperationalHealthSample
    from app.db.session import Base
    eng=create_engine(f"sqlite:///{tmp_path/'slo.db'}")
    Base.metadata.create_all(eng, tables=[OperationalHealthSample.__table__])
    Session=sessionmaker(bind=eng)
    with Session() as db:
        out=pc._runtime_dependency_slo(db, pc.PROFILES["30"])
    assert out["status"] == "NO_DATA" and out["availability"] is None

