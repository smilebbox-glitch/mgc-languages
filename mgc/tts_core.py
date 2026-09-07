from __future__ import annotations

import hashlib
import io
import json
import os
import re
import subprocess
import threading
import time
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any, Callable

from fastapi import HTTPException, Request
from fastapi.responses import StreamingResponse


@dataclass(frozen=True)
class TTSCoreConfig:
    enabled: bool
    binary: str
    voice_chinese: str
    voice_english: str
    timeout_seconds: int
    concurrency: int
    failure_threshold: int
    circuit_cooldown_seconds: int
    health_ttl_seconds: int
    disk_cache_enabled: bool
    cache_dir: Path
    disk_cache_max_mb: int
    disk_cache_ttl_hours: int
    cache_persistence: str


@dataclass(frozen=True)
class TTSCoreBindings:
    cache_path: Callable[[str, str, int], Path]
    cache_read: Callable[[str, str, int], bytes | None]
    prune_cache: Callable[[], None]
    cache_write: Callable[[str, str, int, bytes], None]
    circuit_open: Callable[[], bool]
    mark_success: Callable[[], None]
    mark_failure: Callable[[], None]
    synthesize_wav: Callable[[str, str, int], bytes]
    health: Callable[[bool], dict[str, Any]]
    pronunciation_response: Callable[[Request, str, str, float], StreamingResponse]
    semaphore: Any
    runtime_lock: Any
    runtime: dict[str, Any]
    health_lock: Any
    health_cache: dict[str, Any]


