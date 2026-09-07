"""Compatibility API facade for v6.2.2.

The legacy monolithic handler file was physically split into six bounded-context
routers. This aggregate keeps historical imports and public URLs stable.
"""
from fastapi import APIRouter
from app.api.contexts.engineering_core import router as engineering_core_router
from app.api.contexts.configuration_change import router as configuration_change_router
from app.api.contexts.manufacturing_quality import router as manufacturing_quality_router
from app.api.contexts.supplier_field import router as supplier_field_router
from app.api.contexts.intelligence_search import router as intelligence_search_router
from app.api.contexts.platform_operations import router as platform_operations_router

router = APIRouter()
for _router in (
    engineering_core_router, configuration_change_router, manufacturing_quality_router,
    supplier_field_router, intelligence_search_router, platform_operations_router,
):
    router.include_router(_router)
