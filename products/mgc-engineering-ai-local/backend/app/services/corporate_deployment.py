from __future__ import annotations

from app.core.runtime_contract import APP_VERSION

import math
from typing import Any

DEPLOYMENT_PROFILES = {
    "pilot_15": {
        "intended_users": "up to 15 concurrent pilot users",
        "topology": "2-node recommended (application/data + model) or 3-node split",
        "app": {"vcpu": 16, "ram_gb": 64},
        "data": {"vcpu": 12, "ram_gb": 48},
        "cpu_model": {"vcpu": 16, "ram_gb": 64},
        "gpu_model": {"vcpu": 8, "ram_gb": 32, "gpu": "1 approved GPU, >=24 GB VRAM recommended"},
        "base_storage_gb": 750,
    },
    "pilot_30": {
        "intended_users": "16-30 concurrent pilot users",
        "topology": "3-node recommended (application + data + model)",
        "app": {"vcpu": 16, "ram_gb": 64},
        "data": {"vcpu": 16, "ram_gb": 64},
        "cpu_model": {"vcpu": 24, "ram_gb": 96},
        "gpu_model": {"vcpu": 12, "ram_gb": 48, "gpu": "1 approved GPU, >=24-48 GB VRAM recommended"},
        "base_storage_gb": 1500,
    },
    "enterprise_reference": {
        "intended_users": "more than 30 users; benchmark-driven sizing required",
        "topology": "split application/data/model nodes; HA is environment-specific",
        "app": {"vcpu": 24, "ram_gb": 96},
        "data": {"vcpu": 24, "ram_gb": 128},
        "cpu_model": {"vcpu": 32, "ram_gb": 128},
        "gpu_model": {"vcpu": 16, "ram_gb": 64, "gpu": "approved GPU capacity determined by target-host benchmark"},
        "base_storage_gb": 3000,
    },
}

NETWORK_PORTS = [
    {"from": "corporate users", "to": "enterprise-edge", "port": 443, "protocol": "TCP/TLS", "scope": "inbound", "required": True, "purpose": "Browser/SSO access"},
    {"from": "approved PLM/ERP/MES/QMS clients", "to": "enterprise-edge", "port": 9443, "protocol": "TCP/mTLS", "scope": "inbound", "required": False, "purpose": "Machine webhook channel"},
    {"from": "enterprise-edge/auth-proxy", "to": "gateway/api", "port": 8080, "protocol": "TCP", "scope": "internal-only", "required": True, "purpose": "Internal application routing"},
    {"from": "api/worker/beat", "to": "PostgreSQL", "port": 5432, "protocol": "TCP", "scope": "internal-only", "required": True, "purpose": "Authoritative MGC state"},
    {"from": "api/worker/beat", "to": "Qdrant", "port": 6333, "protocol": "TCP", "scope": "internal-only", "required": True, "purpose": "Vector search"},
    {"from": "api/worker/beat", "to": "Redis", "port": 6379, "protocol": "TCP", "scope": "internal-only", "required": True, "purpose": "Queue/broker"},
    {"from": "api/worker", "to": "Neo4j", "port": 7687, "protocol": "TCP", "scope": "internal-only", "required": False, "purpose": "Optional graph projection"},
    {"from": "api/worker", "to": "MinIO", "port": 9000, "protocol": "TCP", "scope": "internal-only", "required": False, "purpose": "Optional object storage"},
    {"from": "api/worker", "to": "local model server", "port": 8000, "protocol": "TCP", "scope": "internal-only", "required": True, "purpose": "Local LLM/VLM inference"},
    {"from": "auth-proxy/api", "to": "corporate IdP", "port": 443, "protocol": "TCP/TLS", "scope": "outbound/internal-corporate", "required": True, "purpose": "OIDC discovery/JWKS/token validation"},
    {"from": "integration workers", "to": "PLM/PDM/ERP/MES/QMS gateways", "port": 443, "protocol": "TCP/TLS", "scope": "outbound/internal-corporate", "required": False, "purpose": "Read-only enterprise integrations"},
    {"from": "MGC hosts", "to": "corporate DNS", "port": 53, "protocol": "UDP/TCP", "scope": "infrastructure", "required": True, "purpose": "Name resolution"},
    {"from": "MGC hosts", "to": "corporate NTP", "port": 123, "protocol": "UDP", "scope": "infrastructure", "required": True, "purpose": "Clock synchronization for OIDC/audit"},
]

