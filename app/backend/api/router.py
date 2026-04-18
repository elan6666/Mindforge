"""Top-level API router registration."""

from fastapi import APIRouter

from app.backend.api.routes.health import router as health_router
from app.backend.api.routes.presets import router as presets_router
from app.backend.api.routes.tasks import router as tasks_router

api_router = APIRouter()
api_router.include_router(health_router, tags=["health"])
api_router.include_router(presets_router, prefix="/presets", tags=["presets"])
api_router.include_router(tasks_router, prefix="/tasks", tags=["tasks"])
