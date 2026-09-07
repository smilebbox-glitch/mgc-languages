from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.context_registry import build_context_router
from app.api.integration_routes import router as integration_router
from app.api.health_routes import router as health_router
from app.api.pilot_routes import router as pilot_router
from app.api.operations_routes import router as operations_router
from app.api.deployment_routes import router as deployment_router
from app.api.simplified_routes import router as simplified_router
from app.core.config import get_settings
from app.db import models  # noqa
from app.db.session import Base, engine, SessionLocal
from app.db.unit_of_work import EditConflict
from app.core.db_performance import QueryBudgetExceeded
from app.db.bootstrap import bootstrap_schema
from app.services.read_model_hooks import install_read_model_invalidation_hooks
from app.core.telemetry import setup_telemetry
from app.core.request_logging import RequestLoggingMiddleware
from app.core.capability_gate import CapabilityGateMiddleware
from app.core.authoritative_write_gate import AuthoritativeWriteGateMiddleware
from app.core.db_pool_admission import DbPoolAdmissionMiddleware
from app.core.runtime_contract import APP_VERSION, validate_build_profile
from prometheus_fastapi_instrumentator import Instrumentator

cfg = get_settings()
install_read_model_invalidation_hooks()
validate_build_profile(cfg.runtime_profile, cfg.mgc_build_profile)
if cfg.auto_migrate_schema:
    bootstrap_schema(engine, Base.metadata)
_prod = cfg.app_env.lower() in {"prod", "production"}
app = FastAPI(
    title=cfg.app_name, version=APP_VERSION,
    description="Engineer-only, fully local Engineering Intelligence platform",
    docs_url=None if _prod else "/docs", redoc_url=None if _prod else "/redoc", openapi_url=None if _prod else "/openapi.json",
)
app.add_middleware(CORSMiddleware, allow_origins=cfg.cors_list, allow_credentials=False, allow_methods=cfg.cors_method_list, allow_headers=cfg.cors_header_list)
app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(CapabilityGateMiddleware)
app.add_middleware(AuthoritativeWriteGateMiddleware)
app.add_middleware(DbPoolAdmissionMiddleware)
app.include_router(health_router, prefix="/api/v1")
app.include_router(build_context_router(cfg.runtime_features), prefix="/api/v1")
app.include_router(integration_router, prefix="/api/v1")
app.include_router(pilot_router, prefix="/api/v1")
app.include_router(operations_router, prefix="/api/v1")
app.include_router(deployment_router, prefix="/api/v1")
app.include_router(simplified_router, prefix="/api/v1")
Instrumentator().instrument(app).expose(app, include_in_schema=False)
setup_telemetry(app)


@app.exception_handler(QueryBudgetExceeded)
async def query_budget_handler(request: Request, exc: QueryBudgetExceeded):
    return JSONResponse(status_code=503, content={"detail": {
        "code": "DB_QUERY_BUDGET_EXCEEDED",
        "message": "Database query budget exceeded. Retry or narrow the request.",
        "hard_enforcement": True,
    }})


@app.exception_handler(EditConflict)
async def edit_conflict_handler(request: Request, exc: EditConflict):
    # Conflict observability must never turn a safe 409 into a 500. The domain write
    # was already rejected, so telemetry is recorded best-effort in a separate session.
    try:
        from app.db.models import EditConflictEvent
        with SessionLocal() as db:
            db.add(EditConflictEvent(
                entity_type=exc.entity_type, entity_id=exc.entity_id, route=request.url.path,
                expected_version=exc.expected_version, current_version=exc.current_version,
                current_record_json=exc.current_record or {},
            ))
            db.commit()
    except Exception:
        pass
    return JSONResponse(
        status_code=409,
        content={"detail": {
            "code": "EDIT_CONFLICT",
            "message": "Запись уже была изменена другим пользователем. Сравните свою версию с актуальной и повторите изменения осознанно.",
            "entity_type": exc.entity_type,
            "entity_id": exc.entity_id,
            "expected_version": exc.expected_version,
            "current_version": exc.current_version,
            "current_record": exc.current_record or {},
            "auto_merge": False,
        }},
    )


@app.get("/")
def root():
    return {"name": cfg.app_name, "version": APP_VERSION, "docs": "/docs", "mode": "air-gapped-local"}
