"""Top-level API router registration."""

from fastapi import APIRouter

from app.backend.api.routes.approvals import router as approvals_router
from app.backend.api.routes.artifacts import router as artifacts_router
from app.backend.api.routes.files import router as files_router
from app.backend.api.routes.github import router as github_router
from app.backend.api.routes.health import router as health_router
from app.backend.api.routes.history import router as history_router
from app.backend.api.routes.mcp import router as mcp_router
from app.backend.api.routes.model_control import router as model_control_router
from app.backend.api.routes.models import router as models_router
from app.backend.api.routes.presets import router as presets_router
from app.backend.api.routes.projects import router as projects_router
from app.backend.api.routes.skills import router as skills_router
from app.backend.api.routes.tasks import router as tasks_router

api_router = APIRouter()
api_router.include_router(approvals_router, prefix="/approvals", tags=["approvals"])
api_router.include_router(artifacts_router, prefix="/artifacts", tags=["artifacts"])
api_router.include_router(files_router, prefix="/files", tags=["files"])
api_router.include_router(github_router, tags=["github"])
api_router.include_router(health_router, tags=["health"])
api_router.include_router(history_router, prefix="/history", tags=["history"])
api_router.include_router(mcp_router, prefix="/mcp", tags=["mcp"])
api_router.include_router(model_control_router, tags=["model-control"])
api_router.include_router(models_router, tags=["models"])
api_router.include_router(presets_router, prefix="/presets", tags=["presets"])
api_router.include_router(projects_router, prefix="/projects", tags=["projects"])
api_router.include_router(skills_router, prefix="/skills", tags=["skills"])
api_router.include_router(tasks_router, prefix="/tasks", tags=["tasks"])
