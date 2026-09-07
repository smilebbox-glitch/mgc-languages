#!/usr/bin/env python3
from __future__ import annotations

import argparse
import concurrent.futures
import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from app.services.performance_certification import PROFILES, evaluate_http_result, summarize_latencies  # noqa: E402

SAFE_PREFIXES = ("/api/v1/health", "/api/v1/projects", "/api/v1/integrations")


def one(url: str, api_key: str | None, timeout: float) -> tuple[bool, float, int | None]:
    req = urllib.request.Request(url, method="GET")
    if api_key:
        req.add_header("X-API-Key", api_key)
    started = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            resp.read(64)
            ok = 200 <= resp.status < 400
            return ok, (time.perf_counter() - started) * 1000.0, resp.status
    except urllib.error.HTTPError as exc:
        return False, (time.perf_counter() - started) * 1000.0, exc.code
    except Exception:
        return False, (time.perf_counter() - started) * 1000.0, None


def main() -> None:
    ap = argparse.ArgumentParser(description="Read-only MGC HTTP load probe")
    ap.add_argument("--base-url", default="http://127.0.0.1:8080")
    ap.add_argument("--path", default="/api/v1/health/live")
    ap.add_argument("--requests", type=int, default=100)
    ap.add_argument("--concurrency", type=int, default=4)
    ap.add_argument("--timeout", type=float, default=10.0)
    ap.add_argument("--api-key", default=None)
    ap.add_argument("--profile", choices=sorted(PROFILES), default="ci")
    ap.add_argument("--output", default="")
    args = ap.parse_args()
    if not args.path.startswith(SAFE_PREFIXES):
        raise SystemExit("Refusing load test against a non-read-only/unknown endpoint path")
    if args.requests < 1 or args.requests > 100000:
        raise SystemExit("requests must be 1..100000")
    if args.concurrency < 1 or args.concurrency > 500:
        raise SystemExit("concurrency must be 1..500")
    url = args.base_url.rstrip("/") + args.path
    latencies=[]; errors=0; statuses={}
    started=time.perf_counter()
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.concurrency) as pool:
        futures=[pool.submit(one,url,args.api_key,args.timeout) for _ in range(args.requests)]
        for fut in concurrent.futures.as_completed(futures):
            ok,ms,status=fut.result()
            statuses[str(status)] = statuses.get(str(status),0)+1
            if ok: latencies.append(ms)
            else: errors += 1
    summary=summarize_latencies(latencies, errors=errors, total_requests=args.requests)
    summary["wall_seconds"] = round(time.perf_counter()-started,3)
    summary["requests_per_second"] = round(args.requests / max(summary["wall_seconds"],0.001),3)
    result={
        "schema":"mgc-http-load-test-v1",
        "profile":args.profile,
        "endpoint":args.path,
        "concurrency":args.concurrency,
        "summary":summary,
        "statuses":statuses,
        "acceptance":evaluate_http_result(summary,PROFILES[args.profile]),
        "governance":{"read_only_probe":True,"not_a_business_transaction_test":True},
    }
    text=json.dumps(result,ensure_ascii=False,indent=2)
    print(text)
    if args.output:
        Path(args.output).write_text(text+"\n",encoding="utf-8")
    raise SystemExit(0 if result["acceptance"]["status"]=="PASS" else 3)

if __name__=="__main__":
    main()
