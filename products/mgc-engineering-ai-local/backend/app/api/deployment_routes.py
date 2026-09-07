from __future__ import annotations

from app.core.runtime_contract import APP_VERSION

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.core.security import Identity, get_identity, is_engineering_admin
from app.services.corporate_deployment import (
    DEPLOYMENT_PROFILES,
    NETWORK_PORTS,
    calculate_deployment_plan,
    evaluate_launch_readiness,
    launch_checklist,
)

router = APIRouter(prefix="/deployment", tags=["deployment"])


def _admin(identity: Identity) -> None:
    if not is_engineering_admin(identity):
        raise HTTPException(403, "Engineering Admin role is required")


class DeploymentPlanRequest(BaseModel):
    user_count: int = Field(default=30, ge=1, le=500)
    documents: int = Field(default=0, ge=0)
    parts: int = Field(default=0, ge=0)
    vehicle_count: int = Field(default=0, ge=0)
    quality_observations: int = Field(default=0, ge=0)
    cad_storage_gb: float = Field(default=0.0, ge=0)
    inference_mode: str = Field(default="cpu", pattern="^(cpu|gpu)$")


class DeploymentReadinessRequest(BaseModel):
    evidence: dict = Field(default_factory=dict)


@router.get("/profiles")
def profiles(identity: Identity = Depends(get_identity)):
    _admin(identity)
    return {"release": APP_VERSION, "profiles": DEPLOYMENT_PROFILES, "certification_required": True}


@router.get("/network-ports")
def network_ports(identity: Identity = Depends(get_identity)):
    _admin(identity)
    return {"release": APP_VERSION, "items": NETWORK_PORTS, "default_deny": True}


@router.get("/launch-checklist")
def checklist(identity: Identity = Depends(get_identity)):
    _admin(identity)
    return launch_checklist()


@router.post("/plan")
def plan(req: DeploymentPlanRequest, identity: Identity = Depends(get_identity)):
    _admin(identity)
    try:
        return calculate_deployment_plan(**req.model_dump())
    except ValueError as exc:
        raise HTTPException(400, str(exc))


@router.post("/readiness")
def readiness(req: DeploymentReadinessRequest, identity: Identity = Depends(get_identity)):
    _admin(identity)
    return evaluate_launch_readiness(req.evidence)
