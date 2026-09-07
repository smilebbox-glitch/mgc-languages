from __future__ import annotations

from typing import Any, Callable

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session


def build_system_router(
    *,
    app_version: str,
    instance_id: str,
    app_env: str,
    auth_mode: str,
    registration_enabled: bool,
    tts_legacy_get_enabled: bool,
    tts_cache_persistence: str,
    expected_alembic_head: str,
    otel_enabled: bool,
    db_session: Callable[..., Any],
    readiness_checks: Callable[[Session], tuple[bool, dict[str, Any]]],
    update_recovery_state: Callable[..., dict[str, Any]],
    tts_health: Callable[..., dict[str, Any]],
    recovery_view: Callable[[], dict[str, Any]],
) -> APIRouter:
    """Build system/readiness/meta routes without importing the legacy app module."""
    router = APIRouter()

    @router.get("/health")
    @router.get("/health/live")
    def health():
        return {
            "status": "ok",
            "service": "mgc-languages",
            "version": app_version,
            "recovery": recovery_view(),
        }

    @router.get("/ready")
    @router.get("/health/ready")
    def ready(db: Session = Depends(db_session)):
        ok, checks = readiness_checks(db)
        recovery = update_recovery_state(
            ready_ok=ok,
            checks=checks,
            tts_health=tts_health(),
        )
        payload = {
            "status": "ready" if ok else "not_ready",
            "checks": checks,
            "recovery": recovery,
        }
        if not ok:
            return JSONResponse(payload, status_code=503)
        return payload

    @router.get("/api/meta")
    def meta():
        return {
            "title": "MGC Languages",
            "version": app_version,
            "instance_id": instance_id,
            "environment": app_env,
            "auth_mode": auth_mode,
            "local_auth_enabled": auth_mode == "local",
            "registration_enabled": registration_enabled and auth_mode == "local",
            "languages": [
                {"id": "english", "label": "Английский", "native": "English"},
                {"id": "chinese", "label": "Китайский", "native": "中文"},
            ],
            "server_tts_available": tts_health()["server_available"],
            "voice_recording_enabled": False,
            "pronunciation_transport": "POST",
            "legacy_tts_get_enabled": tts_legacy_get_enabled,
            "tts_cache_persistence": tts_cache_persistence,
            "expected_schema_head": expected_alembic_head,
            "reliability_profile": "pilot-v5.7.1",
            "slo_profile": "pilot-operations-v5.5",
            "governance_profile": "pilot-governance-v5.6",
            "security_profile": "rls-content-integrity-v5.7",
            "adaptive_learning": "srs-v5.7",
            "recovery_profile": "observability-recovery-v5.7.1",
            "otel_enabled": otel_enabled,
            "chinese_learning_standard": "Путунхуа (普通话) — стандартный китайский",
        }

    return router


__all__ = ["build_system_router"]
