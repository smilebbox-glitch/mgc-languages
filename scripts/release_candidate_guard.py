from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = ROOT / "RELEASE_MANIFEST_v6.0.29.json"
BOOT_PATH = ROOT / "static/frontend/boot.js"
INDEX_PATH = ROOT / "static/index.html"

# Keep the guard independent from a developer database.
os.environ.setdefault("AUTO_CREATE_SCHEMA", "false")
os.environ.setdefault("MGC_ADMIN_USERNAME", "")
os.environ.setdefault("MGC_ADMIN_PASSWORD", "")

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from mgc.services.practice_games import GAME_TYPES, MAX_GAME_ANSWERS  # noqa: E402
import app as runtime  # noqa: E402


def parse_boot_modules(boot: str) -> list[str]:
    match = re.search(r"const requiredModules = \[(.*?)\];", boot, flags=re.S)
    if not match:
        raise AssertionError("requiredModules array not found in boot.js")
    return re.findall(r"'([^']+)'", match.group(1))


def check(ok: bool, message: str, failures: list[str]) -> None:
    if not ok:
        failures.append(message)


def main() -> int:
    parser = argparse.ArgumentParser(description="MGC Languages v6.0.29 Release Candidate / Pilot Freeze guard")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    failures: list[str] = []
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    boot = BOOT_PATH.read_text(encoding="utf-8")
    index = INDEX_PATH.read_text(encoding="utf-8")

    check(manifest.get("release") == "6.0.29", "manifest release must be 6.0.29", failures)
    check(manifest.get("candidate") == "RC1", "candidate must be RC1", failures)
    check(manifest.get("status") == "pilot-freeze", "status must be pilot-freeze", failures)
    check(manifest.get("freeze") is True, "freeze flag must be true", failures)
    check(manifest.get("base_release") == "6.0.28", "base release must be v6.0.28", failures)

    game_contract = manifest["game_contract"]
    check(game_contract["count"] == 20, "manifest must freeze 20 game types", failures)
    check(game_contract["max_answers_per_session"] == 5, "manifest must freeze max-five answers", failures)
    check(game_contract["anti_farm"] == "unchanged", "anti-farm must remain unchanged", failures)
    check(list(GAME_TYPES) == game_contract["game_types"], "runtime GAME_TYPES differs from frozen manifest", failures)
    check(MAX_GAME_ANSWERS == 5, "runtime MAX_GAME_ANSWERS must remain 5", failures)

    check(len(runtime.TERMS["chinese"]) == 2029, "Chinese runtime vocabulary must remain 2029", failures)
    check(len(runtime.TERMS["english"]) == 2029, "English runtime vocabulary must remain 2029", failures)
    check(len(runtime.TERMS["chinese"]) == len(runtime.TERMS["english"]), "Chinese/English parity must remain exact", failures)

    expected_modules = manifest["frontend_modules"]
    actual_modules = parse_boot_modules(boot)
    check(actual_modules == expected_modules, "boot requiredModules differs from frozen frontend module list", failures)
    check("pilotCandidate: 'v6.0.29'" in boot, "boot.js must publish pilotCandidate v6.0.29", failures)

    for rel in manifest["critical_files"]:
        path = ROOT / rel
        check(path.is_file() and path.stat().st_size > 0, f"critical file missing/empty: {rel}", failures)

    deployment = manifest["deployment_contract"]
    for rel in deployment["compose_files"] + deployment["environment_templates"]:
        check((ROOT / rel).is_file(), f"deployment file missing: {rel}", failures)
    check((ROOT / deployment["one_click_windows"]).is_file(), "one-click Company Pilot launcher missing", failures)

    for endpoint in deployment["health_endpoints"]:
        check(endpoint in (ROOT / "scripts/company_pilot_preflight.py").read_text(encoding="utf-8") or endpoint in (ROOT / "docker-compose.lan.yml").read_text(encoding="utf-8"), f"health endpoint contract missing: {endpoint}", failures)

    freeze_rules = manifest["freeze_rules"]
    for key in ("new_game_types", "new_frontend_modules", "new_database_migrations", "new_xp_paths", "feature_additions_after_rc"):
        check(freeze_rules.get(key) is False, f"freeze rule must prohibit {key}", failures)

    # v6.0.29 is a release-control layer only: no new runtime JS/CSS is loaded.
    check("v629" not in index.lower(), "v6.0.29 must not add a new frontend runtime asset", failures)

    result = {
        "release": "6.0.29",
        "candidate": "RC1",
        "status": "GO" if not failures else "NO-GO",
        "freeze": True,
        "game_types": len(GAME_TYPES),
        "max_answers": MAX_GAME_ANSWERS,
        "frontend_modules": len(actual_modules),
        "vocabulary": {"chinese": len(runtime.TERMS["chinese"]), "english": len(runtime.TERMS["english"])},
        "failures": failures,
    }

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"MGC Languages v6.0.29 RC1 Pilot Freeze: {result['status']}")
        print(f"game types={result['game_types']} | max answers={result['max_answers']} | frontend modules={result['frontend_modules']}")
        print(f"vocabulary={result['vocabulary']['chinese']}/{result['vocabulary']['english']}")
        for failure in failures:
            print(f"FAIL: {failure}")

    return 0 if not failures else 2


if __name__ == "__main__":
    raise SystemExit(main())
