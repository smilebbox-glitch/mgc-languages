from __future__ import annotations

import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INDEX = (ROOT / "static/index.html").read_text(encoding="utf-8")
BOUNDARY = (ROOT / "static/frontend/error_boundary.js").read_text(encoding="utf-8")
BOOT = (ROOT / "static/frontend/boot.js").read_text(encoding="utf-8")

runtime_pos = INDEX.index('/frontend/runtime.js')
error_pos = INDEX.index('/frontend/error_boundary.js')
legacy_pos = INDEX.index('/app.js')
assert runtime_pos < error_pos < legacy_pos
assert INDEX.count('/frontend/error_boundary.js') == 1
assert "'error-boundary'" in BOOT
assert "frontend.get('error-boundary').reconcile()" in BOOT

for token in (
    "const MAX_EVENTS = 20",
    "authorization\\s*:\\s*bearer",
    "mgc_(?:session|csrf)",
    "password|token|secret",
    "dataset.mgcFrontend = 'degraded'",
    "window.addEventListener('error'",
    "window.addEventListener('unhandledrejection'",
    "function reconcile()",
    "reconcile: reconcile",
    "frontend.register('error-boundary'",
):
    assert token in BOUNDARY, token

# No persistence or automatic outbound telemetry from browser diagnostics.
for forbidden in (
    "localStorage",
    "sessionStorage",
    "fetch(",
    "XMLHttpRequest",
    "sendBeacon",
    "document.cookie",
):
    assert forbidden not in BOUNDARY, forbidden

harness = r'''
const fs = require('fs');
const vm = require('vm');
const listeners = {};
global.window = global;
global.location = {href: 'http://localhost/'};
global.document = {documentElement: {dataset: {}}};
global.addEventListener = function (name, fn) { listeners[name] = fn; };
vm.runInThisContext(fs.readFileSync('static/frontend/runtime.js', 'utf8'));
vm.runInThisContext(fs.readFileSync('static/frontend/error_boundary.js', 'utf8'));
const boundary = MGCFrontend.get('error-boundary');
const item = boundary.record(
  'error',
  'password=supersecret mgc_session=sessionvalue Authorization: Bearer bearervalue token=tokvalue',
  'https://example.test/static/app.js?secret=queryvalue',
  10,
  4
);
const first = JSON.stringify(item);
for (const secret of ['supersecret','sessionvalue','bearervalue','tokvalue','queryvalue']) {
  if (first.includes(secret)) throw new Error('secret leaked: ' + secret);
}
if (item.source !== '/static/app.js') throw new Error('source was not query-scrubbed: ' + item.source);
if (document.documentElement.dataset.mgcFrontend !== 'degraded') throw new Error('frontend not degraded');
MGCFrontend.markReady();
if (document.documentElement.dataset.mgcFrontend !== 'ready') throw new Error('runtime markReady setup failed');
if (boundary.reconcile() !== 'degraded') throw new Error('reconcile did not preserve degraded state');
if (document.documentElement.dataset.mgcFrontend !== 'degraded') throw new Error('degraded state was overwritten');
for (let i = 0; i < 25; i++) boundary.record('error', 'message-' + i, '', i, 0);
if (boundary.snapshot().length !== 20) throw new Error('ring buffer is not bounded');
if (!listeners.error || !listeners.unhandledrejection) throw new Error('global error listeners missing');
const count = boundary.snapshot().length;
if (boundary.clear() !== 'ready') throw new Error('clear did not restore ready state');
if (boundary.snapshot().length !== 0) throw new Error('clear did not drop diagnostics');
if (document.documentElement.dataset.mgcFrontend !== 'ready') throw new Error('ready state not restored after clear');
console.log(JSON.stringify({ok:true,count:count,max:boundary.maxEvents,cleared:true}));
'''
result = subprocess.run(
    ["node", "-e", harness],
    check=True,
    cwd=ROOT,
    capture_output=True,
    text=True,
)
payload = json.loads(result.stdout.strip())
assert payload == {"ok": True, "count": 20, "max": 20, "cleared": True}

print("PASS: v6.0.2 frontend error boundary is bounded, privacy-safe and preserves early degraded state")
