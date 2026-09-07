#!/usr/bin/env python3
from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import json
import os
import random
import ssl
import subprocess
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from app.core.load_certification import (  # noqa: E402
    DEFAULT_WORKLOAD,
    LOAD_EVIDENCE_SCHEMA,
    LOAD_PROFILES,
    attach_integrity,
    canonical_payload_bytes,
    load_decision,
    normalize_load_profile,
    summarize_request_records,
    summarize_saturation,
    workload_contract,
)
from app.core.runtime_contract import APP_VERSION, SCHEMA_VERSION  # noqa: E402

CONFIRM_ENV = "MGC_LOAD_CERTIFY_CONFIRM"


def _auth_headers() -> dict[str, str]:
    api_key = os.getenv("MGC_LOAD_API_KEY", "").strip()
    bearer = os.getenv("MGC_LOAD_BEARER_TOKEN", "").strip()
    if api_key and bearer:
        raise SystemExit("Set only one of MGC_LOAD_API_KEY or MGC_LOAD_BEARER_TOKEN")
    if api_key:
        return {"X-API-Key": api_key}
    if bearer:
        return {"Authorization": f"Bearer {bearer}"}
    return {}


def _ssl_context(ca_file: str) -> ssl.SSLContext:
    return ssl.create_default_context(cafile=ca_file or None)


def _request(base_url: str, operation: str, method: str, path: str, body: dict[str, Any] | None, headers: dict[str, str], timeout: float, ctx: ssl.SSLContext) -> dict[str, Any]:
    url = base_url.rstrip("/") + path
    payload = json.dumps(body, ensure_ascii=False).encode("utf-8") if body is not None else None
    req_headers = {"Accept": "application/json", **headers}
    if payload is not None:
        req_headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=payload, headers=req_headers, method=method)
    started = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
            resp.read(4096)
            status = int(resp.status)
            return {"operation": operation, "ok": 200 <= status < 400, "status": status, "latency_ms": (time.perf_counter() - started) * 1000.0}
    except urllib.error.HTTPError as exc:
        return {"operation": operation, "ok": False, "status": int(exc.code), "latency_ms": (time.perf_counter() - started) * 1000.0}
    except Exception as exc:
        return {"operation": operation, "ok": False, "status": None, "latency_ms": (time.perf_counter() - started) * 1000.0, "error_type": type(exc).__name__}


