from app.services.performance_certification import (
    PROFILES, PERFORMANCE_SCHEMA, capacity_envelope, evaluate_http_result,
    evaluate_reconciliation_latency, percentile, summarize_latencies,
)


def test_percentile_is_deterministic_and_interpolated():
    assert percentile([1,2,3,4], 50) == 2.5
    assert percentile([10], 95) == 10
    assert percentile([], 95) is None


def test_latency_summary_and_http_gate():
    summary=summarize_latencies([100,110,120,130,140,150,160,170,180,190],errors=0,total_requests=10)
    assert summary["requests"] == 10 and summary["p95_ms"] > 180
    assert evaluate_http_result(summary,PROFILES["ci"])["status"] == "PASS"
    bad={**summary,"p95_ms":900.0,"error_rate":0.02}
    out=evaluate_http_result(bad,PROFILES["ci"])
    assert out["status"] == "FAIL" and len([x for x in out["checks"] if not x["pass"]]) == 2


def test_reconciliation_gate_has_separate_budget():
    assert evaluate_reconciliation_latency(4999,PROFILES["ci"])["status"] == "PASS"
    assert evaluate_reconciliation_latency(5001,PROFILES["ci"])["status"] == "FAIL"


def test_capacity_envelope_never_claims_live_certification():
    out=capacity_envelope(logical_cpus=4,ram_gib=8,profile="enterprise")
    assert out["schema"] == PERFORMANCE_SCHEMA
    assert out["host_class"] == "developer"
    assert out["recommended_max_concurrent_users_before_live_test"] <= 5
    assert "not a production pilot capacity claim" in out["note"].lower()


def test_profiles_are_explicit_and_monotonic():
    assert set(PROFILES) == {"ci","pilot","enterprise"}
    assert PROFILES["ci"].parts < PROFILES["pilot"].parts < PROFILES["enterprise"].parts
    assert PROFILES["ci"].quality_observations < PROFILES["pilot"].quality_observations < PROFILES["enterprise"].quality_observations
