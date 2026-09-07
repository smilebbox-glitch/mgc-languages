from __future__ import annotations

import inspect
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType

from mgc.tts_core import TTSCoreBindings, TTSCoreConfig, build_tts_core


@dataclass(frozen=True)
class TTSBindingReport:
    ok: bool
    cache_bound: bool
    circuit_bound: bool
    synthesis_bound: bool
    health_bound: bool
    pronunciation_response_bound: bool
    state_bound: bool
    config_preserved: bool
    lru_cache_preserved: bool
    observability_state_compatible: bool
    hooks_captured: bool
    module_owned: bool


def _config_from_module(module: ModuleType) -> TTSCoreConfig:
    return TTSCoreConfig(
        enabled=bool(module.TTS_ENABLED),
        binary=str(module.TTS_BINARY),
        voice_chinese=str(module.TTS_VOICE_CHINESE),
        voice_english=str(module.TTS_VOICE_ENGLISH),
        timeout_seconds=int(module.TTS_TIMEOUT_SECONDS),
        concurrency=int(module.TTS_CONCURRENCY),
        failure_threshold=int(module.TTS_FAILURE_THRESHOLD),
        circuit_cooldown_seconds=int(module.TTS_CIRCUIT_COOLDOWN_SECONDS),
        health_ttl_seconds=int(module.TTS_HEALTH_TTL_SECONDS),
        disk_cache_enabled=bool(module.TTS_DISK_CACHE_ENABLED),
        cache_dir=Path(module.TTS_CACHE_DIR),
        disk_cache_max_mb=int(module.TTS_DISK_CACHE_MAX_MB),
        disk_cache_ttl_hours=int(module.TTS_DISK_CACHE_TTL_HOURS),
        cache_persistence=str(module.TTS_CACHE_PERSISTENCE),
    )


def _hooks_captured(module: ModuleType, bindings: TTSCoreBindings) -> bool:
    try:
        closure = inspect.getclosurevars(bindings.pronunciation_response)
    except (TypeError, ValueError):
        return False
    return all(
        (
            closure.nonlocals.get("validate_language") is module.validate_language,
            closure.nonlocals.get("rate_limit") is module.rate_limit,
            closure.nonlocals.get("operational_event") is module.operational_event,
            closure.nonlocals.get("logger") is module.logger,
        )
    )


