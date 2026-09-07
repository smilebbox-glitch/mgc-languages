from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOCK = threading.Lock()
XP: dict[str, int] = {}
SEEN: set[str] = set()


class Handler(BaseHTTPRequestHandler):
    def _token(self) -> str:
        cookie = self.headers.get("Cookie", "")
        for part in cookie.split(";"):
            part = part.strip()
            if part.startswith("mgc_session="):
                return part.split("=", 1)[1]
        return ""

    def _csrf_ok(self) -> bool:
        cookie = self.headers.get("Cookie", "")
        csrf_cookie = ""
        for part in cookie.split(";"):
            part = part.strip()
            if part.startswith("mgc_csrf="):
                csrf_cookie = part.split("=", 1)[1]
                break
        return bool(csrf_cookie) and csrf_cookie == self.headers.get("X-CSRF-Token", "")

    def _send(self, status: int, payload: dict[str, object]) -> None:
        body = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802
        token = self._token()
        if self.path != "/api/gamification/me" or not token:
            self._send(401, {"detail": "unauthorized"})
            return
        with LOCK:
            xp = XP.setdefault(token, 0)
        self._send(200, {"lifetime_xp": xp, "spendable_xp": xp, "weekly_xp": xp})

    def do_POST(self) -> None:  # noqa: N802
        token = self._token()
        if self.path != "/api/practice/result" or not token or not self._csrf_ok():
            self._send(403, {"detail": "csrf"})
            return
        length = int(self.headers.get("Content-Length", "0") or 0)
        data = json.loads(self.rfile.read(length) or b"{}")
        sid = str(data.get("session_id") or "")
        with LOCK:
            if sid in SEEN:
                self._send(200, {"ok": True, "duplicate": True, "profile": {"lifetime_xp": XP[token]}})
                return
            SEEN.add(sid)
            XP[token] = XP.get(token, 0) + 40
            current = XP[token]
        self._send(200, {"ok": True, "duplicate": False, "awarded": 40, "profile": {"lifetime_xp": current}})

    def log_message(self, format: str, *args: object) -> None:
        return


server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
thread = threading.Thread(target=server.serve_forever, daemon=True)
thread.start()
try:
    sessions = {
        "sessions": [
            {"username": f"u{i}", "user_id": i, "session_token": f"token-{i}"}
            for i in range(1, 5)
        ]
    }
    with tempfile.TemporaryDirectory(prefix="mgc-v596-") as td:
        sessions_path = Path(td) / "sessions.json"
        report_path = Path(td) / "report.json"
        sessions_path.write_text(json.dumps(sessions), encoding="utf-8")
        proc = subprocess.run(
            [
                sys.executable,
                "scripts/concurrent_write_load.py",
                "--base-url",
                f"http://127.0.0.1:{server.server_port}",
                "--sessions-file",
                str(sessions_path),
                "--users",
                "4",
                "--writes-per-user",
                "3",
                "--report-file",
                str(report_path),
            ],
            cwd=ROOT,
            text=True,
            capture_output=True,
            timeout=25,
        )
        assert proc.returncode == 0, proc.stderr + proc.stdout
        report = json.loads(report_path.read_text(encoding="utf-8"))
        assert report["authenticated_users"] == 4
        assert report["attempted_writes"] == 12
        assert report["successful_unique_writes"] == 12
        assert report["duplicate_replays_checked"] == 4
        assert report["duplicate_failures"] == []
        assert report["expected_xp_delta_per_user"] == 120
        assert report["isolation_failures"] == []
        serialized = json.dumps(report)
        assert "token-1" not in serialized
        assert "session_token" not in serialized
        assert "PASS: concurrent authenticated write integrity" in proc.stdout
finally:
    server.shutdown()
    server.server_close()

print("PASS: v5.9.6 concurrent write load, CSRF, duplicate and isolation probe")
