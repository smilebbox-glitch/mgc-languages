from __future__ import annotations

import argparse
import concurrent.futures
import json
import statistics
import time
import urllib.request
from pathlib import Path


PROFILES = {
    "pilot": {"users": 20, "requests": 400, "max_p95_ms": 3000.0, "min_success_rate": 100.0},
    "team": {"users": 50, "requests": 1000, "max_p95_ms": 3000.0, "min_success_rate": 99.5},
    "burst": {"users": 100, "requests": 2000, "max_p95_ms": 4000.0, "min_success_rate": 99.0},
}

ENDPOINTS = (
    "/api/me",
    "/api/gamification/me",
    "/api/learning/preferences",
    "/api/review/queue?language=chinese&limit=10",
    "/api/language/chinese/summary",
    "/api/language/english/quiz?count=5",
)


def percentile(values: list[float], pct: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, round((len(ordered) - 1) * pct)))
    return ordered[index]


def request_once(url: str, token: str, timeout: float) -> tuple[bool, float, str]:
    started = time.perf_counter()
    request = urllib.request.Request(
        url,
        headers={
            "Cookie": f"mgc_session={token}",
            "Accept": "application/json",
            "User-Agent": "mgc-authenticated-load/1",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = response.read()
            ok = response.status == 200 and bool(body)
            detail = f"{response.status} {url}"
    except Exception as exc:
        ok = False
        detail = f"{type(exc).__name__}: {exc} @ {url}"
    elapsed_ms = (time.perf_counter() - started) * 1000.0
    return ok, elapsed_ms, detail


def main() -> int:
    parser = argparse.ArgumentParser(description="Authenticated concurrent load probe for MGC Languages")
    parser.add_argument("--base-url", default="http://127.0.0.1:8080")
    parser.add_argument("--sessions-file", required=True)
    parser.add_argument("--profile", choices=sorted(PROFILES), default="pilot")
    parser.add_argument("--users", type=int)
    parser.add_argument("--requests", type=int)
    parser.add_argument("--timeout", type=float, default=8.0)
    parser.add_argument("--max-p95-ms", type=float)
    parser.add_argument("--min-success-rate", type=float)
    args = parser.parse_args()

    data = json.loads(Path(args.sessions_file).read_text(encoding="utf-8"))
    sessions = data.get("sessions") if isinstance(data, dict) else None
    if not isinstance(sessions, list) or not sessions:
        raise SystemExit("ERROR: sessions file does not contain load-test sessions")
    tokens = [str(item.get("session_token") or "") for item in sessions if isinstance(item, dict)]
    tokens = [token for token in tokens if token]
    if not tokens:
        raise SystemExit("ERROR: no session_token values in sessions file")

    profile = PROFILES[args.profile]
    requested_users = args.users if args.users is not None else int(profile["users"])
    users = max(1, min(len(tokens), min(300, requested_users)))
    request_count = max(1, min(20000, args.requests if args.requests is not None else int(profile["requests"])))
    max_p95_ms = args.max_p95_ms if args.max_p95_ms is not None else float(profile["max_p95_ms"])
    min_success_rate = args.min_success_rate if args.min_success_rate is not None else float(profile["min_success_rate"])
    min_success_rate = max(0.0, min(100.0, min_success_rate))

    selected_tokens = tokens[:users]
    base = args.base_url.rstrip("/")
    work = [
        (f"{base}{ENDPOINTS[index % len(ENDPOINTS)]}", selected_tokens[index % users])
        for index in range(request_count)
    ]

    started = time.perf_counter()
    results: list[tuple[bool, float, str]] = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=users) as executor:
        futures = [executor.submit(request_once, url, token, args.timeout) for url, token in work]
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
        "profile": args.profile,
        "base_url": base,
        "authenticated_users": users,
        "requests": request_count,
        "endpoints": list(ENDPOINTS),
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
        print(f"FAIL: authenticated success rate {success_rate:.3f}% is below {min_success_rate:.3f}%")
        return 2
    if successes and p95 > max_p95_ms:
        print(f"FAIL: authenticated p95 {p95:.2f} ms exceeds {max_p95_ms:.2f} ms")
        return 3
    print("PASS: authenticated multi-user load completed within thresholds")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
