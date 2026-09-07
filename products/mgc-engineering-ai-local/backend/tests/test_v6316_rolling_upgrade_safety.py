from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.core import deployment_safety as ds


def _settings(**overrides):
    base = dict(
        rolling_upgrade_enabled=True,
        rolling_upgrade_max_patch_skew=1,
        rolling_upgrade_task_envelope_enabled=True,
        rolling_upgrade_allow_legacy_task_envelopes=True,
        rolling_upgrade_component_registry_enabled=True,
        deployment_component_heartbeat_ttl_seconds=120,
        deployment_profile="core",
        runtime_profile="core",
        redis_url="redis://localhost:6379/0",
        health_timeout_seconds=0.1,
    )
    base.update(overrides)
    return SimpleNamespace(**base)


def test_v6316_version_without_database_schema_change():
    from app.core.runtime_contract import APP_VERSION, SCHEMA_VERSION
    assert APP_VERSION == "6.3.34"
    assert SCHEMA_VERSION == "6.3.13"


def test_adjacent_patch_with_same_schema_is_compatible(monkeypatch):
    monkeypatch.setattr(ds, "get_settings", lambda: _settings())
    out = ds.compatibility("6.3.33", "6.3.13")
    assert out.compatible is True
    assert out.reason == "compatible"


def test_old_patch_beyond_window_is_rejected(monkeypatch):
    monkeypatch.setattr(ds, "get_settings", lambda: _settings())
    out = ds.compatibility("6.3.29", "6.3.13")
    assert out.compatible is False
    assert out.reason == "patch_skew_exceeded"


def test_schema_skew_is_rejected_even_for_adjacent_patch(monkeypatch):
    monkeypatch.setattr(ds, "get_settings", lambda: _settings())
    out = ds.compatibility("6.3.30", "6.3.12")
    assert out.compatible is False
    assert out.reason == "schema_mismatch"


def test_task_envelope_contains_runtime_identity(monkeypatch):
    monkeypatch.setattr(ds, "get_settings", lambda: _settings())
    headers = ds.task_publish_headers()
    assert headers["mgc_app_version"] == "6.3.34"
    assert headers["mgc_schema_version"] == "6.3.13"
    assert headers["mgc_deployment_profile"] == "core"


def test_legacy_task_envelope_allowed_only_during_transition(monkeypatch):
    monkeypatch.setattr(ds, "get_settings", lambda: _settings(rolling_upgrade_allow_legacy_task_envelopes=True))
    out = ds.validate_task_headers({})
    assert out.compatible is True
    assert out.legacy_envelope is True

    monkeypatch.setattr(ds, "get_settings", lambda: _settings(rolling_upgrade_allow_legacy_task_envelopes=False))
    with pytest.raises(ds.RuntimeVersionSkew):
        ds.validate_task_headers({})


def test_incompatible_task_envelope_fails_closed(monkeypatch):
    monkeypatch.setattr(ds, "get_settings", lambda: _settings())
    with pytest.raises(ds.RuntimeVersionSkew):
        ds.validate_task_headers({"mgc_app_version": "6.3.25", "mgc_schema_version": "6.3.13"})


def test_component_registry_reports_incompatible_runtime(monkeypatch):
    monkeypatch.setattr(ds, "get_settings", lambda: _settings())

    class FakeRedis:
        def scan_iter(self, **_kwargs):
            return ["mgc:deployment:component:worker:cpu@node"]

        def get(self, _key):
            return '{"component":"worker","node":"cpu@node","state":"active","app_version":"6.3.25","schema_version":"6.3.13","deployment_profile":"core"}'

    monkeypatch.setattr(ds, "_redis_client", lambda: FakeRedis())
    snap = ds.deployment_safety_snapshot()
    assert snap["registry_status"] == "available"
    assert snap["incompatible_components"] == 1
    assert snap["rolling_upgrade_safe"] is False


def test_component_registry_outage_is_diagnostic_not_core_truth(monkeypatch):
    monkeypatch.setattr(ds, "get_settings", lambda: _settings())
    monkeypatch.setattr(ds, "_redis_client", lambda: (_ for _ in ()).throw(RuntimeError("offline")))
    snap = ds.deployment_safety_snapshot()
    assert snap["registry_status"] == "unavailable"
    assert snap["rolling_upgrade_safe"] is True
    assert snap["policy"]["registry_outage_blocks_core"] is False



def test_version_guard_source_checks_before_task_body():
    from pathlib import Path
    src = Path("backend/app/workers/version_guard.py").read_text()
    assert "validate_task_headers" in src
    assert "super().__call__" in src
    assert src.index("validate_task_headers") < src.index("super().__call__")