MANDATORY_LAUNCH_GATES = [
    "target_host_capacity_profile_accepted",
    "target_host_performance_profile_pass",
    "docker_runtime_acceptance_pass",
    "cve_scan_pass",
    "dependency_lock_pass",
    "oidc_negative_tests_pass",
    "tls_mtls_negative_tests_pass",
    "runtime_db_least_privilege_pass",
    "backup_restore_drill_pass",
    "network_firewall_approved",
    "dns_ntp_storage_ready",
    "integration_reconciliation_ready",
    "enterprise_security_approval",
    "data_owner_approval",
    "pilot_owner_named",
    "support_rota_ready",
    "operations_rehearsal_pass",
    "monitoring_alerting_ready",
]

RECOMMENDED_LAUNCH_GATES = [
    "pilot_training_material_ready",
    "support_escalation_contacts_verified",
    "change_window_booked",
    "rollback_window_booked",
]


def _round_storage(value: float) -> int:
    return int(math.ceil(max(value, 100.0) / 100.0) * 100)


def select_profile(user_count: int) -> str:
    if user_count <= 15:
        return "pilot_15"
    if user_count <= 30:
        return "pilot_30"
    return "enterprise_reference"


def calculate_deployment_plan(*, user_count: int, documents: int = 0, parts: int = 0,
                              vehicle_count: int = 0, quality_observations: int = 0,
                              cad_storage_gb: float = 0.0, inference_mode: str = "cpu") -> dict[str, Any]:
    if user_count < 1:
        raise ValueError("user_count must be >= 1")
    if inference_mode not in {"cpu", "gpu"}:
        raise ValueError("inference_mode must be cpu or gpu")
    profile_name = select_profile(user_count)
    profile = DEPLOYMENT_PROFILES[profile_name]
    estimated_working = (
        float(profile["base_storage_gb"])
        + max(cad_storage_gb, 0.0) * 2.5
        + max(documents, 0) * 0.015
        + max(parts, 0) * 0.002
        + max(vehicle_count, 0) * 0.01
        + max(quality_observations, 0) * 0.0005
    )
    working_storage_gb = _round_storage(estimated_working)
    backup_target_gb = _round_storage(working_storage_gb * 1.5)
    model = profile["cpu_model"] if inference_mode == "cpu" else profile["gpu_model"]
    warnings = [
        "Reference sizing is a conservative starting point, not a throughput guarantee.",
        "Target-host v6.0.4 performance certification is mandatory before pilot launch.",
        "Storage estimate includes working/index/headroom assumptions and must be reconciled with retention policy.",
    ]
    if user_count > 30:
        warnings.append("More than 30 users requires benchmark-driven enterprise sizing; this reference profile is not certification.")
    return {
        "release": APP_VERSION,
        "profile": profile_name,
        "intended_users": profile["intended_users"],
        "topology": profile["topology"],
        "requested": {
            "user_count": user_count, "documents": documents, "parts": parts,
            "vehicle_count": vehicle_count, "quality_observations": quality_observations,
            "cad_storage_gb": cad_storage_gb, "inference_mode": inference_mode,
        },
        "nodes": {"application": profile["app"], "data": profile["data"], "model": model},
        "storage": {"working_storage_gb": working_storage_gb, "protected_backup_target_gb": backup_target_gb},
        "network_exposure_rule": "Only enterprise edge ports are host-exposed; database/vector/queue/model ports stay internal.",
        "certification_required": True,
        "deployment_authorized": False,
        "warnings": warnings,
    }


def evaluate_launch_readiness(evidence: dict[str, Any] | None) -> dict[str, Any]:
    evidence = dict(evidence or {})
    missing = [name for name in MANDATORY_LAUNCH_GATES if evidence.get(name) is not True]
    recommended_missing = [name for name in RECOMMENDED_LAUNCH_GATES if evidence.get(name) is not True]
    if missing:
        decision = "NOT_READY"
    elif recommended_missing:
        decision = "CONDITIONAL_READY"
    else:
        decision = "READY_TO_LAUNCH_CONTROLLED_PILOT"
    return {
        "release": APP_VERSION,
        "decision": decision,
        "mandatory_gate_coverage": round((len(MANDATORY_LAUNCH_GATES)-len(missing))/len(MANDATORY_LAUNCH_GATES), 4),
        "missing_mandatory_gates": missing,
        "missing_recommended_gates": recommended_missing,
        "human_change_approval_required": True,
        "deployment_authorized": False,
        "production_go_decision": False,
        "note": "This gate authorizes neither production nor final UAT approval; it only assesses readiness to begin a controlled pilot.",
    }


def launch_checklist() -> dict[str, Any]:
    return {
        "mandatory": MANDATORY_LAUNCH_GATES,
        "recommended": RECOMMENDED_LAUNCH_GATES,
        "roles": ["IT infrastructure owner", "Information Security", "Engineering IT", "R&D pilot owner", "Manufacturing representative", "Quality representative", "Data owners", "Support/SRE"],
        "pilot_population": "15-30 engineers recommended for the controlled pilot",
        "deployment_authorized": False,
    }
