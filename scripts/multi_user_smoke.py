from __future__ import annotations

import argparse
import concurrent.futures
import json
import statistics
import time
import urllib.request


PROFILES = {
    "smoke": {"clients": 20, "requests": 200, "max_p95_ms": 3000.0, "min_success_rate": 100.0},
    "office": {"clients": 50, "requests": 1000, "max_p95_ms": 2500.0, "min_success_rate": 100.0},
    "burst": {"clients": 100, "requests": 2000, "max_p95_ms": 3000.0, "min_success_rate": 99.0},
}


def request_once(url: str, timeout: float) -> tuple[bool, float, str]:
    started = time.perf_counter()
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:
            body = response.read()
            ok = response.status == 200 and bool(body)
            detail = str(response.status)
    except Exception as exc:  # diagnostic utility: retain compact failure type
        ok = False
        detail = f"{type(exc).__name__}: {exc}"
    elapsed_ms = (time.perf_counter() - started) * 1000.0
    return ok, elapsed_ms, detail


def percentile(values: list[float], pct: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, round((len(ordered) - 1) * pct)))
    return ordered[index]


def main() -> int:
    parser = argparse.ArgumentParser(description="Concurrent smoke/load probe for an already running MGC Languages LAN deployment")
    parser.add_argument("--base-url", default="http://127.0.0.1:8080")
    parser.add_argument("--profile", choices=sorted(PROFILES), default="smoke")
    parser.add_argument("--clients", type=int)
    parser.add_argument("--requests", type=int)
    parser.add_argument("--timeout", type=float, default=5.0)
    parser.add_argument("--max-p95-ms", type=float)
    parser.add_argument("--min-success-rate", type=float)
    args = parser.parse_args()

    profile = PROFILES[args.profile]
    clients = max(1, min(300, args.clients if args.clients is not None else int(profile["clients"])))
    requests = max(1, min(20000, args.requests if args.requests is not None else int(profile["requests"])))
    max_p95_ms = args.max_p95_ms if args.max_p95_ms is not None else float(profile["max_p95_ms"])
    min_success_rate = args.min_success_rate if args.min_success_rate is not None else float(profile["min_success_rate"])
    min_success_rate = max(0.0, min(100.0, min_success_rate))

    base = args.base_url.rstrip("/")
    paths = ("/health", "/api/meta", "/health/ready", "/health/live")
    urls = [f"{base}{paths[i % len(paths)]}" for i in range(requests)]

    started = time.perf_counter()
    results: list[tuple[bool, float, str]] = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=clients) as executor:
        futures = [executor.submit(request_once, url, args.timeout) for url in urls]
        for future in concurrent.futures.as_completed(futures):
            results.append(future.result())
    wall = time.perf_counter() - started

    successes = [latency for ok, latency, _ in results if ok]
    failures = [detail for ok, _, detail in results if not ok]
    success_rate = (len(successes) / max(1, len(results))) * 100.0
    p50 = percentile(successes, 0.50)
    p95 = percentile(successes, 0.95)
    p99 = percentile(successes, 0.99)
    report = {
        "base_url": base,
        "profile": args.profile,
        "clients": clients,
        "requests": requests,
        "success": len(successes),
        "failed": len(failures),
        "success_rate_percent": round(success_rate, 3),
        "required_success_rate_percent": min_success_rate,
        "wall_seconds": round(wall, 3),
        "requests_per_second": round(len(results) / max(wall, 0.001), 2),
        "latency_ms": {
            "mean": round(statistics.fmean(successes), 2) if successes else None,
            "p50": round(p50, 2) if successes else None,
            "p95": round(p95, 2) if successes else None,
            "p99": round(p99, 2) if successes else None,
            "max": round(max(successes), 2) if successes else None,
        },
        "thresholds": {"max_p95_ms": max_p95_ms},
        "failure_examples": failures[:10],
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))

    if success_rate + 1e-9 < min_success_rate:
        print(f"FAIL: success rate {success_rate:.3f}% is below {min_success_rate:.3f}%")
        return 2
    if successes and p95 > max_p95_ms:
        print(f"FAIL: p95 {p95:.2f} ms exceeds {max_p95_ms:.2f} ms")
        return 3
    print("PASS: concurrent LAN capacity profile completed within thresholds")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