def build_tts_core(
    *,
    config: TTSCoreConfig,
    validate_language: Callable[[str], str],
    rate_limit: Callable[[Request, str, int, int], None],
    operational_event: Callable[..., None],
    logger: Any,
) -> TTSCoreBindings:
    """Build the offline TTS runtime without importing the FastAPI monolith.

    The implementation preserves the v5.3.2 cache key, in-process LRU cache,
    disk-cache validation/pruning, circuit breaker, semaphore, health probe and
    pronunciation response contracts. Mutable state is returned explicitly so
    the compatibility bridge can expose the same objects to observability.
    """

    semaphore = threading.BoundedSemaphore(config.concurrency)
    runtime_lock = threading.Lock()
    runtime: dict[str, Any] = {
        "success_total": 0,
        "failure_total": 0,
        "disk_cache_hits": 0,
        "disk_cache_writes": 0,
        "consecutive_failures": 0,
        "circuit_open_until": 0.0,
    }
    health_lock = threading.Lock()
    health_cache: dict[str, Any] = {"expires_at": 0.0, "value": None}

    def cache_path(language: str, text_value: str, rate_key: int) -> Path:
        digest = hashlib.sha256(
            f"v5.3.2|{language}|{rate_key}|{text_value}".encode("utf-8")
        ).hexdigest()
        return config.cache_dir / f"{digest}.wav"

    def cache_read(language: str, text_value: str, rate_key: int) -> bytes | None:
        if not config.disk_cache_enabled:
            return None
        path = cache_path(language, text_value, rate_key)
        try:
            if not path.is_file():
                return None
            age = time.time() - path.stat().st_mtime
            if age > config.disk_cache_ttl_hours * 3600:
                path.unlink(missing_ok=True)
                return None
            data = path.read_bytes()
            if not data.startswith(b"RIFF") or len(data) < 512:
                path.unlink(missing_ok=True)
                return None
            with runtime_lock:
                runtime["disk_cache_hits"] += 1
            return data
        except OSError:
            return None

    def prune_cache() -> None:
        if not config.disk_cache_enabled:
            return
        try:
            config.cache_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
            files = [x for x in config.cache_dir.glob("*.wav") if x.is_file()]
            max_bytes = config.disk_cache_max_mb * 1024 * 1024
            total = sum(x.stat().st_size for x in files)
            if total <= max_bytes:
                return
            target = int(max_bytes * 0.8)
            for item in sorted(files, key=lambda x: x.stat().st_mtime):
                size = item.stat().st_size
                item.unlink(missing_ok=True)
                total -= size
                if total <= target:
                    break
        except OSError:
            pass

    def cache_write(language: str, text_value: str, rate_key: int, data: bytes) -> None:
        if not config.disk_cache_enabled or not data.startswith(b"RIFF"):
            return
        try:
            config.cache_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
            path = cache_path(language, text_value, rate_key)
            tmp = path.with_suffix(".tmp")
            tmp.write_bytes(data)
            os.chmod(tmp, 0o600)
            os.replace(tmp, path)
            with runtime_lock:
                runtime["disk_cache_writes"] += 1
            prune_cache()
        except OSError:
            pass

    def circuit_open() -> bool:
        with runtime_lock:
            return time.monotonic() < float(runtime["circuit_open_until"])

    def mark_success() -> None:
        with runtime_lock:
            runtime["success_total"] += 1
            runtime["consecutive_failures"] = 0
            runtime["circuit_open_until"] = 0.0

    def mark_failure() -> None:
        with runtime_lock:
            runtime["failure_total"] += 1
            runtime["consecutive_failures"] += 1
            if runtime["consecutive_failures"] >= config.failure_threshold:
                runtime["circuit_open_until"] = (
                    time.monotonic() + config.circuit_cooldown_seconds
                )

    @lru_cache(maxsize=256)
    def synthesize_wav(language: str, text_value: str, rate_key: int) -> bytes:
        if not config.enabled or not config.binary:
            raise RuntimeError("server TTS unavailable")
        cached = cache_read(language, text_value, rate_key)
        if cached:
            return cached
        if circuit_open():
            raise RuntimeError("TTS circuit breaker open")
        acquired = semaphore.acquire(timeout=config.timeout_seconds)
        if not acquired:
            mark_failure()
            raise RuntimeError("TTS concurrency limit reached")
        try:
            voice = config.voice_chinese if language == "chinese" else config.voice_english
            speed = max(80, min(240, int(175 * (rate_key / 100))))
            result = subprocess.run(
                [config.binary, "-v", voice, "-s", str(speed), "--stdout"],
                input=text_value.encode("utf-8"),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=config.timeout_seconds,
                check=False,
            )
            if result.returncode != 0 or not result.stdout.startswith(b"RIFF"):
                error = (result.stderr or b"TTS failed").decode("utf-8", "ignore")[:500]
                mark_failure()
                raise RuntimeError(error)
            mark_success()
            cache_write(language, text_value, rate_key, result.stdout)
            return result.stdout
        except subprocess.SubprocessError:
            mark_failure()
            raise
        finally:
            semaphore.release()

    def health(force: bool = False) -> dict[str, Any]:
        now = time.monotonic()
        with health_lock:
            cached = health_cache.get("value")
            if (
                not force
                and cached is not None
                and now < float(health_cache.get("expires_at", 0))
            ):
                return dict(cached)
        engine = Path(config.binary).name if config.binary else "browser-fallback"
        result: dict[str, Any] = {
            "server_available": False,
            "engine": engine,
            "offline": False,
            "voices": {
                "chinese": config.voice_chinese,
                "english": config.voice_english,
            },
            "language_checks": {"chinese": False, "english": False},
            "circuit_open": circuit_open(),
            "timeout_seconds": config.timeout_seconds,
            "concurrency": config.concurrency,
            "disk_cache_enabled": config.disk_cache_enabled,
            "cache_persistence": config.cache_persistence,
            "cache_writable": False,
        }
        if config.disk_cache_enabled:
            try:
                config.cache_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
                probe = config.cache_dir / ".write-probe"
                probe.write_bytes(b"ok")
                os.chmod(probe, 0o600)
                probe.unlink(missing_ok=True)
                result["cache_writable"] = True
            except OSError:
                result["cache_writable"] = False
        else:
            result["cache_writable"] = True
        if config.enabled and config.binary and not result["circuit_open"]:
            samples = {"chinese": "你好", "english": "hello"}
            for language, sample in samples.items():
                try:
                    wav = synthesize_wav(language, sample, 90)
                    result["language_checks"][language] = (
                        wav.startswith(b"RIFF") and len(wav) > 512
                    )
                except Exception as exc:
                    logger.warning(
                        json.dumps(
                            {
                                "event": "tts_probe_failed",
                                "language": language,
                                "error": str(exc)[:200],
                            },
                            ensure_ascii=False,
                        )
                    )
            result["server_available"] = all(result["language_checks"].values())
            result["offline"] = result["server_available"]
        with runtime_lock:
            result["runtime"] = dict(runtime)
        with health_lock:
            health_cache["value"] = dict(result)
            health_cache["expires_at"] = now + config.health_ttl_seconds
        return result

    def pronunciation_response(
        request: Request,
        language: str,
        text_value: str,
        rate: float,
    ) -> StreamingResponse:
        language = validate_language(language)
        rate_limit(request, "tts", 90, 60)
        cleaned = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", " ", text_value).strip()
        if not cleaned:
            raise HTTPException(400, "Нет текста для произношения")
        health_view = health()
        if (
            not health_view.get("server_available")
            or not health_view.get("language_checks", {}).get(language)
        ):
            operational_event(
                "tts.fallback",
                severity="warning",
                component="tts",
                status_code=503,
                request=request,
                metadata={"language": language, "circuit_open": circuit_open()},
                throttle_seconds=60,
            )
            raise HTTPException(
                503,
                "Серверное произношение недоступно; используйте browser fallback",
            )
        try:
            wav = synthesize_wav(language, cleaned, int(round(rate * 100)))
        except (subprocess.SubprocessError, RuntimeError) as exc:
            logger.warning(
                json.dumps(
                    {
                        "event": "tts_failed",
                        "language": language,
                        "error": str(exc)[:200],
                    },
                    ensure_ascii=False,
                )
            )
            operational_event(
                "tts.failure",
                severity="error",
                component="tts",
                status_code=503,
                request=request,
                detail=type(exc).__name__,
                metadata={"language": language, "circuit_open": circuit_open()},
                throttle_seconds=10,
            )
            raise HTTPException(503, "Серверное произношение временно недоступно")
        return StreamingResponse(
            io.BytesIO(wav),
            media_type="audio/wav",
            headers={
                "Content-Disposition": "inline; filename=pronunciation.wav",
                "X-TTS-Engine": Path(config.binary).name,
                "X-TTS-Voice": (
                    config.voice_chinese if language == "chinese" else config.voice_english
                ),
                "Cache-Control": "no-store",
                "X-Content-Type-Options": "nosniff",
            },
        )

    for function, legacy_name in (
        (cache_path, "_tts_cache_path"),
        (cache_read, "_tts_cache_read"),
        (prune_cache, "_prune_tts_cache"),
        (cache_write, "_tts_cache_write"),
        (circuit_open, "_tts_circuit_open"),
        (mark_success, "_tts_mark_success"),
        (mark_failure, "_tts_mark_failure"),
        (synthesize_wav, "_synthesize_wav"),
        (health, "_tts_health"),
        (pronunciation_response, "_pronunciation_response"),
    ):
        function.__name__ = legacy_name
        function.__qualname__ = legacy_name

    return TTSCoreBindings(
        cache_path=cache_path,
        cache_read=cache_read,
        prune_cache=prune_cache,
        cache_write=cache_write,
        circuit_open=circuit_open,
        mark_success=mark_success,
        mark_failure=mark_failure,
        synthesize_wav=synthesize_wav,
        health=health,
        pronunciation_response=pronunciation_response,
        semaphore=semaphore,
        runtime_lock=runtime_lock,
        runtime=runtime,
        health_lock=health_lock,
        health_cache=health_cache,
    )


__all__ = ["TTSCoreBindings", "TTSCoreConfig", "build_tts_core"]
