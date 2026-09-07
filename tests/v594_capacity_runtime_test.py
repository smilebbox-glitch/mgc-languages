from __future__ import annotations

import json
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class HealthyHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:  # noqa: N802
        body = b'{"ok":true}'
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: object) -> None:
        return


class FailingHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:  # noqa: N802
        body = b'{"ok":false}'
        self.send_response(503)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: object) -> None:
        return


def run_server(handler: type[BaseHTTPRequestHandler]) -> tuple[ThreadingHTTPServer, threading.Thread]:
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, thread


def run_probe(port: int, *extra: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            "scripts/multi_user_smoke.py",
            "--base-url",
            f"http://127.0.0.1:{port}",
            "--profile",
            "smoke",
            "--clients",
            "8",
            "--requests",
            "40",
            "--max-p95-ms",
            "5000",
            *extra,
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        timeout=20,
    )


healthy, _ = run_server(HealthyHandler)
try:
    passed = run_probe(healthy.server_port)
finally:
    healthy.shutdown()
    healthy.server_close()
assert passed.returncode == 0, passed.stderr + passed.stdout
report_text = passed.stdout[: passed.stdout.rfind("}\n") + 1]
report = json.loads(report_text)
assert report["success"] == 40
assert report["failed"] == 0
assert report["success_rate_percent"] == 100.0
assert report["latency_ms"]["p50"] is not None
assert report["latency_ms"]["p95"] is not None
assert report["latency_ms"]["p99"] is not None
assert "PASS: concurrent LAN capacity profile" in passed.stdout

failing, _ = run_server(FailingHandler)
try:
    failed = run_probe(failing.server_port, "--min-success-rate", "100")
finally:
    failing.shutdown()
    failing.server_close()
assert failed.returncode == 2
assert "success rate" in failed.stdout

print("PASS: v5.9.4 load probe reports healthy capacity and detects degradation")
