"""FastAPI application entrypoint for the local backend."""

from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.backend.api.router import api_router
from app.backend.core.config import get_settings
from app.backend.core.logging import configure_logging, get_logger


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
        },
    )
    yield


def create_app() -> FastAPI:
    """Create and configure the FastAPI application instance."""
    settings = get_settings()
    app = FastAPI(title=settings.app_name, lifespan=lifespan)
    app.include_router(api_router, prefix="/api")
    return app


app = create_app()

