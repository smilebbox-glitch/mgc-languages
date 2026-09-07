from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.db import models  # noqa: F401
from app.db.session import Base
from app.db.migrations import ensure_v610_schema
from app.services.corporate_deployment import (
    MANDATORY_LAUNCH_GATES,
    RECOMMENDED_LAUNCH_GATES,
    NETWORK_PORTS,
    calculate_deployment_plan,
    evaluate_launch_readiness,
    select_profile,
)


def test_v610_schema_marker_is_idempotent():
    eng=create_engine("sqlite:///:memory:")
    Base.metadata.create_all(eng)
    ensure_v610_schema(eng); ensure_v610_schema(eng)
    with eng.begin() as c:
        assert c.execute(text("SELECT schema_version FROM mgc_schema_state WHERE id=1")).scalar_one()=="6.1.0"


def test_profile_selection_matches_controlled_pilot_population():
    assert select_profile(15)=="pilot_15"
    assert select_profile(16)=="pilot_30"
    assert select_profile(30)=="pilot_30"
    assert select_profile(31)=="enterprise_reference"


def test_plan_is_conservative_and_never_authorizes_deployment():
    p=calculate_deployment_plan(user_count=30, documents=10000, parts=50000, vehicle_count=100000,
                                quality_observations=1000000, cad_storage_gb=500, inference_mode="cpu")
    assert p["profile"]=="pilot_30"
    assert p["storage"]["working_storage_gb"] >= 1500
    assert p["storage"]["protected_backup_target_gb"] > p["storage"]["working_storage_gb"]
    assert p["certification_required"] is True
    assert p["deployment_authorized"] is False


def test_gpu_plan_keeps_benchmark_requirement():
    p=calculate_deployment_plan(user_count=12, inference_mode="gpu")
    assert "gpu" in p["nodes"]["model"]
    assert p["certification_required"] is True


def test_missing_mandatory_gate_is_not_ready():
    evidence={x: True for x in MANDATORY_LAUNCH_GATES}
    evidence["cve_scan_pass"]=False
    out=evaluate_launch_readiness(evidence)
    assert out["decision"]=="NOT_READY"
    assert "cve_scan_pass" in out["missing_mandatory_gates"]
    assert out["deployment_authorized"] is False


def test_all_mandatory_but_recommended_missing_is_conditional():
    evidence={x: True for x in MANDATORY_LAUNCH_GATES}
    out=evaluate_launch_readiness(evidence)
    assert out["decision"]=="CONDITIONAL_READY"
    assert set(out["missing_recommended_gates"])==set(RECOMMENDED_LAUNCH_GATES)


def test_all_gates_ready_only_launches_controlled_pilot_not_production():
    evidence={x: True for x in MANDATORY_LAUNCH_GATES + RECOMMENDED_LAUNCH_GATES}
    out=evaluate_launch_readiness(evidence)
    assert out["decision"]=="READY_TO_LAUNCH_CONTROLLED_PILOT"
    assert out["production_go_decision"] is False
    assert out["human_change_approval_required"] is True
    assert out["deployment_authorized"] is False


def test_port_matrix_exposes_only_enterprise_edges_inbound():
    inbound=[x for x in NETWORK_PORTS if x["scope"]=="inbound"]
    assert {x["port"] for x in inbound} <= {443,9443}
    for x in NETWORK_PORTS:
        if x["port"] in {5432,6333,6379,7687,9000,8000,8080}:
            assert x["scope"]=="internal-only"
