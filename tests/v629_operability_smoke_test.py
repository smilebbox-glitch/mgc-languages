from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = json.loads((ROOT / "RELEASE_MANIFEST_v6.0.29.json").read_text(encoding="utf-8"))

# Historical v6.0.29 deployment contract remains readable after the current runtime advances.
assert MANIFEST["release"] == "6.0.29"
assert MANIFEST["candidate"] == "RC1"
assert MANIFEST["freeze"] is True
assert MANIFEST["deployment_contract"]["database"] == "PostgreSQL"
assert MANIFEST["deployment_contract"]["reverse_proxy"] == "Nginx"
for endpoint in ("/health/live", "/health/ready", "/api/meta"):
    assert endpoint in MANIFEST["deployment_contract"]["health_endpoints"]
for rel in MANIFEST["deployment_contract"]["compose_files"] + MANIFEST["deployment_contract"]["environment_templates"]:
    assert (ROOT / rel).is_file(), rel
assert (ROOT / MANIFEST["deployment_contract"]["one_click_windows"]).is_file()

print("PASS: archived v6.0.29 operability contract remains available as the pre-v6.0.30 baseline")