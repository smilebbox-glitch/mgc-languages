#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from app.core.runtime_contract import APP_VERSION, SCHEMA_VERSION  # noqa: E402
from app.core.target_host_assurance import EVIDENCE_SCHEMA, REPORT_SCHEMA, build_report, validate_integrity  # noqa: E402

checks=[]
def ck(name, ok): checks.append((name, bool(ok)))

ck("runtime_6329", APP_VERSION == "6.3.34" and SCHEMA_VERSION == "6.3.13")
for path in [
    "backend/app/core/target_host_assurance.py",
    "scripts/target_host_probe.py",
    "scripts/target_host_certify.py",
    "scripts/target_host_deployment_guard.py",
    "TARGET_HOST_DEPLOYMENT_ASSURANCE_v6.3.34.md",
]:
    ck("exists_" + Path(path).stem, (ROOT / path).exists())

sample = {
    "schema": EVIDENCE_SCHEMA, "release": APP_VERSION, "schema_version": SCHEMA_VERSION,
    "profile": "30", "node_id": "mgc-app-a",
    "system": {"os":"Linux","architecture":"x86_64","cpu_cores":8,"memory_gib":16},
    "storage": {"free_gib":120,"used_ratio":0.50,"rw_fsync_passed":True},
    "resource_limits": {"nofile_soft":8192},
    "container_runtime": {"docker_cli":True,"daemon_reachable":True,"server_version":"27.5.1","compose_version":"2.32.0"},
    "time_sync": {"synchronized":True},
}
sample_b = json.loads(json.dumps(sample)); sample_b["node_id"] = "mgc-app-b"
topology = {"schema":"mgc-multihost-topology-v1","profile":"30","nodes":[{"node_id":"mgc-app-a"},{"node_id":"mgc-app-b"}]}
report = build_report(profile="30", topology=topology, evidence_documents=[sample, sample_b])
ck("report_schema", report.get("schema") == REPORT_SCHEMA)
ck("synthetic_pass", report.get("decision") == "PASS")
ck("integrity", validate_integrity(report)[0] is True)
missing = build_report(profile="30", topology=topology, evidence_documents=[sample])
ck("missing_node_fail_closed", missing.get("decision") == "FAIL" and missing.get("missing_nodes") == ["mgc-app-b"])
old = json.loads(json.dumps(sample)); old["container_runtime"]["server_version"] = "20.10.24"
old_report = build_report(profile="30", topology={"schema":"mgc-multihost-topology-v1","profile":"30","nodes":[{"node_id":"mgc-app-a"}]}, evidence_documents=[old])
ck("old_docker_fail_closed", old_report.get("decision") == "FAIL")
mgc = (ROOT / "scripts/mgcctl.py").read_text(encoding="utf-8")
ck("mgcctl_registered", "target-host" in mgc and "host-assurance" in mgc)
rolling = (ROOT / "scripts/rolling_upgrade.sh").read_text(encoding="utf-8")
blue = (ROOT / "scripts/blue_green_cutover.sh").read_text(encoding="utf-8")
ck("rolling_guard", "target_host_deployment_guard.py" in rolling)
ck("bluegreen_guard", "target_host_deployment_guard.py" in blue)
ck("no_db_migration", not any((ROOT / "backend/app/db/migrations/versions").glob("*6.3.34*")) if (ROOT / "backend/app/db/migrations/versions").exists() else True)
for n,o in checks: print(("PASS" if o else "FAIL") + ": " + n)
failed=[n for n,o in checks if not o]
print(f"target-host assurance preflight: {len(checks)-len(failed)}/{len(checks)} PASS")
raise SystemExit(2 if failed else 0)
