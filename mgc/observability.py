from __future__ import annotations

from collections.abc import Mapping
from typing import Any


def render_prometheus_metrics(
    *,
    http_requests: Mapping[tuple[str, str, int], int],
    http_latency: Mapping[tuple[str, str], float],
    reliability_runtime: Mapping[str, Any],
    tts_runtime: Mapping[str, Any],
    db_gauges: Mapping[str, Any] | None,
    db_queries: Mapping[str, Any],
    db_pool: Mapping[str, Any],
    recovery_evidence: Mapping[str, Any],
    slo: Mapping[str, Any],
    recovery: Mapping[str, Any],
    rpo_target_minutes: int,
    rto_target_minutes: int,
    tts_circuit_open: bool,
    tts_cache_writable: bool,
) -> str:
    """Render the stable MGC Prometheus text contract from precomputed snapshots."""
    lines = [
        "# HELP mgc_http_requests_total HTTP requests",
        "# TYPE mgc_http_requests_total counter",
    ]
    for (method, path, status), value in sorted(http_requests.items()):
        lines.append(
            f'mgc_http_requests_total{{method="{method}",path="{path}",status="{status}"}} {value}'
        )
    lines += [
        "# HELP mgc_http_request_duration_seconds_sum HTTP request duration sum",
        "# TYPE mgc_http_request_duration_seconds_sum counter",
    ]
    for (method, path), value in sorted(http_latency.items()):
        lines.append(
            f'mgc_http_request_duration_seconds_sum{{method="{method}",path="{path}"}} {value:.6f}'
        )

    lines += [
        "# HELP mgc_database_failures_total Database failures observed since process start",
        "# TYPE mgc_database_failures_total counter",
        f"mgc_database_failures_total {reliability_runtime.get('database_failures_total', 0)}",
        "# HELP mgc_http_5xx_runtime_total HTTP 5xx responses observed since process start",
        "# TYPE mgc_http_5xx_runtime_total counter",
        f"mgc_http_5xx_runtime_total {reliability_runtime.get('http_5xx_total', 0)}",
    ]

    if db_gauges is None:
        lines += [
            "# HELP mgc_database_metrics_available Whether DB-backed metrics could be collected",
            "# TYPE mgc_database_metrics_available gauge",
            "mgc_database_metrics_available 0",
        ]
    else:
        lines += [
            "# HELP mgc_operational_events_24h Operational events recorded in last 24 hours",
            "# TYPE mgc_operational_events_24h gauge",
            f"mgc_operational_events_24h {db_gauges['operational_events_24h']}",
            "# HELP mgc_operational_errors_24h Operational error events recorded in last 24 hours",
            "# TYPE mgc_operational_errors_24h gauge",
            f"mgc_operational_errors_24h {db_gauges['operational_errors_24h']}",
            "# HELP mgc_expired_sessions_pending_cleanup Expired sessions awaiting maintenance cleanup",
            "# TYPE mgc_expired_sessions_pending_cleanup gauge",
            f"mgc_expired_sessions_pending_cleanup {db_gauges['expired_sessions']}",
            "# HELP mgc_pilot_alerts_open Active pilot operations alerts",
            "# TYPE mgc_pilot_alerts_open gauge",
            f"mgc_pilot_alerts_open {db_gauges['open_alerts']}",
            "# HELP mgc_srs_cards_due Adaptive SRS cards currently due across the pilot",
            "# TYPE mgc_srs_cards_due gauge",
            f"mgc_srs_cards_due {db_gauges['srs_due']}",
            "# HELP mgc_question_attempts_total Learning question attempts recorded",
            "# TYPE mgc_question_attempts_total gauge",
            f"mgc_question_attempts_total {db_gauges['question_attempts_total']}",
            "# HELP mgc_database_metrics_available Whether DB-backed metrics could be collected",
            "# TYPE mgc_database_metrics_available gauge",
            "mgc_database_metrics_available 1",
        ]

    backup_age = recovery_evidence["backup"].get("age_minutes")
    restore_age = recovery_evidence["restore_rehearsal"].get("age_days")
    lines += [
        "# HELP mgc_db_query_p95_ms Database query p95 latency in the in-process telemetry window",
        "# TYPE mgc_db_query_p95_ms gauge",
        f"mgc_db_query_p95_ms {db_queries['p95_ms']}",
        "# HELP mgc_db_slow_queries_window Slow queries in the current telemetry window",
        "# TYPE mgc_db_slow_queries_window gauge",
        f"mgc_db_slow_queries_window {db_queries['slow_queries']}",
        "# HELP mgc_db_slow_queries_total Slow queries since process start",
        "# TYPE mgc_db_slow_queries_total counter",
        f"mgc_db_slow_queries_total {db_queries['lifetime_slow_queries']}",
        "# HELP mgc_db_pool_checked_out Checked-out PostgreSQL pool connections",
        "# TYPE mgc_db_pool_checked_out gauge",
        f"mgc_db_pool_checked_out {float(db_pool.get('checked_out') or 0)}",
        "# HELP mgc_db_pool_capacity Configured PostgreSQL pool plus overflow capacity",
        "# TYPE mgc_db_pool_capacity gauge",
        f"mgc_db_pool_capacity {float(db_pool.get('capacity') or 0)}",
        "# HELP mgc_db_pool_saturation_percent PostgreSQL connection-pool saturation",
        "# TYPE mgc_db_pool_saturation_percent gauge",
        f"mgc_db_pool_saturation_percent {float(db_pool.get('saturation_percent') or 0)}",
        "# HELP mgc_recovery_backup_evidence_available Whether a backup artifact is visible to the app",
        "# TYPE mgc_recovery_backup_evidence_available gauge",
        f"mgc_recovery_backup_evidence_available {1 if backup_age is not None else 0}",
        "# HELP mgc_recovery_backup_age_minutes Age of newest observed backup artifact",
        "# TYPE mgc_recovery_backup_age_minutes gauge",
        f"mgc_recovery_backup_age_minutes {float(backup_age) if backup_age is not None else -1}",
        "# HELP mgc_recovery_restore_evidence_available Whether restore rehearsal evidence is visible to the app",
        "# TYPE mgc_recovery_restore_evidence_available gauge",
        f"mgc_recovery_restore_evidence_available {1 if restore_age is not None else 0}",
        "# HELP mgc_recovery_restore_evidence_age_days Age of newest restore rehearsal evidence",
        "# TYPE mgc_recovery_restore_evidence_age_days gauge",
        f"mgc_recovery_restore_evidence_age_days {float(restore_age) if restore_age is not None else -1}",
        "# HELP mgc_recovery_rpo_target_minutes Configured pilot RPO target",
        "# TYPE mgc_recovery_rpo_target_minutes gauge",
        f"mgc_recovery_rpo_target_minutes {rpo_target_minutes}",
        "# HELP mgc_recovery_rto_target_minutes Configured pilot RTO target",
        "# TYPE mgc_recovery_rto_target_minutes gauge",
        f"mgc_recovery_rto_target_minutes {rto_target_minutes}",
    ]

    state_map = {"healthy": 0, "degraded": 1, "recovering": 2, "unavailable": 3}
    lines += [
        "# HELP mgc_slo_availability_percent Rolling pilot availability SLI",
        "# TYPE mgc_slo_availability_percent gauge",
        f"mgc_slo_availability_percent {slo['availability_percent']}",
        "# HELP mgc_slo_error_rate_percent Rolling pilot HTTP 5xx rate",
        "# TYPE mgc_slo_error_rate_percent gauge",
        f"mgc_slo_error_rate_percent {slo['error_rate_percent']}",
        "# HELP mgc_slo_p95_ms Rolling pilot HTTP p95 latency in milliseconds",
        "# TYPE mgc_slo_p95_ms gauge",
        f"mgc_slo_p95_ms {slo['p95_ms']}",
        "# HELP mgc_slo_samples Rolling pilot SLO sample count",
        "# TYPE mgc_slo_samples gauge",
        f"mgc_slo_samples {slo['samples']}",
        "# HELP mgc_recovery_state Pilot recovery state (0 healthy, 1 degraded, 2 recovering, 3 unavailable)",
        "# TYPE mgc_recovery_state gauge",
        f"mgc_recovery_state {state_map.get(recovery.get('state'), 3)}",
        "# HELP mgc_tts_success_total Successful server-side TTS syntheses",
        "# TYPE mgc_tts_success_total counter",
        f"mgc_tts_success_total {tts_runtime['success_total']}",
        "# HELP mgc_tts_failure_total Failed server-side TTS syntheses",
        "# TYPE mgc_tts_failure_total counter",
        f"mgc_tts_failure_total {tts_runtime['failure_total']}",
        "# HELP mgc_tts_disk_cache_hits_total TTS disk cache hits",
        "# TYPE mgc_tts_disk_cache_hits_total counter",
        f"mgc_tts_disk_cache_hits_total {tts_runtime['disk_cache_hits']}",
        "# HELP mgc_tts_circuit_open TTS circuit breaker state",
        "# TYPE mgc_tts_circuit_open gauge",
        f"mgc_tts_circuit_open {1 if tts_circuit_open else 0}",
        "# HELP mgc_tts_cache_writable TTS cache writability",
        "# TYPE mgc_tts_cache_writable gauge",
        f"mgc_tts_cache_writable {1 if tts_cache_writable else 0}",
    ]
    return "\n".join(lines) + "\n"


__all__ = ["render_prometheus_metrics"]
