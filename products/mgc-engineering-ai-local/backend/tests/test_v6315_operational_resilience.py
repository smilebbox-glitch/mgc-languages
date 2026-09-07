from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.core import resilience as r


def _settings(**overrides):
    base = dict(
        resilience_enabled=True,
        resilience_failure_threshold=2,
        resilience_open_seconds=30.0,
    )
    base.update(overrides)
    return SimpleNamespace(**base)


def test_breaker_opens_after_threshold_and_reports_brownout(monkeypatch):
    monkeypatch.setattr(r, "get_settings", lambda: _settings())
    reg = r.ResilienceRegistry()
    monkeypatch.setattr(r, "REGISTRY", reg)
    assert r.circuit_allows("qdrant") is True
    r.record_failure("qdrant", TimeoutError())
    assert reg.circuit("qdrant").state == "closed"
    r.record_failure("qdrant", TimeoutError())
    assert r.circuit_allows("qdrant") is False
    snap = r.resilience_snapshot()
    assert snap["mode"] == "BROWNOUT"
    assert "qdrant" in snap["optional_dependencies_open"]
    assert snap["policy"]["qdrant_failure_allows_lexical_fallback"] is True


def test_success_closes_circuit(monkeypatch):
    monkeypatch.setattr(r, "get_settings", lambda: _settings(resilience_failure_threshold=1))
    reg = r.ResilienceRegistry()
    monkeypatch.setattr(r, "REGISTRY", reg)
    r.record_failure("local_ai", RuntimeError())
    assert r.circuit_allows("local_ai") is False
    r.record_success("local_ai")
    assert reg.circuit("local_ai").state == "closed"
    assert r.resilience_snapshot()["mode"] == "NORMAL"


def test_open_circuit_half_open_probe_after_cooldown(monkeypatch):
    clock = [100.0]
    monkeypatch.setattr(r, "get_settings", lambda: _settings(resilience_failure_threshold=1, resilience_open_seconds=5.0))
    monkeypatch.setattr(r.time, "monotonic", lambda: clock[0])
    reg = r.ResilienceRegistry()
    monkeypatch.setattr(r, "REGISTRY", reg)
    r.record_failure("vlm", TimeoutError())
    assert r.circuit_allows("vlm") is False
    clock[0] = 106.0
    assert r.circuit_allows("vlm") is True
    assert reg.circuit("vlm").state == "half_open"
    assert r.circuit_allows("vlm") is False
    r.record_success("vlm")
    assert r.circuit_allows("vlm") is True


def test_non_dependency_capability_remains_available(monkeypatch):
    monkeypatch.setattr(r, "get_settings", lambda: _settings(resilience_failure_threshold=1))
    reg = r.ResilienceRegistry()
    monkeypatch.setattr(r, "REGISTRY", reg)
    r.record_failure("qdrant", RuntimeError())
    assert r.capability_available("engineering_core") is True
    assert r.capability_available("semantic_search") is False


def test_vector_search_falls_back_when_qdrant_circuit_open(monkeypatch):
    import app.services.vector_store as vector_store
    monkeypatch.setattr(vector_store, "_semantic_enabled", lambda: True)
    monkeypatch.setattr(vector_store, "circuit_allows", lambda dependency: False)
    monkeypatch.setattr(vector_store, "_fallback_search", lambda *args, **kwargs: [{"metadata": {"retrieval_mode": "core_lexical_postgres"}}])
    hits = vector_store.search("bom", 5, ["all"])
    assert hits[0]["metadata"]["retrieval_mode"] == "core_lexical_postgres"


def test_version_is_6315_without_schema_change():
    from app.core.runtime_contract import APP_VERSION, SCHEMA_VERSION
    assert APP_VERSION == "6.3.34"
    assert SCHEMA_VERSION == "6.3.13"
