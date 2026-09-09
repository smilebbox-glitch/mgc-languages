from __future__ import annotations

import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STATIC = ROOT / "static"

manifest = json.loads((STATIC / "manifest.webmanifest").read_text(encoding="utf-8"))
index = (STATIC / "index.html").read_text(encoding="utf-8")
worker = (STATIC / "service-worker.js").read_text(encoding="utf-8")
register = (STATIC / "pwa-register.js").read_text(encoding="utf-8")
offline = (STATIC / "offline.html").read_text(encoding="utf-8")
boot = (STATIC / "frontend/boot.js").read_text(encoding="utf-8")
release = json.loads((ROOT / "RELEASE_MANIFEST_v6.0.29.json").read_text(encoding="utf-8"))

# Installable web-app contract.
assert manifest["name"] == "MGC Language Lab"
assert manifest["id"] == "/"
assert manifest["start_url"] == "/"
assert manifest["scope"] == "/"
assert manifest["display"] == "standalone"
assert manifest["theme_color"] == "#f8fbfe"
assert manifest["background_color"] == "#f8fbfe"
assert len(manifest["icons"]) >= 2
assert {icon["purpose"] for icon in manifest["icons"]} >= {"any", "maskable"}

assert '<link rel="manifest" href="/manifest.webmanifest">' in index
assert '<meta name="mobile-web-app-capable" content="yes">' in index
assert '<meta name="apple-mobile-web-app-capable" content="yes">' in index
assert '<script src="/pwa-register.js" defer></script>' in index
assert "/frontend/pwa.js" not in index

# Registration must require HTTPS (or localhost) and bypass the HTTP cache for SW updates.
assert "window.location.protocol === 'https:'" in register
assert "navigator.serviceWorker.register('/service-worker.js'" in register
assert "scope: '/'" in register
assert "updateViaCache: 'none'" in register

# Privacy/security invariant: only public static extensions can enter Cache Storage.
for sensitive_prefix in (
    "/api", "/auth", "/admin", "/manager", "/observability",
    "/notifications", "/user", "/users", "/metrics", "/health", "/ready",
):
    assert repr(sensitive_prefix) in worker, sensitive_prefix
assert "request.headers.has('authorization')" in worker
assert "STATIC_ASSET_RE" in worker
assert "request.mode === 'navigate'" in worker
assert "fetch(request, {cache: 'no-store'})" in worker
assert "caches.match(OFFLINE_URL)" in worker
assert "'/index.html'" not in worker
assert "'/app'" not in worker

# Offline fallback must remain generic and explicitly avoid pretending private data is available.
assert "Персональные данные" in offline
assert "не сохраняются" in offline
assert "<form" not in offline.lower()

# This infrastructure addition must not change the frozen product version/module contract.
assert release["release"] == "6.0.29"
assert release["freeze"] is True
assert "pilotCandidate: 'v6.0.29'" in boot
assert "'pwa'" not in boot

subprocess.run(["node", "--check", str(STATIC / "service-worker.js")], check=True, cwd=ROOT)
subprocess.run(["node", "--check", str(STATIC / "pwa-register.js")], check=True, cwd=ROOT)

print("PASS: PWA/web-app shell is installable, version-neutral and excludes private/API data from Cache Storage")
