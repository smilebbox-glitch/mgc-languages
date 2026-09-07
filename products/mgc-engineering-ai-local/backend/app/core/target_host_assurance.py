from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass
from typing import Any

from app.core.runtime_contract import APP_VERSION, SCHEMA_VERSION

EVIDENCE_SCHEMA = "mgc-target-host-assurance-evidence-v1"
REPORT_SCHEMA = "mgc-target-host-assurance-report-v1"


@dataclass(frozen=True)
class HostProfile:
    code: str
    min_cpu_cores: int
    min_memory_gib: float
    min_disk_free_gib: float
    max_disk_used_ratio: float
    min_nofile_soft: int
    min_docker_version: tuple[int, int]
    min_compose_version: tuple[int, int]


# This is a baseline deployment envelope, not a workload/capacity certification.
# Capacity remains governed by the dedicated production/load certification.
PROFILES: dict[str, HostProfile] = {
    "15": HostProfile("15", 4, 8.0, 40.0, 0.90, 4096, (24, 0), (2, 20)),
    "30": HostProfile("30", 4, 8.0, 60.0, 0.90, 4096, (24, 0), (2, 20)),
    "100": HostProfile("100", 8, 16.0, 100.0, 0.85, 8192, (24, 0), (2, 20)),
}


def normalize_profile(value: str | int | None) -> str:
    raw = str(value or "30").strip().lower()
    aliases = {"pilot_15": "15", "pilot_30": "30", "enterprise_100": "100"}
    raw = aliases.get(raw, raw)
    if raw not in PROFILES:
        raise ValueError("Unsupported target-host profile; expected 15, 30 or 100")
    return raw


def profile_contract(value: str | int | None) -> dict[str, Any]:
    out = asdict(PROFILES[normalize_profile(value)])
    out["min_docker_version"] = ".".join(map(str, out["min_docker_version"]))
    out["min_compose_version"] = ".".join(map(str, out["min_compose_version"]))
    return out


def canonical_payload(document: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in document.items() if k != "integrity"}


