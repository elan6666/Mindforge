"""FastAPI application entrypoint for the local backend."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.backend.api.router import api_router
from app.backend.core.config import get_settings
from app.backend.core.logging import configure_logging, get_logger
from app.backend.services.history_service import get_history_service


@asynccontextmanager
async def lifespan(_: FastAPI):
    """Configure runtime concerns when the application starts."""
    settings = get_settings()
    configure_logging(settings.log_level)
    logger = get_logger("app.startup")
    logger.info(
        "starting application",
        extra={
            "app_name": settings.app_name,
            "environment": settings.app_env,
            "openhands_mode": settings.openhands_mode,
            "sqlite_db_path": settings.sqlite_db_path,
        },
    )
    get_history_service()
    yield


def create_app() -> FastAPI:
    """Create and configure the FastAPI application instance."""
    settings = get_settings()
    app = FastAPI(title=settings.app_name, lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(api_router, prefix="/api")
    return app


app = create_app()
