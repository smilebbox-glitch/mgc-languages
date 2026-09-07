from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class AuthHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:  # noqa: N802
        cookie = self.headers.get("Cookie", "")
        allowed = "mgc_session=token-" in cookie
        body = b'{"ok":true}' if allowed else b'{"detail":"unauthorized"}'
        self.send_response(200 if allowed else 401)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: object) -> None:
        return


def run_probe(port: int, sessions: dict[str, object], *, report_file: Path | None = None) -> subprocess.CompletedProcess[str]:
    with tempfile.TemporaryDirectory(prefix="mgc-v595-") as td:
        path = Path(td) / "sessions.json"
        path.write_text(json.dumps(sessions), encoding="utf-8")
        cmd = [
            sys.executable,
            "scripts/authenticated_load.py",
            "--base-url",
            f"http://127.0.0.1:{port}",
            "--sessions-file",
            str(path),
            "--profile",
            "pilot",
            "--users",
            "4",
            "--requests",
            "48",
            "--max-p95-ms",
            "5000",
        ]
        if report_file is not None:
            cmd.extend(["--report-file", str(report_file)])
        return subprocess.run(
            cmd,
            cwd=ROOT,
            text=True,
            capture_output=True,
            timeout=20,
        )


server = ThreadingHTTPServer(("127.0.0.1", 0), AuthHandler)
thread = threading.Thread(target=server.serve_forever, daemon=True)
thread.start()
try:
    valid = {
        "sessions": [
            {"username": f"u{i}", "session_token": f"token-{i}"}
            for i in range(1, 5)
        ]
    }
    with tempfile.TemporaryDirectory(prefix="mgc-v595-report-") as td:
        report_path = Path(td) / "report.json"
        passed = run_probe(server.server_port, valid, report_file=report_path)
        assert passed.returncode == 0, passed.stderr + passed.stdout
        assert '"authenticated_users": 4' in passed.stdout
        assert '"success": 48' in passed.stdout
        assert '"failed": 0' in passed.stdout
        assert '"p99"' in passed.stdout
        assert "PASS: authenticated multi-user load" in passed.stdout
        report = json.loads(report_path.read_text(encoding="utf-8"))
        assert report["authenticated_users"] == 4
        assert report["success"] == 48
        serialized = json.dumps(report)
        assert "session_token" not in serialized
        for index in range(1, 5):
            assert f"token-{index}" not in serialized

    invalid = {"sessions": [{"username": "bad", "session_token": "invalid"}]}
    failed = run_probe(server.server_port, invalid)
    assert failed.returncode == 2
    assert "authenticated success rate" in failed.stdout
finally:
    server.shutdown()
    server.server_close()

load_source = (ROOT / "scripts/authenticated_load.py").read_text(encoding="utf-8")
for endpoint in (
    "/api/me",
    "/api/gamification/me",
    "/api/learning/preferences",
    "/api/review/queue?language=chinese&limit=10",
    "/api/language/chinese/summary",
    "/api/language/english/quiz?count=5",
):
    assert endpoint in load_source
assert '"pilot"' in load_source and '"team"' in load_source and '"burst"' in load_source
assert "--report-file" in load_source

seed_source = (ROOT / "scripts/seed_authenticated_load.py").read_text(encoding="utf-8")
assert 'LOAD_TEST_FIXTURES_ENABLED' in seed_source
assert 'APP_ENV", "development"' in seed_source
assert '== "production"' in seed_source
assert "token_digest(raw_token)" in seed_source
assert "LoginSession(" in seed_source

print("PASS: v5.9.5 authenticated load probe, sanitized report and fixture safety contracts")
