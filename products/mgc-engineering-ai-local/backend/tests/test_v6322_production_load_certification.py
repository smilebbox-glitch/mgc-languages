from __future__ import annotations

from app.core import load_certification as lc
from app.core.runtime_contract import APP_VERSION, SCHEMA_VERSION


def records(*, n=1000, latency=100.0, error_every=0):
    ops=list(lc.REQUIRED_WORKLOAD_OPERATIONS)
    out=[]
    for i in range(n):
        err=bool(error_every and i % error_every == 0)
        out.append({"operation":ops[i%len(ops)],"ok":not err,"status":500 if err else 200,"latency_ms":latency + (i%7)})
    return out


def saturation(pool=.5, age=1.0, dlq=0, orphaned=0, expired=0):
    return lc.summarize_saturation([{
        "production_certification":{"database_pool":{"saturation_ratio":pool}},
        "queue":{"oldest_job_age_seconds":age,"queues":[{"queue":"interactive","depth":3}]},
        "workload":{"dead_letter_jobs":dlq,"orphaned_jobs":orphaned,"expired_running_leases":expired},
    }])


def evidence(profile="15", *, signed=True, latency=100.0):
    p=lc.LOAD_PROFILES[profile]
    ev={
        "schema":lc.LOAD_EVIDENCE_SCHEMA,
        "release":"6.3.24",
        "schema_version":"6.3.13",
        "profile":profile,
        "named_users":p.named_users,
        "concurrency":p.concurrency,
        "workload":lc.workload_contract(),
        "summary":lc.summarize_request_records(records(n=p.min_requests,latency=latency),wall_seconds=10,profile=profile),
        "saturation":saturation(),
        "governance":{"live_target_measurement":True,"synthetic":False,"engineering_state_mutation_allowed":False,"non_idempotent_business_write_replay_allowed":False},
    }
    ev=lc.attach_integrity(ev,detached_signature_verified=signed,signature_algorithm="test")
    return ev


def test_release_marker_and_schema_stability():
    assert APP_VERSION == "6.3.34"
    assert SCHEMA_VERSION == "6.3.13"


def test_profiles_run_full_controlled_concurrency_15_30_100():
    assert {k:v.concurrency for k,v in lc.LOAD_PROFILES.items()} == {"15":15,"30":30,"100":100}


def test_default_workload_covers_engineering_reads_and_rag():
    codes={x.code for x in lc.DEFAULT_WORKLOAD}
    assert {"object_360","bom_versions","work_instructions","digital_thread","rag_search","rag_ask"}.issubset(codes)
    assert sum(x.weight for x in lc.DEFAULT_WORKLOAD) == 100


def test_latency_summary_reports_p50_p95_p99_and_error_budget():
    r=lc.summarize_request_records(records(n=1000),wall_seconds=10,profile="15")
    assert r["p50_ms"] is not None and r["p95_ms"] is not None and r["p99_ms"] is not None
    assert r["error_budget"]["status"] == "PASS"
    assert r["requests_per_second"] == 100.0


def test_error_budget_burn_is_no_go():
    ev=evidence(); ev["summary"]=lc.summarize_request_records(records(n=1000,error_every=10),wall_seconds=10,profile="15"); ev=lc.attach_integrity(ev,detached_signature_verified=True)
    r=lc.load_decision(ev,profile="15")
    assert r["decision"] == "NO_GO"
    assert "LOAD_ERROR_RATE" in r["failed_checks"] or "LOAD_ERROR_BUDGET_BURN" in r["failed_checks"]


def test_unsigned_evidence_is_conditional_not_go():
    r=lc.load_decision(evidence(signed=False),profile="15")
    assert r["decision"] == "CONDITIONAL"
    assert "LOAD_DETACHED_SIGNATURE" in r["missing_checks"]


def test_signed_complete_evidence_is_go():
    r=lc.load_decision(evidence(),profile="15")
    assert r["decision"] == "GO"


def test_tamper_after_digest_is_fail_closed():
    ev=evidence(); ev["summary"]["p95_ms"]=1.0
    r=lc.load_decision(ev,profile="15")
    assert r["decision"] == "NO_GO"
    assert "LOAD_CANONICAL_DIGEST" in r["failed_checks"]


def test_missing_rag_coverage_fails_certification():
    ev=evidence(); ev["summary"]["operations"].pop("rag_ask"); ev=lc.attach_integrity(ev,detached_signature_verified=True)
    r=lc.load_decision(ev,profile="15")
    assert r["decision"] == "CONDITIONAL"
    assert "LOAD_COVERAGE_RAG_ASK" in r["missing_checks"]


def test_saturation_snapshot_captures_pool_queue_and_managed_job_safety():
    s=saturation(pool=.77,age=12,dlq=1,orphaned=2,expired=3)
    assert s["db_pool"]["max_saturation_ratio"] == .77
    assert s["queue"]["max_depth"] == 3 and s["queue"]["max_oldest_job_age_seconds"] == 12
    assert s["workload"] == {"max_dead_letter_jobs":1,"max_orphaned_jobs":2,"max_expired_running_leases":3}


def test_db_pool_or_dlq_saturation_is_no_go():
    ev=evidence(); ev["saturation"]=saturation(pool=.99,dlq=1); ev=lc.attach_integrity(ev,detached_signature_verified=True)
    r=lc.load_decision(ev,profile="15")
    assert r["decision"] == "NO_GO"
    assert {"LOAD_DB_POOL_SATURATION","LOAD_DLQ"}.issubset(set(r["failed_checks"]))


def test_integrity_ignores_signature_metadata_but_not_payload():
    ev=evidence(); digest=ev["integrity"]["canonical_sha256"]
    ev["integrity"]["detached_signature_verified"]=False
    ok, claimed, actual=lc.validate_integrity(ev)
    assert ok is True and claimed == actual == digest


def test_workload_contract_forbids_business_write_replay():
    c=lc.workload_contract()
    assert c["governance"]["engineering_state_mutation_allowed"] is False
    assert c["governance"]["non_idempotent_business_write_replay_allowed"] is False