def bind_legacy_tts(module: ModuleType) -> TTSBindingReport:
    """Bind the legacy TTS globals to the extracted stateful TTS core.

    State aliases are intentionally preserved because the extracted v5.8.1
    observability bridge reads `_TTS_RUNTIME_LOCK` and `_TTS_RUNTIME` directly.
    Both layers therefore observe one shared runtime state, not copied counters.
    """
    existing = getattr(module, "MGC_TTS_BINDING_REPORT", None)
    if isinstance(existing, TTSBindingReport) and existing.ok:
        return existing

    required_config = (
        "TTS_ENABLED",
        "TTS_BINARY",
        "TTS_VOICE_CHINESE",
        "TTS_VOICE_ENGLISH",
        "TTS_TIMEOUT_SECONDS",
        "TTS_CONCURRENCY",
        "TTS_FAILURE_THRESHOLD",
        "TTS_CIRCUIT_COOLDOWN_SECONDS",
        "TTS_HEALTH_TTL_SECONDS",
        "TTS_DISK_CACHE_ENABLED",
        "TTS_CACHE_DIR",
        "TTS_DISK_CACHE_MAX_MB",
        "TTS_DISK_CACHE_TTL_HOURS",
        "TTS_CACHE_PERSISTENCE",
    )
    required_hooks = ("validate_language", "rate_limit", "operational_event", "logger")
    required_legacy = (
        "_tts_cache_path",
        "_tts_cache_read",
        "_prune_tts_cache",
        "_tts_cache_write",
        "_tts_circuit_open",
        "_tts_mark_success",
        "_tts_mark_failure",
        "_synthesize_wav",
        "_tts_health",
        "_pronunciation_response",
        "_TTS_SEMAPHORE",
        "_TTS_RUNTIME_LOCK",
        "_TTS_RUNTIME",
        "_TTS_HEALTH_LOCK",
        "_TTS_HEALTH_CACHE",
    )
    missing = [
        name
        for name in (*required_config, *required_hooks, *required_legacy)
        if not hasattr(module, name)
    ]
    if missing:
        raise RuntimeError(f"legacy TTS contract is incomplete: {missing}")

    config = _config_from_module(module)
    config_preserved = all(
        (
            config.enabled == bool(module.TTS_ENABLED),
            config.binary == str(module.TTS_BINARY),
            config.voice_chinese == str(module.TTS_VOICE_CHINESE),
            config.voice_english == str(module.TTS_VOICE_ENGLISH),
            config.timeout_seconds == int(module.TTS_TIMEOUT_SECONDS),
            config.concurrency == int(module.TTS_CONCURRENCY),
            config.failure_threshold == int(module.TTS_FAILURE_THRESHOLD),
            config.circuit_cooldown_seconds == int(module.TTS_CIRCUIT_COOLDOWN_SECONDS),
            config.health_ttl_seconds == int(module.TTS_HEALTH_TTL_SECONDS),
            config.disk_cache_enabled == bool(module.TTS_DISK_CACHE_ENABLED),
            config.cache_dir == Path(module.TTS_CACHE_DIR),
            config.disk_cache_max_mb == int(module.TTS_DISK_CACHE_MAX_MB),
            config.disk_cache_ttl_hours == int(module.TTS_DISK_CACHE_TTL_HOURS),
            config.cache_persistence == str(module.TTS_CACHE_PERSISTENCE),
        )
    )
    if not config_preserved:
        raise RuntimeError("TTS configuration drifted during core extraction")

    bindings = build_tts_core(
        config=config,
        validate_language=module.validate_language,
        rate_limit=module.rate_limit,
        operational_event=module.operational_event,
        logger=module.logger,
    )

    module._TTS_SEMAPHORE = bindings.semaphore
    module._TTS_RUNTIME_LOCK = bindings.runtime_lock
    module._TTS_RUNTIME = bindings.runtime
    module._TTS_HEALTH_LOCK = bindings.health_lock
    module._TTS_HEALTH_CACHE = bindings.health_cache
    module._tts_cache_path = bindings.cache_path
    module._tts_cache_read = bindings.cache_read
    module._prune_tts_cache = bindings.prune_cache
    module._tts_cache_write = bindings.cache_write
    module._tts_circuit_open = bindings.circuit_open
    module._tts_mark_success = bindings.mark_success
    module._tts_mark_failure = bindings.mark_failure
    module._synthesize_wav = bindings.synthesize_wav
    module._tts_health = bindings.health
    module._pronunciation_response = bindings.pronunciation_response
    module.MGC_TTS_CORE_CONFIG = config
    module.MGC_TTS_CORE_BINDINGS = bindings

    cache_bound = all(
        (
            module._tts_cache_path is bindings.cache_path,
            module._tts_cache_read is bindings.cache_read,
            module._prune_tts_cache is bindings.prune_cache,
            module._tts_cache_write is bindings.cache_write,
        )
    )
    circuit_bound = all(
        (
            module._tts_circuit_open is bindings.circuit_open,
            module._tts_mark_success is bindings.mark_success,
            module._tts_mark_failure is bindings.mark_failure,
        )
    )
    synthesis_bound = module._synthesize_wav is bindings.synthesize_wav
    health_bound = module._tts_health is bindings.health
    pronunciation_response_bound = (
        module._pronunciation_response is bindings.pronunciation_response
    )
    state_bound = all(
        (
            module._TTS_SEMAPHORE is bindings.semaphore,
            module._TTS_RUNTIME_LOCK is bindings.runtime_lock,
            module._TTS_RUNTIME is bindings.runtime,
            module._TTS_HEALTH_LOCK is bindings.health_lock,
            module._TTS_HEALTH_CACHE is bindings.health_cache,
        )
    )
    runtime_keys = {
        "success_total",
        "failure_total",
        "disk_cache_hits",
        "disk_cache_writes",
        "consecutive_failures",
        "circuit_open_until",
    }
    observability_state_compatible = (
        state_bound and set(module._TTS_RUNTIME) == runtime_keys
    )
    cache_info = getattr(bindings.synthesize_wav, "cache_info", None)
    lru_cache_preserved = callable(cache_info) and cache_info().maxsize == 256
    hooks_captured = _hooks_captured(module, bindings)
    function_names = (
        "_tts_cache_path",
        "_tts_cache_read",
        "_prune_tts_cache",
        "_tts_cache_write",
        "_tts_circuit_open",
        "_tts_mark_success",
        "_tts_mark_failure",
        "_synthesize_wav",
        "_tts_health",
        "_pronunciation_response",
    )
    module_owned = all(
        getattr(getattr(module, name), "__module__", "") == "mgc.tts_core"
        for name in function_names
    )

    report = TTSBindingReport(
        ok=all(
            (
                cache_bound,
                circuit_bound,
                synthesis_bound,
                health_bound,
                pronunciation_response_bound,
                state_bound,
                config_preserved,
                lru_cache_preserved,
                observability_state_compatible,
                hooks_captured,
                module_owned,
            )
        ),
        cache_bound=cache_bound,
        circuit_bound=circuit_bound,
        synthesis_bound=synthesis_bound,
        health_bound=health_bound,
        pronunciation_response_bound=pronunciation_response_bound,
        state_bound=state_bound,
        config_preserved=config_preserved,
        lru_cache_preserved=lru_cache_preserved,
        observability_state_compatible=observability_state_compatible,
        hooks_captured=hooks_captured,
        module_owned=module_owned,
    )
    if not report.ok:
        raise RuntimeError("v5.8.7 TTS core binding failed closed")
    module.MGC_TTS_BINDING_REPORT = report
    return report


__all__ = ["TTSBindingReport", "bind_legacy_tts"]
