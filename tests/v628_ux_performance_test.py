from __future__ import annotations

import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INDEX = (ROOT / "static/index.html").read_text(encoding="utf-8")
FRONTEND = (ROOT / "static/frontend/ux_performance_v628.js").read_text(encoding="utf-8")
CSS = (ROOT / "static/ux_performance_v628.css").read_text(encoding="utf-8")
HARDENING = (ROOT / "static/frontend/pilot_ux_hardening.js").read_text(encoding="utf-8")
BOOT = (ROOT / "static/frontend/boot.js").read_text(encoding="utf-8")

# Shell accessibility exists before dynamic content finishes rendering.
for marker in [
    'class="v628-skip-link" href="#main"',
    'id="menuToggle" class="icon-button menu-toggle" aria-label="Открыть меню" aria-controls="sidebar" aria-expanded="false"',
    'id="sidebar" class="sidebar" role="navigation" aria-label="Основная навигация"',
    'id="main" class="main" role="main" tabindex="-1"',
    'id="toast" class="toast hidden" role="status" aria-live="polite" aria-atomic="true"',
]:
    assert marker in INDEX, marker

# Dynamic accessibility synchronizes state rather than hard-coding active controls.
for marker in [
    "frontend.register('ux-performance-v628'",
    "aria-expanded",
    "aria-selected",
    "aria-pressed",
    "aria-current",
    "aria-live",
    "aria-atomic",
    "Открыт раздел:",
    "requestAnimationFrame",
    "event.key === 'Escape'",
    "event.key !== '/'",
    "ArrowLeft",
    "ArrowRight",
    "v628-defer",
]:
    assert marker in FRONTEND, marker

# UX polish is additive and must not introduce another API/XP path.
for forbidden in ["fetch(", "/api/", "award_xp", "spendable_xp", "XPEvent"]:
    assert forbidden not in FRONTEND, forbidden

# CSS covers keyboard focus, reduced motion, high contrast and deferred offscreen rendering.
for marker in [
    ":focus-visible",
    "prefers-reduced-motion:reduce",
    "forced-colors:active",
    "content-visibility:auto",
    "contain-intrinsic-size",
    ".v628-skip-link:focus",
]:
    assert marker in CSS, marker

# The older DOM hardening no longer rescans the whole document on every mutation.
assert "const pendingRoots = new Set()" in HARDENING
assert "queueDomFixes(node)" in HARDENING
assert "window.requestAnimationFrame(flushDomFixes)" in HARDENING
assert HARDENING.count("applyDomFixes(document);") == 1
assert "mutation.addedNodes.forEach(function (node) { queueDomFixes(node); });" in HARDENING

# Assets load after previous UX modules and before the release boot contract.
assert "/ux_performance_v628.css" in INDEX
assert "/frontend/ux_performance_v628.js" in INDEX
assert INDEX.index("pilot_ux_hardening.js") < INDEX.index("ux_performance_v628.js") < INDEX.index("frontend/boot.js")
assert "'ux-performance-v628'" in BOOT
assert "pilotCandidate: 'v6.0.28'" in BOOT

subprocess.run(["node", "--check", str(ROOT / "static/frontend/ux_performance_v628.js")], check=True, cwd=ROOT)
subprocess.run(["node", "--check", str(ROOT / "static/frontend/pilot_ux_hardening.js")], check=True, cwd=ROOT)
subprocess.run(["node", "--check", str(ROOT / "static/frontend/boot.js")], check=True, cwd=ROOT)

print("PASS: v6.0.28 improves keyboard/screen-reader UX and batches DOM work without changing game or XP contracts")
