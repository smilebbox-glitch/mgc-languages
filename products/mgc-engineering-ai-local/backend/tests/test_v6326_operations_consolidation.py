from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location("mgcctl_v6326", ROOT / "scripts/mgcctl.py")
assert SPEC and SPEC.loader
mgcctl = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = mgcctl
SPEC.loader.exec_module(mgcctl)


def parse(*argv: str):
    return mgcctl.build_parser().parse_args(list(argv))


def test_current_release_and_schema():
    assert mgcctl.APP_VERSION == "6.3.34"
    assert mgcctl.SCHEMA_VERSION == "6.3.13"
    assert mgcctl.CLI_SCHEMA == "mgc.operations-cli.v1"


def test_parser_exposes_consolidated_commands():
    for command in ("status", "verify", "deploy", "rollback", "backup", "restore", "certify", "provenance", "drill", "diagnose"):
        ns = parse(command, *({
            "provenance": ("--registry", "/tmp/r", "verify"),
            "restore": ("--backup", "/tmp/b"),
            "certify": ("preflight",),
            "drill": ("catalog",),
        }.get(command, ())))
        assert ns.command == command


def test_run_step_never_uses_shell(monkeypatch):
    seen = {}
    def fake_run(argv, **kwargs):
        seen["argv"] = argv; seen.update(kwargs)
        return SimpleNamespace(returncode=0, stdout="ok\n", stderr="")
    monkeypatch.setattr(mgcctl.subprocess, "run", fake_run)
    result = mgcctl.run_step("x", ["python", "-V"])
    assert result.status == "PASS"
    assert seen["shell"] is False
    assert isinstance(seen["argv"], list)


def test_status_offline_json_does_not_require_docker(capsys):
    ns = parse("status", "--offline", "--json")
    assert ns.func(ns) == 0
    doc = json.loads(capsys.readouterr().out)
    assert doc["source_version"] == "6.3.34"
    assert doc["runtime_checked"] is False


def test_verify_quick_dry_run_is_non_destructive(capsys):
    ns = parse("verify", "--scope", "quick", "--dry-run", "--json")
    assert ns.func(ns) == 0
    doc = json.loads(capsys.readouterr().out)
    assert doc["scope"] == "quick"
    assert len(doc["steps"]) == 4
    assert {x["status"] for x in doc["steps"]} == {"DRY_RUN"}


def test_deploy_requires_exact_confirmation():
    ns = parse("deploy", "--mode", "rolling", "--dry-run")
    with pytest.raises(SystemExit, match="--confirm DEPLOY"):
        ns.func(ns)


def test_deploy_refuses_uncertified_target():
    ns = parse("deploy", "--mode", "rolling", "--target-version", "6.3.35", "--confirm", "DEPLOY", "--dry-run")
    with pytest.raises(SystemExit, match="certifies 6.3.34"):
        ns.func(ns)


def test_deploy_dry_run_delegates_to_existing_script(capsys):
    ns = parse("deploy", "--mode", "blue-green", "--confirm", "DEPLOY", "--dry-run", "--json")
    assert ns.func(ns) == 0
    doc = json.loads(capsys.readouterr().out)
    assert doc["steps"][0]["status"] == "DRY_RUN"
    assert doc["steps"][0]["argv"][-1].endswith("scripts/blue_green_cutover.sh")


def test_rollback_requires_exact_confirmation():
    ns = parse("rollback", "--dry-run")
    with pytest.raises(SystemExit, match="--confirm ROLLBACK"):
        ns.func(ns)


def test_restore_requires_exact_confirmation():
    ns = parse("restore", "--backup", "/does/not/exist", "--dry-run")
    with pytest.raises(SystemExit, match="--confirm RESTORE"):
        ns.func(ns)


def test_restore_dry_run_sets_authoritative_confirmation(monkeypatch):
    captured = {}
    def fake_step(name, argv, **kwargs):
        captured.update(kwargs)
        return mgcctl.StepResult(name, list(argv), "DRY_RUN", 0)
    monkeypatch.setattr(mgcctl, "run_step", fake_step)
    ns = parse("restore", "--backup", "/does/not/exist", "--confirm", "RESTORE", "--dry-run")
    assert ns.func(ns) == 0
    assert captured["env"]["MGC_RESTORE_CONFIRM"] == "RESTORE"


def test_load_certification_requires_exact_confirmation():
    ns = parse("certify", "load", "--profile", "15", "--base-url", "https://example.invalid", "--project-code", "fixture", "--part-number", "P1", "--output", "/tmp/load.json", "--dry-run")
    with pytest.raises(SystemExit, match="--confirm LOAD"):
        ns.func(ns)


def test_provenance_dry_run_forwards_argv_without_shell(capsys):
    ns = parse("provenance", "--registry", "/tmp/registry", "--dry-run", "--json", "verify")
    assert ns.func(ns) == 0
    doc = json.loads(capsys.readouterr().out)
    argv = doc["steps"][0]["argv"]
    assert argv[-3:] == ["--registry", "/tmp/registry", "verify"]


def test_diagnose_dry_run_uses_quick_static_scope(capsys):
    ns = parse("diagnose", "--dry-run", "--json")
    assert ns.func(ns) == 0
    doc = json.loads(capsys.readouterr().out)
    assert doc["diagnostic_scope"] == "quick-static"
    assert len(doc["steps"]) == 4
    assert doc["contains_command_output"] is False
    assert all(set(step) == {"name", "status", "returncode"} for step in doc["steps"])


def test_old_make_targets_remain_available():
    make = (ROOT / "Makefile").read_text(encoding="utf-8")
    for target in ("backup:", "restore:", "rolling-upgrade:", "blue-green-rollback:", "release-provenance-verify:"):
        assert target in make
