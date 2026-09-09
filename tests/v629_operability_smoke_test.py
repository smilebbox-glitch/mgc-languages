from __future__ import annotations

import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = json.loads((ROOT / "RELEASE_MANIFEST_v6.0.29.json").read_text(encoding="utf-8"))
CONFIG = (ROOT / "mgc/config.py").read_text(encoding="utf-8")
CI = (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")
RC_GATE = (ROOT / ".github/workflows/ci-v629-release-candidate.yml").read_text(encoding="utf-8")
INDEX = (ROOT / "static/index.html").read_text(encoding="utf-8")
BOOT = (ROOT / "static/frontend/boot.js").read_text(encoding="utf-8")
ADAPTIVE_ROUTER = (ROOT / "mgc/routers/adaptive_training.py").read_text(encoding="utf-8")
APP_JS = (ROOT / "static/app.js").read_text(encoding="utf-8")
UX_HARDENING = (ROOT / "static/frontend/pilot_ux_hardening.js").read_text(encoding="utf-8")

assert MANIFEST["release"] == "6.0.29"
assert MANIFEST["candidate"] == "RC1"
assert MANIFEST["freeze"] is True

# The deployed /api/meta endpoint must not silently report an old build number.
assert 'APP_VERSION = os.getenv("APP_VERSION", "6.0.29").strip() or "6.0.29"' in CONFIG
assert "pilotCandidate: 'v6.0.29'" in BOOT

# Static shell and the critical post-RC modules must be reachable through Nginx in LAN smoke.
for asset in (
    "/frontend/boot.js",
    "/frontend/game_lab_v618.js",
    "/frontend/shift_simulation_v624.js",
    "/frontend/team_leaderboard_v626.js",
    "/frontend/adaptive_training_v627.js",
    "/frontend/ux_performance_v628.js",
):
    assert asset in CI, asset

assert "/frontend/boot.js" in INDEX

# Health/meta endpoints declared by the release manifest must be exercised by real HTTP smoke.
for endpoint in MANIFEST["deployment_contract"]["health_endpoints"]:
    assert f"http://127.0.0.1:18080{endpoint}" in CI, endpoint

# Use the real authenticated adaptive route, so a renamed/nonexistent path cannot make the smoke test lie.
assert '@router.get("/api/adaptive-training/plan")' in ADAPTIVE_ROUTER

# Runtime metadata and unauthenticated protection are explicit operability contracts.
for marker in (
    "Verify HTTP operability through Nginx",
    'meta.get("version") == "6.0.29"',
    'meta.get("title") == "MGC Languages"',
    "/api/adaptive-training/plan",
    "/api/manager/shift-analytics",
    "401|403",
):
    assert marker in CI, marker

# Natural pronunciation is a non-versioned pilot quality fix: prefer a high-quality
# browser/OS voice when available, while retaining the existing offline server TTS fallback.
for marker in (
    "NATURAL_VOICE_NAME",
    "MIN_NATURAL_VOICE_SCORE",
    "voice.localService === true",
    "naturalRate",
    "selectNaturalVoice",
    "speechSynthesis.addEventListener('voiceschanged', refreshVoiceCache)",
    "return originalPlayPronunciation(text, rate, language)",
):
    assert marker in UX_HARDENING, marker
assert "server_audio" in APP_JS
assert "/api/pronunciation/audio" in APP_JS

assert "python tests/v629_operability_smoke_test.py" in CI
assert "python tests/v629_operability_smoke_test.py" in RC_GATE

# Temporary test-VM deployment is part of operability: it must remain CPU-only,
# run on port 8080 next to Okno v Kitai:3000, and explicitly disable server TTS.
subprocess.run(["python", str(ROOT / "tests/vm_no_ai_deployment_test.py")], check=True, cwd=ROOT)

# Keep source/runtime syntax checks close to the operability contract.
subprocess.run(["python", "-m", "compileall", "-q", "mgc", "mgc_core", "asgi.py"], check=True, cwd=ROOT)
subprocess.run(["node", "--check", str(ROOT / "static/frontend/boot.js")], check=True, cwd=ROOT)
subprocess.run(["node", "--check", str(ROOT / "static/frontend/pilot_ux_hardening.js")], check=True, cwd=ROOT)
subprocess.run(["python", str(ROOT / "scripts/release_candidate_guard.py"), "--json"], check=True, cwd=ROOT)

print("PASS: v6.0.29 operability contract covers runtime, LAN HTTP checks, protected APIs, natural pronunciation fallback and CPU-only VM deployment")