from __future__ import annotations

import json

from app.core.runtime_contract import APP_VERSION, SCHEMA_VERSION
from app.core.target_host_assurance import EVIDENCE_SCHEMA, build_report, evaluate_host_evidence, validate_integrity


def evidence(node="a", profile="30"):
    return {
        "schema": EVIDENCE_SCHEMA, "release": APP_VERSION, "schema_version": SCHEMA_VERSION,
        "profile": profile, "node_id": node,
        "system": {"os":"Linux","architecture":"x86_64","cpu_cores":8,"memory_gib":16},
        "storage": {"free_gib":120,"used_ratio":0.5,"rw_fsync_passed":True},
        "resource_limits": {"nofile_soft":8192},
        "container_runtime": {"docker_cli":True,"daemon_reachable":True,"server_version":"27.5.1","compose_version":"2.32.0"},
        "time_sync": {"synchronized":True},
    }


def topology(*nodes, profile="30"):
    return {"schema":"mgc-multihost-topology-v1","profile":profile,"nodes":[{"node_id":n} for n in nodes]}


def test_runtime_contract_6329_no_schema_migration():
    assert APP_VERSION == "6.3.34"
    assert SCHEMA_VERSION == "6.3.13"


def test_host_baseline_passes():
    out = evaluate_host_evidence(evidence(), profile="30")
    assert out["decision"] == "PASS"
    assert out["failed_checks"] == [] and out["missing_checks"] == []


def test_old_docker_and_unsynced_clock_fail_closed():
    doc = evidence()
    doc["container_runtime"]["server_version"] = "20.10.24"
    doc["time_sync"]["synchronized"] = False
    out = evaluate_host_evidence(doc, profile="30")
    assert out["decision"] == "FAIL"
    assert {"DOCKER_VERSION", "TIME_SYNCHRONIZED"}.issubset(set(out["failed_checks"]))


def test_topology_requires_evidence_for_every_node():
    report = build_report(profile="30", topology=topology("a", "b"), evidence_documents=[evidence("a")])
    assert report["decision"] == "FAIL"
    assert report["missing_nodes"] == ["b"]


def test_report_integrity_detects_tamper():
    report = build_report(profile="30", topology=topology("a"), evidence_documents=[evidence("a")])
    assert report["decision"] == "PASS"
    assert validate_integrity(report)[0] is True
    tampered = json.loads(json.dumps(report)); tampered["decision"] = "FAIL"
    assert validate_integrity(tampered)[0] is False


def test_duplicate_and_extra_nodes_fail_closed():
    report = build_report(profile="30", topology=topology("a"), evidence_documents=[evidence("a"), evidence("a")])
    assert report["decision"] == "FAIL" and report["duplicate_node_ids"] == ["a"]
    extra = build_report(profile="30", topology=topology("a"), evidence_documents=[evidence("a"), evidence("b")])
    assert extra["decision"] == "FAIL" and extra["extra_nodes"] == ["b"]
