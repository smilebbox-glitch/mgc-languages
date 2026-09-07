from types import SimpleNamespace

import pytest

from app.services import local_ai


def _cfg(**overrides):
    base = dict(
        air_gapped_mode=True,
        local_inference_allowed_host_set={"model-server", "localhost", "127.0.0.1"},
    )
    base.update(overrides)
    return SimpleNamespace(**base)


def test_airgap_allows_internal_model_host(monkeypatch):
    monkeypatch.setattr(local_ai, "get_settings", lambda: _cfg())
    assert local_ai.validate_inference_url("http://model-server:8000/v1") == "http://model-server:8000/v1"


def test_airgap_blocks_public_model_host(monkeypatch):
    monkeypatch.setattr(local_ai, "get_settings", lambda: _cfg())
    with pytest.raises(RuntimeError, match="blocks inference host"):
        local_ai.validate_inference_url("https://api.example.com/v1")


def test_airgap_allows_private_ip(monkeypatch):
    monkeypatch.setattr(local_ai, "get_settings", lambda: _cfg())
    assert local_ai.validate_inference_url("http://10.25.4.8:8000/v1") == "http://10.25.4.8:8000/v1"


def test_non_airgap_does_not_restrict_url(monkeypatch):
    monkeypatch.setattr(local_ai, "get_settings", lambda: _cfg(air_gapped_mode=False))
    assert local_ai.validate_inference_url("https://example.com/v1") == "https://example.com/v1"