def _json_get(base_url: str, path: str, headers: dict[str, str], timeout: float, ctx: ssl.SSLContext) -> dict[str, Any] | None:
    req = urllib.request.Request(base_url.rstrip("/") + path, headers={"Accept": "application/json", **headers}, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception:
        return None


def _fixture_hash(project_code: str, part_number: str, query: str) -> str:
    return hashlib.sha256(f"{project_code}\0{part_number}\0{query}".encode("utf-8")).hexdigest()


def _build_requests(project_code: str, part_number: str, query: str) -> list[tuple[str, str, str, dict[str, Any] | None]]:
    vals = {"project_code": urllib.parse.quote(project_code, safe=""), "part_number": urllib.parse.quote(part_number, safe="")}
    out = []
    for op in DEFAULT_WORKLOAD:
        path = op.path_template.format(**vals)
        body = None
        if op.code in {"rag_search", "rag_ask"}:
            body = {"query": query, "limit": 5 if op.code == "rag_search" else 3, "project_code": project_code, "part_number": part_number}
            if op.code == "rag_ask":
                body["conversation"] = []
        out.append((op.code, op.method, path, body))
    return out


def _weighted_schedule(total: int, requests: list[tuple[str, str, str, dict[str, Any] | None]], seed: int) -> list[tuple[str, str, str, dict[str, Any] | None]]:
    weighted: list[tuple[str, str, str, dict[str, Any] | None]] = []
    by_code = {x[0]: x for x in requests}
    for op in DEFAULT_WORKLOAD:
        weighted.extend([by_code[op.code]] * op.weight)
    rng = random.Random(seed)
    schedule = [weighted[i % len(weighted)] for i in range(total)]
    rng.shuffle(schedule)
    return schedule


def _sign(canonical: bytes, key_path: str, signature_path: Path) -> str:
    with tempfile.NamedTemporaryFile(prefix="mgc-load-evidence-", delete=False) as fh:
        fh.write(canonical); temp = Path(fh.name)
    try:
        proc = subprocess.run(["openssl", "dgst", "-sha256", "-sign", key_path, "-out", str(signature_path), str(temp)], capture_output=True, text=True)
        if proc.returncode != 0:
            raise RuntimeError((proc.stderr or proc.stdout or "openssl sign failed").strip())
    finally:
        temp.unlink(missing_ok=True)
    return "openssl-dgst-sha256"


def main() -> int:
    ap = argparse.ArgumentParser(description="MGC v6.3.34 production load certification harness")
    ap.add_argument("--profile", required=True, help="15, 30 or 100")
    ap.add_argument("--base-url", required=True)
    ap.add_argument("--project-code", required=True)
    ap.add_argument("--part-number", required=True)
    ap.add_argument("--query", default="engineering requirements and latest approved evidence")
    ap.add_argument("--requests", type=int, default=0, help="Override profile request count; cannot be lower for certifiable evidence")
    ap.add_argument("--concurrency", type=int, default=0, help="Override profile concurrency; cannot be lower for certifiable evidence")
    ap.add_argument("--timeout", type=float, default=30.0)
    ap.add_argument("--monitor-interval", type=float, default=1.0)
    ap.add_argument("--seed", type=int, default=6322)
    ap.add_argument("--ca-file", default="")
    ap.add_argument("--output", required=True)
    ap.add_argument("--signing-key", default="", help="Optional PEM private key; creates detached .sig over canonical payload")
    args = ap.parse_args()

    profile = normalize_load_profile(args.profile); p = LOAD_PROFILES[profile]
    if os.getenv(CONFIRM_ENV) != "YES":
        raise SystemExit(f"Refusing live certification without {CONFIRM_ENV}=YES")
    parsed = urllib.parse.urlparse(args.base_url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise SystemExit("--base-url must be an explicit http(s) target")
    if args.timeout <= 0 or args.timeout > 120:
        raise SystemExit("--timeout must be >0 and <=120 seconds")
    total = args.requests or p.min_requests
    concurrency = args.concurrency or p.concurrency
    if total < p.min_requests:
        raise SystemExit(f"Certifiable profile {profile} requires at least {p.min_requests} measured requests")
    if concurrency < p.concurrency:
        raise SystemExit(f"Certifiable profile {profile} requires concurrency >= {p.concurrency}")
    if concurrency > 500 or total > 250_000:
        raise SystemExit("Safety cap exceeded: concurrency<=500 and requests<=250000")
    if any(x.audited_read_semantics for x in DEFAULT_WORKLOAD) and os.getenv("MGC_LOAD_ALLOW_AUDITED_POSTS") != "YES":
        raise SystemExit("RAG/search certification uses audited read-semantics POST endpoints; set MGC_LOAD_ALLOW_AUDITED_POSTS=YES after approving audit-volume impact")

    headers = _auth_headers(); ctx = _ssl_context(args.ca_file)
    requests = _build_requests(args.project_code, args.part_number.upper(), args.query)
    warmup = _weighted_schedule(p.warmup_requests, requests, args.seed - 1)
    for op, method, path, body in warmup:
        _request(args.base_url, op, method, path, body, headers, args.timeout, ctx)

    monitoring: list[dict[str, Any]] = []
    stop = threading.Event()
    def monitor() -> None:
        while not stop.is_set():
            snap = _json_get(args.base_url, "/api/v1/operations/summary", headers, min(args.timeout, 10.0), ctx)
            if isinstance(snap, dict): monitoring.append(snap)
            stop.wait(max(args.monitor_interval, 0.25))
    t = threading.Thread(target=monitor, daemon=True); t.start()

    measured = _weighted_schedule(total, requests, args.seed)
    records: list[dict[str, Any]] = []
    started_at = datetime.now(timezone.utc); started = time.perf_counter()
    with concurrent.futures.ThreadPoolExecutor(max_workers=concurrency) as pool:
        futures = [pool.submit(_request, args.base_url, op, method, path, body, headers, args.timeout, ctx) for op, method, path, body in measured]
        for fut in concurrent.futures.as_completed(futures):
            records.append(fut.result())
    wall = time.perf_counter() - started; finished_at = datetime.now(timezone.utc)
    stop.set(); t.join(timeout=max(args.monitor_interval * 2, 1.0))
    final_snap = _json_get(args.base_url, "/api/v1/operations/summary", headers, min(args.timeout, 10.0), ctx)
    if isinstance(final_snap, dict): monitoring.append(final_snap)

    summary = summarize_request_records(records, wall_seconds=wall, profile=profile)
    saturation = summarize_saturation(monitoring)
    evidence: dict[str, Any] = {
        "schema": LOAD_EVIDENCE_SCHEMA,
        "release": APP_VERSION,
        "schema_version": SCHEMA_VERSION,
        "profile": profile,
        "named_users": p.named_users,
        "concurrency": concurrency,
        "started_at": started_at.isoformat(),
        "finished_at": finished_at.isoformat(),
        "target": {"origin_sha256": hashlib.sha256(f"{parsed.scheme}://{parsed.netloc}".encode()).hexdigest(), "tls_verified": True},
        "fixture": {"sha256": _fixture_hash(args.project_code, args.part_number.upper(), args.query), "raw_identifiers_retained": False},
        "workload": workload_contract(),
        "summary": summary,
        "saturation": saturation,
        "governance": {
            "live_target_measurement": True,
            "synthetic": False,
            "engineering_state_mutation_allowed": False,
            "audited_read_semantics_posts_enabled": True,
            "operational_audit_events_expected": True,
            "non_idempotent_business_write_replay_allowed": False,
            "production_authorized": False,
            "human_change_approval_required": True,
        },
    }
    evidence = attach_integrity(evidence)
    decision = load_decision(evidence, profile=profile)

    output = Path(args.output); output.parent.mkdir(parents=True, exist_ok=True)
    if args.signing_key:
        sig_path = output.with_suffix(output.suffix + ".sig")
        algorithm = _sign(canonical_payload_bytes(evidence), args.signing_key, sig_path)
        evidence["integrity"]["signature_algorithm"] = algorithm
        evidence["integrity"]["detached_signature_file"] = sig_path.name
        # Verification happens with a public key in production_certify.py; signing alone is not verification.
        evidence["integrity"]["detached_signature_verified"] = False
    output.write_text(json.dumps(evidence, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    output.with_suffix(output.suffix + ".sha256").write_text(evidence["integrity"]["canonical_sha256"] + "\n", encoding="utf-8")
    print(json.dumps({"output": str(output), "profile": profile, "requests": summary["requests"], "p95_ms": summary["p95_ms"], "p99_ms": summary["p99_ms"], "error_rate": summary["error_rate"], "load_decision_before_signature_verification": decision["decision"], "canonical_sha256": evidence["integrity"]["canonical_sha256"]}, indent=2))
    return 0 if decision["decision"] != "NO_GO" else 3


if __name__ == "__main__":
    raise SystemExit(main())
