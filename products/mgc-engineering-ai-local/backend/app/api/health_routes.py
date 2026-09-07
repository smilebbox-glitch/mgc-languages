from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.core.config import get_settings
from app.core.runtime_contract import APP_VERSION, SCHEMA_VERSION
from app.core.operational_health import readiness_snapshot

router = APIRouter()


@router.get("/health")
def health():
    # Backward-compatible liveness endpoint. It intentionally performs no downstream I/O.
    return {"status": "ok", "service": get_settings().app_name, "version": APP_VERSION, "air_gapped_mode": get_settings().air_gapped_mode}


@router.get("/health/live")
def health_live():
    return {"status": "alive", "service": get_settings().app_name, "version": APP_VERSION}


@router.get("/health/ready")
def health_ready():
    snapshot = readiness_snapshot()
    return JSONResponse(snapshot, status_code=200 if snapshot["status"] == "ready" else 503)


@router.get("/health/lb")
def health_load_balancer():
    """Minimal external load-balancer eligibility contract; never expose internal diagnostics."""
    snapshot = readiness_snapshot()
    eligible = snapshot.get("status") == "ready"
    body = {
        "contract": "mgc-external-lb-v1",
        "status": "eligible" if eligible else "ineligible",
        "traffic_eligible": eligible,
        "version": APP_VERSION,
        "schema_version": SCHEMA_VERSION,
    }
    return JSONResponse(body, status_code=200 if eligible else 503)