def canonical_payload_bytes(document: dict[str, Any]) -> bytes:
    return json.dumps(canonical_payload(document), ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def canonical_sha256(document: dict[str, Any]) -> str:
    return hashlib.sha256(canonical_payload_bytes(document)).hexdigest()


def attach_integrity(document: dict[str, Any], *, signature_path_hint: str | None = None) -> dict[str, Any]:
    out = json.loads(json.dumps(document))
    out["integrity"] = {
        "canonical_sha256": canonical_sha256(out),
        "detached_signature_path_hint": signature_path_hint,
    }
    return out


def validate_integrity(document: dict[str, Any]) -> tuple[bool, str | None, str]:
    claimed = (document.get("integrity") or {}).get("canonical_sha256")
    actual = canonical_sha256(document)
    return claimed == actual, claimed, actual


def _version_pair(value: Any) -> tuple[int, int] | None:
    if value is None:
        return None
    match = re.search(r"(\d+)\.(\d+)", str(value))
    if not match:
        return None
    return int(match.group(1)), int(match.group(2))


def _check(code: str, ok: bool | None, actual: Any, expected: Any) -> dict[str, Any]:
    return {
        "code": code,
        "status": "PASS" if ok is True else ("FAIL" if ok is False else "NO_DATA"),
        "actual": actual,
        "expected": expected,
        "required": True,
    }


def evaluate_host_evidence(evidence: dict[str, Any], *, profile: str | int | None) -> dict[str, Any]:
    p = PROFILES[normalize_profile(profile)]
    system = evidence.get("system") or {}
    storage = evidence.get("storage") or {}
    runtime = evidence.get("container_runtime") or {}
    clock = evidence.get("time_sync") or {}
    limits = evidence.get("resource_limits") or {}
    checks: list[dict[str, Any]] = []

    checks.append(_check("EVIDENCE_SCHEMA", evidence.get("schema") == EVIDENCE_SCHEMA, evidence.get("schema"), EVIDENCE_SCHEMA))
    checks.append(_check("RELEASE_MATCH", evidence.get("release") == APP_VERSION, evidence.get("release"), APP_VERSION))
    checks.append(_check("DB_SCHEMA_MATCH", evidence.get("schema_version") == SCHEMA_VERSION, evidence.get("schema_version"), SCHEMA_VERSION))
    checks.append(_check("PROFILE_MATCH", str(evidence.get("profile")) == p.code, evidence.get("profile"), p.code))
    checks.append(_check("NODE_ID", bool(str(evidence.get("node_id") or "").strip()), evidence.get("node_id"), "non-empty"))
    checks.append(_check("LINUX_HOST", str(system.get("os") or "").lower() == "linux", system.get("os"), "Linux"))
    checks.append(_check("SUPPORTED_ARCH", str(system.get("architecture") or "").lower() in {"x86_64", "amd64", "aarch64", "arm64"}, system.get("architecture"), "x86_64/amd64/aarch64/arm64"))

    def numeric(code: str, obj: dict[str, Any], key: str, predicate, expected: Any) -> None:
        raw = obj.get(key)
        if raw is None:
            checks.append(_check(code, None, None, expected)); return
        try:
            val = float(raw)
        except (TypeError, ValueError):
            checks.append(_check(code, False, raw, expected)); return
        checks.append(_check(code, bool(predicate(val)), raw, expected))

    numeric("CPU_CORES", system, "cpu_cores", lambda v: v >= p.min_cpu_cores, f">={p.min_cpu_cores}")
    numeric("MEMORY_GIB", system, "memory_gib", lambda v: v >= p.min_memory_gib, f">={p.min_memory_gib}")
    numeric("DISK_FREE_GIB", storage, "free_gib", lambda v: v >= p.min_disk_free_gib, f">={p.min_disk_free_gib}")
    numeric("DISK_USED_RATIO", storage, "used_ratio", lambda v: v <= p.max_disk_used_ratio, f"<={p.max_disk_used_ratio}")
    checks.append(_check("STORAGE_RW_FSYNC", storage.get("rw_fsync_passed") is True if "rw_fsync_passed" in storage else None, storage.get("rw_fsync_passed"), True))
    numeric("NOFILE_SOFT", limits, "nofile_soft", lambda v: v >= p.min_nofile_soft, f">={p.min_nofile_soft}")

    checks.append(_check("DOCKER_CLI", runtime.get("docker_cli") is True if "docker_cli" in runtime else None, runtime.get("docker_cli"), True))
    checks.append(_check("DOCKER_DAEMON", runtime.get("daemon_reachable") is True if "daemon_reachable" in runtime else None, runtime.get("daemon_reachable"), True))
    docker_version = _version_pair(runtime.get("server_version"))
    checks.append(_check("DOCKER_VERSION", None if docker_version is None else docker_version >= p.min_docker_version, runtime.get("server_version"), f">={p.min_docker_version[0]}.{p.min_docker_version[1]}"))
    compose_version = _version_pair(runtime.get("compose_version"))
    checks.append(_check("COMPOSE_VERSION", None if compose_version is None else compose_version >= p.min_compose_version, runtime.get("compose_version"), f">={p.min_compose_version[0]}.{p.min_compose_version[1]}"))
    checks.append(_check("TIME_SYNCHRONIZED", clock.get("synchronized") is True if "synchronized" in clock else None, clock.get("synchronized"), True))

    failed = [x["code"] for x in checks if x["status"] == "FAIL"]
    missing = [x["code"] for x in checks if x["status"] == "NO_DATA"]
    decision = "PASS" if not failed and not missing else "FAIL"
    return {
        "node_id": evidence.get("node_id"),
        "decision": decision,
        "checks": checks,
        "failed_checks": failed,
        "missing_checks": missing,
    }


def build_report(*, profile: str | int | None, topology: dict[str, Any], evidence_documents: list[dict[str, Any]]) -> dict[str, Any]:
    code = normalize_profile(profile)
    topology_nodes = [str(x.get("node_id") or "") for x in (topology.get("nodes") or []) if str(x.get("node_id") or "")]
    evidence_ids = [str(x.get("node_id") or "") for x in evidence_documents if str(x.get("node_id") or "")]
    duplicate_ids = sorted({x for x in evidence_ids if evidence_ids.count(x) > 1})
    missing_nodes = sorted(set(topology_nodes) - set(evidence_ids))
    extra_nodes = sorted(set(evidence_ids) - set(topology_nodes))
    node_results = [evaluate_host_evidence(doc, profile=code) for doc in evidence_documents]
    topology_ok = topology.get("schema") == "mgc-multihost-topology-v1" and str(topology.get("profile")) == code and bool(topology_nodes)
    decision = "PASS" if topology_ok and not duplicate_ids and not missing_nodes and not extra_nodes and all(x["decision"] == "PASS" for x in node_results) else "FAIL"
    report = {
        "schema": REPORT_SCHEMA,
        "release": APP_VERSION,
        "schema_version": SCHEMA_VERSION,
        "profile": code,
        "decision": decision,
        "production_authorized": False,
        "performance_certified": False,
        "human_approval_required": True,
        "policy": profile_contract(code),
        "topology": {
            "schema": topology.get("schema"),
            "profile": topology.get("profile"),
            "expected_nodes": topology_nodes,
            "topology_contract_valid": topology_ok,
        },
        "node_results": node_results,
        "missing_nodes": missing_nodes,
        "extra_nodes": extra_nodes,
        "duplicate_node_ids": duplicate_ids,
        "notes": [
            "PASS establishes a baseline target-host deployment envelope only.",
            "Production load/capacity, CVE/SCA, integration and human change approval remain separate gates.",
        ],
    }
    return attach_integrity(report)
