#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import platform
import resource
import shutil
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
import sys
sys.path.insert(0, str(ROOT / "backend"))
from app.core.runtime_contract import APP_VERSION, SCHEMA_VERSION  # noqa: E402
from app.core.target_host_assurance import EVIDENCE_SCHEMA, normalize_profile  # noqa: E402


def run(argv: list[str]) -> tuple[int, str]:
    try:
        p = subprocess.run(argv, text=True, capture_output=True, timeout=10, shell=False)
        return p.returncode, (p.stdout or p.stderr or "").strip()
    except (OSError, subprocess.SubprocessError):
        return 127, ""


def memory_gib() -> float | None:
    try:
        for line in Path("/proc/meminfo").read_text().splitlines():
            if line.startswith("MemTotal:"):
                kib = int(line.split()[1]); return round(kib / (1024 * 1024), 3)
    except (OSError, ValueError, IndexError):
        return None
    return None


def storage_probe(path: Path) -> dict:
    try:
        path.mkdir(parents=True, exist_ok=True)
        usage = shutil.disk_usage(path)
        rw_ok = False
        with tempfile.NamedTemporaryFile(prefix=".mgc-host-probe-", dir=path, delete=False) as fh:
            probe_path = Path(fh.name)
            token = os.urandom(32)
            fh.write(token); fh.flush(); os.fsync(fh.fileno())
        try:
            rw_ok = probe_path.read_bytes() == token
        finally:
            probe_path.unlink(missing_ok=True)
        return {
            "free_gib": round(usage.free / (1024 ** 3), 3),
            "total_gib": round(usage.total / (1024 ** 3), 3),
            "used_ratio": round(usage.used / usage.total, 5) if usage.total else None,
            "rw_fsync_passed": rw_ok,
        }
    except OSError:
        return {"free_gib": None, "total_gib": None, "used_ratio": None, "rw_fsync_passed": False}


def docker_probe() -> dict:
    docker = shutil.which("docker")
    if not docker:
        return {"docker_cli": False, "daemon_reachable": False, "server_version": None, "compose_version": None}
    rc, server = run([docker, "version", "--format", "{{.Server.Version}}"])
    crc, compose = run([docker, "compose", "version", "--short"])
    return {
        "docker_cli": True,
        "daemon_reachable": rc == 0 and bool(server),
        "server_version": server if rc == 0 else None,
        "compose_version": compose if crc == 0 else None,
    }


def time_sync_probe() -> dict:
    timedatectl = shutil.which("timedatectl")
    if timedatectl:
        rc, out = run([timedatectl, "show", "-p", "NTPSynchronized", "--value"])
        if rc == 0 and out:
            return {"synchronized": out.strip().lower() == "yes", "source": "timedatectl"}
    chronyc = shutil.which("chronyc")
    if chronyc:
        rc, out = run([chronyc, "tracking"])
        if rc == 0:
            return {"synchronized": "Leap status     : Normal" in out or "Leap status     : Not synchronised" not in out, "source": "chronyc"}
    return {"synchronized": None, "source": "unavailable"}


def main() -> int:
    ap = argparse.ArgumentParser(description="Collect privacy-safe MGC target-host deployment evidence on the target node")
    ap.add_argument("--node-id", required=True)
    ap.add_argument("--profile", choices=["15", "30", "100"], required=True)
    ap.add_argument("--storage-path", default=".")
    ap.add_argument("--output", required=True)
    args = ap.parse_args()
    profile = normalize_profile(args.profile)
    soft, hard = resource.getrlimit(resource.RLIMIT_NOFILE)
    evidence = {
        "schema": EVIDENCE_SCHEMA,
        "release": APP_VERSION,
        "schema_version": SCHEMA_VERSION,
        "profile": profile,
        "node_id": args.node_id,
        "captured_at_utc": datetime.now(timezone.utc).isoformat(),
        "privacy": {"hostname_collected": False, "ip_addresses_collected": False, "environment_collected": False, "secrets_collected": False},
        "system": {
            "os": platform.system(),
            "architecture": platform.machine(),
            "kernel_release": platform.release(),
            "cpu_cores": os.cpu_count(),
            "memory_gib": memory_gib(),
        },
        "storage": storage_probe(Path(args.storage_path)),
        "resource_limits": {"nofile_soft": int(soft), "nofile_hard": int(hard)},
        "container_runtime": docker_probe(),
        "time_sync": time_sync_probe(),
    }
    Path(args.output).write_text(json.dumps(evidence, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"output": args.output, "node_id": args.node_id, "release": APP_VERSION}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
